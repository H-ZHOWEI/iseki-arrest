@echo off
chcp 65001 > nul
:: ============================================================
::  异色逮捕计划 —— 高级打包脚本
:: ============================================================
:: 说明：
:: 1. OCR 识别功能（识别公告图异色精灵）的依赖是「函数内惰性导入」，
::    PyInstaller 静态扫描抓不到，必须用下面的 --hidden-import / --collect-* 显式声明，
::    否则打包后的 exe 一调用识别就会 ModuleNotFoundError 崩溃。
:: 2. 默认只打包 PaddleOCR（主识别引擎）+ 其 C 扩展依赖，体积可控（exe 约数百 MB）。
::    easyocr / tesseract 作为兜底引擎【默认不打包】（见下方注释），因为 easyocr 会
::    拉入 torch（额外约 700MB+）。若确实需要兜底引擎也打进 exe，取消对应注释行即可。
:: 3. PaddleOCR / easyocr 首次运行会自动联网下载模型到用户缓存目录（~/.paddleocr 等），
::    只需联网一次，之后离线可用。
:: 4. 打包环境需先：pip install pyinstaller pillow paddleocr paddlepaddle
::    （可选兜底）pip install easyocr  /  pip install pytesseract 并安装 Tesseract-OCR
:: ============================================================

pyinstaller --onefile --windowed --noconsole ^
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
--collect-data-files paddleocr ^
--hidden-import pytesseract ^
automation_app.py

:: ===== 可选：把 easyocr 兜底引擎也打进 exe（会额外引入 torch，体积大增）=====
:: 取消下面两行注释即可启用：
:: --hidden-import easyocr ^
:: --collect-submodules easyocr ^

echo.
echo 构建完成！可执行文件位于 dist 目录下
echo 文件名称：异色逮捕计划.exe
echo.
pause
