@echo off
cd /d "%~dp0"
REM ============================================================
REM  异色逮捕计划 打包脚本 (PyInstaller onefile)
REM ============================================================
REM 说明：
REM 1. OCR 识别功能的依赖是函数内惰性导入，PyInstaller 静态扫描抓不到，
REM    必须用 --hidden-import / --collect-* 显式声明，否则打包后的 exe 一调用识别就报 ModuleNotFoundError。
REM 2. 默认只打包 PaddleOCR 主引擎 + 其 C 扩展依赖，体积约数百 MB。
REM    easyocr / tesseract 兜底引擎【默认不打包】（见文件末尾注释），避免拉入 torch 约 700MB+。
REM 3. PaddleOCR 首次运行会联网下载模型到用户缓存目录(~/.paddleocr)，只需联网一次，之后离线可用。
REM 4. 打包前请先安装：pip install pyinstaller pillow paddleocr paddlepaddle
REM    （可选兜底）pip install easyocr  或  pip install pytesseract 并安装 Tesseract-OCR

REM 检查 pyinstaller 是否可用
where pyinstaller > nul 2>&1
if errorlevel 1 (
    echo [ERROR] 未找到 pyinstaller，请先执行：pip install pyinstaller
    pause
    exit /b 1
)

REM 执行打包（--clean 清理缓存，避免旧构建干扰）
pyinstaller --clean --onefile --windowed --noconsole ^
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
automation_app.py

if errorlevel 1 (
    echo [ERROR] 打包失败，请查看上方错误信息。
    pause
    exit /b 1
)

REM 校验产物
if exist "dist\异色逮捕计划.exe" (
    echo.
    echo 构建完成！可执行文件位于 dist 目录下
    echo 文件名称：异色逮捕计划.exe
) else (
    echo [ERROR] 未生成 dist\异色逮捕计划.exe，请检查上方日志。
)

echo.
pause
