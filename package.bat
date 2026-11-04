@echo off
chcp 936 >nul
cd /d "%~dp0"
REM ============================================================
REM  异色逮捕计划 打包脚本 (PyInstaller onefile / spec 驱动)
REM ============================================================
REM 说明：
REM 1. 本软件仅保留「软件自动更新」功能；公告图 OCR 识别功能已移除，不再打包 PaddleOCR 等重型依赖。
REM 2. 本机存在多个 Python，pyinstaller 可能指向缺依赖的解释器导致打包失败。
REM    因此本脚本会「自动探测」第一个同时具备 PyQt5 与 PyInstaller 的 Python 来使用，
REM    不再依赖 PATH 里 pyinstaller 指向谁。
REM 3. PyQt5 自带 msvcp140 / vcruntime140 运行库可能与系统 VC++ 运行库冲突，导致打包出的
REM    exe 一启动就 0xc0000005 崩溃。打包前临时移走这些 DLL，让 exe 改用系统运行库，
REM    打包结束（无论成败）再还原，不影响原 Python 环境。
REM 4. 打包参数集中在「异色逮捕计划.spec」里（图标、单文件、无控制台、体积裁剪），
REM    本脚本不再直接传命令行参数，避免每次重新生成 spec 时把裁剪规则冲掉。
REM 5. 体积裁剪会把不用的 Qt 文件（软件 OpenGL 回退、DevTools 资源、多余语言包、
REM    整套 QML/Quick3D 等）剔除，exe 由 107MB 降到约 87MB。
REM    GitHub 对单个文件限制 100MB，超过就推不上去，所以本脚本最后会做体积校验。
REM 6. 打包前请先安装：pip install pyinstaller PyQt5 PyQtWebEngine
REM 7. 图标文件 application-note.ico 必须与本脚本同目录（图标在 spec 里配置）。

REM ---- 自动定位同时具备 PyQt5 与 PyInstaller 的 Python ----
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
    echo [ERROR] 未找到同时安装 PyQt5 与 PyInstaller 的 Python，请先安装：
    echo          pip install pyinstaller PyQt5 PyQtWebEngine
    pause
    exit /b 1
)
echo 使用 Python：%BUILD_PYTHON%

REM ---- 检查必要文件 ----
if not exist "automation_app.py" (
    echo [ERROR] 未找到 automation_app.py
    pause
    exit /b 1
)
if not exist "application-note.ico" (
    echo [ERROR] 缺少图标文件 application-note.ico，请与本脚本放在同一目录
    pause
    exit /b 1
)
if not exist "异色逮捕计划.spec" (
    echo [ERROR] 缺少打包配置 异色逮捕计划.spec
    pause
    exit /b 1
)

REM ---- 临时移走 PyQt5 自带 VC++ 运行库，避免与系统运行库冲突导致 exe 启动崩溃 ----
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
if "%RESTORE_DLLS%"=="1" echo 已临时移走 PyQt5 自带 VC++ 运行库（稍后还原）

REM ---- 执行打包（--clean 清缓存；参数全部来自 spec）----
"%BUILD_PYTHON%" -m PyInstaller --clean --noconfirm "异色逮捕计划.spec"
set "BUILD_RC=%errorlevel%"

REM ---- 还原 PyQt5 自带 VC++ 运行库（无论打包成功与否都会还原）----
if "%RESTORE_DLLS%"=="1" (
    if exist "%QTBIN%\msvcp140.dll.bak" move /Y "%QTBIN%\msvcp140.dll.bak" "%QTBIN%\msvcp140.dll" >nul
    if exist "%QTBIN%\msvcp140_1.dll.bak" move /Y "%QTBIN%\msvcp140_1.dll.bak" "%QTBIN%\msvcp140_1.dll" >nul
    if exist "%QTBIN%\msvcp140_2.dll.bak" move /Y "%QTBIN%\msvcp140_2.dll.bak" "%QTBIN%\msvcp140_2.dll" >nul
    if exist "%QTBIN%\vcruntime140.dll.bak" move /Y "%QTBIN%\vcruntime140.dll.bak" "%QTBIN%\vcruntime140.dll" >nul
    if exist "%QTBIN%\vcruntime140_1.dll.bak" move /Y "%QTBIN%\vcruntime140_1.dll.bak" "%QTBIN%\vcruntime140_1.dll" >nul
    echo 已还原 PyQt5 自带 VC++ 运行库
)

if %BUILD_RC% neq 0 (
    echo [ERROR] 打包失败，请查看上方错误信息
    pause
    exit /b 1
)

REM ---- 校验产物与体积（GitHub 单文件上限 100MB）----
if not exist "dist\异色逮捕计划.exe" (
    echo [ERROR] 未生成 dist\异色逮捕计划.exe，请检查上方日志
    pause
    exit /b 1
)

echo.
echo 打包完成：dist\异色逮捕计划.exe
for %%F in ("dist\异色逮捕计划.exe") do (
    echo 体积：%%~zF 字节
    if %%~zF GEQ 104857600 (
        echo.
        echo [WARN] 文件超过 100MB，GitHub 会拒绝推送！
        echo        请检查 spec 里的 DROP_NAMES / DROP_PREFIXES 裁剪规则是否被改动。
    )
)

echo.
pause
