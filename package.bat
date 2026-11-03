@echo off
cd /d "%~dp0"
REM ============================================================
REM  异色逮捕计划 打包脚本 (PyInstaller onefile)
REM ============================================================
REM 说明：
REM 1. OCR 识别功能的依赖是函数内惰性导入，PyInstaller 静态扫描抓不到，
REM    必须用 --hidden-import / --collect-* 显式声明，否则打包后的 exe 一调用识别就报 ModuleNotFoundError。
REM 2. 本机存在多个 Python，pyinstaller 可能解析到“缺依赖”的解释器导致打包失败。
REM    因此本脚本会【自动探测】第一个“同时具备 PyQt5 与 PyInstaller”的 Python 来打包，
REM    不再依赖 PATH 里 pyinstaller 指向谁。
REM 3. 必须排除 tensorflow / paddlex / keras：本软件做 OCR 只用 PaddleOCR，
REM    不需要 tensorflow；若让 PyInstaller 收集到 tensorflow，其原生扩展在导入时会
REM    “access violation” 段错误导致整个打包崩溃。
REM 4. PyQt5 自带的 msvcp140 / vcruntime140 运行库与系统 VC++ 运行库冲突，会让冻结后的
REM    exe 一启动就 0xc0000005 段错误崩溃。故打包时临时移走这些 DLL，让 exe 改用系统运行库，
REM    打包结束再还原，不影响原 Python 环境。
REM 5. 默认只打包 PaddleOCR 主引擎 + 其 C 扩展依赖，体积约数百 MB。
REM    easyocr / tesseract 兜底引擎【默认不打包】（见文件末尾注释），避免拉入 torch 约 700MB+。
REM 6. 打包前请先安装：pip install pyinstaller pillow paddleocr paddlepaddle
REM    （可选兜底）pip install easyocr  或  pip install pytesseract 并安装 Tesseract-OCR

REM ---- 自动定位“同时具备 PyQt5 与 PyInstaller”的 Python ----
set "BUILD_PYTHON="
for /f "delims=" %%P in ('where python 2^>nul') do (
    if not defined BUILD_PYTHON (
        "%%P" -c "import PyQt5, PyInstaller" >nul 2>&1 && set "BUILD_PYTHON=%%P"
    )
)
if not defined BUILD_PYTHON (
    for %%P in (
        "E:\Program Files (x86)\python\python.exe"
        "%LocalAppData%\Programs\Python\Python38\python.exe"
        "%LocalAppData%\Programs\Python\Python38-32\python.exe"
    ) do (
        if not defined BUILD_PYTHON (
            "%%P" -c "import PyQt5, PyInstaller" >nul 2>&1 && set "BUILD_PYTHON=%%P"
        )
    )
)
if not defined BUILD_PYTHON (
    echo [ERROR] 未找到同时安装 PyQt5 与 PyInstaller 的 Python，请先安装依赖：
    echo          pip install pyinstaller PyQt5 pillow paddleocr paddlepaddle
    pause
    exit /b 1
)
echo 使用 Python：%BUILD_PYTHON%

REM ---- 临时移走 PyQt5 自带的 VC++ 运行库，避免与系统运行库冲突导致 exe 启动崩溃 ----
set "QTBIN="
for /f "delims=" %%D in ('"%BUILD_PYTHON%" -c "import os,PyQt5;print(os.path.join(os.path.dirname(PyQt5.__file__),'Qt5','bin'))" 2^>nul') do set "QTBIN=%%D"
set "RESTORE_DLLS=0"
if defined QTBIN (
    if exist "%QTBIN%\msvcp140.dll" ( move /Y "%QTBIN%\msvcp140.dll" "%QTBIN%\msvcp140.dll.bak" >nul & set "RESTORE_DLLS=1" )
    if exist "%QTBIN%\msvcp140_1.dll" ( move /Y "%QTBIN%\msvcp140_1.dll" "%QTBIN%\msvcp140_1.dll.bak" >nul & set "RESTORE_DLLS=1" )
    if exist "%QTBIN%\msvcp140_2.dll" ( move /Y "%QTBIN%\msvcp140_2.dll" "%QTBIN%\msvcp140_2.dll.bak" >nul & set "RESTORE_DLLS=1" )
    if exist "%QTBIN%\vcruntime140.dll" ( move /Y "%QTBIN%\vcruntime140.dll" "%QTBIN%\vcruntime140.dll.bak" >nul & set "RESTORE_DLLS=1" )
    if exist "%QTBIN%\vcruntime140_1.dll" ( move /Y "%QTBIN%\vcruntime140_1.dll" "%QTBIN%\vcruntime140_1.dll.bak" >nul & set "RESTORE_DLLS=1" )
)
if "%RESTORE_DLLS%"=="1" echo 已临时移走 PyQt5 自带 VC++ 运行库（打包后还原）

REM ---- 执行打包（--clean 清理缓存，避免旧构建干扰）----
"%BUILD_PYTHON%" -m PyInstaller --clean --onefile --windowed --noconsole ^
--name "异色逮捕计划" ^
--hidden-import paddleocr ^
--hidden-import paddle ^
--hidden-import cv2 ^
--hidden-import numpy ^
--hidden-import PIL ^
--hidden-import scipy ^
--hidden-import sklearn ^
--hidden-import shapely ^
--hidden-import skimage ^
--hidden-import pyclipper ^
--hidden-import lmdb ^
--collect-submodules paddle ^
--collect-binaries paddle ^
--collect-submodules paddleocr ^
--collect-data paddleocr ^
--hidden-import pytesseract ^
--exclude-module tensorflow ^
--exclude-module paddlex ^
--exclude-module keras ^
automation_app.py
set "BUILD_RC=%errorlevel%"

REM ---- 还原 PyQt5 自带 VC++ 运行库（无论打包成功与否都还原）----
if "%RESTORE_DLLS%"=="1" (
    if exist "%QTBIN%\msvcp140.dll.bak" move /Y "%QTBIN%\msvcp140.dll.bak" "%QTBIN%\msvcp140.dll" >nul
    if exist "%QTBIN%\msvcp140_1.dll.bak" move /Y "%QTBIN%\msvcp140_1.dll.bak" "%QTBIN%\msvcp140_1.dll" >nul
    if exist "%QTBIN%\msvcp140_2.dll.bak" move /Y "%QTBIN%\msvcp140_2.dll.bak" "%QTBIN%\msvcp140_2.dll" >nul
    if exist "%QTBIN%\vcruntime140.dll.bak" move /Y "%QTBIN%\vcruntime140.dll.bak" "%QTBIN%\vcruntime140.dll" >nul
    if exist "%QTBIN%\vcruntime140_1.dll.bak" move /Y "%QTBIN%\vcruntime140_1.dll.bak" "%QTBIN%\vcruntime140_1.dll" >nul
    echo 已还原 PyQt5 自带 VC++ 运行库
)

if %BUILD_RC% neq 0 (
    echo [ERROR] 打包失败，请查看上方错误信息。
    pause
    exit /b 1
)

REM ---- 校验产物 ----
if exist "dist\异色逮捕计划.exe" (
    echo.
    echo 构建完成！可执行文件位于 dist 目录下
    echo 文件名称：异色逮捕计划.exe
) else (
    echo [ERROR] 未生成 dist\异色逮捕计划.exe，请检查上方日志。
)

echo.
pause
