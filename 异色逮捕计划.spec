# -*- mode: python ; coding: utf-8 -*-
"""异色逮捕计划 PyInstaller 打包配置（onefile / 无控制台 / 带图标 / 体积裁剪）

体积裁剪说明
------------
本软件是「PyQt5 窗口 + QWebEngineView 显示内嵌 HTML」的结构，不使用 QML / Quick3D、
不需要软件 OpenGL 回退、也不需要 Chromium DevTools 资源。但 PyQt5 的 hook 会把整个
Qt5 目录（约 96MB）都收集进来，导致 exe 膨胀到 107MB，超过 GitHub 单文件 100MB 限制。
下面 DROP_* 列表把这些用不到的重型文件剔除，exe 可压到约 87MB。
若后续新增功能用到被剔除的模块，删掉对应条目即可。
"""

import os

# ---- 需要剔除的单个文件（按文件名匹配，小写）----
DROP_NAMES = {
    # 软件 OpenGL 回退（QtWebEngine 在 Windows 上走 ANGLE，即 libGLESv2 + d3dcompiler）
    'opengl32sw.dll',
    # Chromium 开发者工具资源（不打开 DevTools 就用不到）
    'qtwebengine_devtools_resources.pak',
    # 用不到的平台插件
    'qminimal.dll', 'qoffscreen.dll', 'qwebgl.dll',
    # 用不到的 Qt 模块
    # 注意：qt5quickwidgets.dll 不能删！Qt5WebEngineWidgets.dll 静态导入它，
    # 删掉后 import QtWebEngineWidgets 会直接报
    # "DLL load failed while importing QtWebEngineWidgets: 找不到指定的模块"
    'qt5xmlpatterns.dll', 'qt5remoteobjects.dll', 'qt5bluetooth.dll',
    'qt5nfc.dll', 'qt5test.dll', 'qt5quicktest.dll', 'qt5sql.dll',
    'qt5sensors.dll', 'qt5serialport.dll', 'qt5webview.dll',
    'qt5positioningquick.dll',
    'qt5quick3d.dll', 'qt5quick3drender.dll', 'qt5quick3druntimerender.dll',
    'qt5quick3dassetimport.dll', 'qt5quick3dutils.dll',
    'qt5quickparticles.dll', 'qt5quickshapes.dll',
}

# ---- 需要整目录剔除的前缀（统一按正斜杠、小写匹配）----
# qml 目录下的 QtQuick / Quick3D / Controls 是给 QML 界面用的，本项目是纯 Widgets + HTML
DROP_PREFIXES = (
    'pyqt5/qt5/qml/',
)

# ---- Chromium 语言包只保留常用的几个（53 个语言包约 4.7MB）----
KEEP_LOCALES = {'zh-cn.pak', 'zh-tw.pak', 'en-us.pak'}


def _should_drop(dest):
    d = dest.replace('\\', '/').lower()
    base = d.rsplit('/', 1)[-1]
    if base in DROP_NAMES:
        return True
    for pre in DROP_PREFIXES:
        if d.startswith(pre):
            return True
    if '/qtwebengine_locales/' in d and base not in KEEP_LOCALES:
        return True
    return False


a = Analysis(
    ['automation_app.py'],
    pathex=[],
    binaries=[],
    datas=[('application-note.ico', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

# 应用体积裁剪（binaries 与 datas 都要过滤，Qt 的 dll/pak 分别落在这两处）
_before_b = len(a.binaries)
_before_d = len(a.datas)
a.binaries = [x for x in a.binaries if not _should_drop(x[0])]
a.datas = [x for x in a.datas if not _should_drop(x[0])]
print('[trim] binaries %d -> %d, datas %d -> %d'
      % (_before_b, len(a.binaries), _before_d, len(a.datas)))

# ---- 防错保险：这些文件是运行时必需的，裁掉任何一个都会导致
#      "DLL load failed while importing QtWebEngineWidgets" 之类的启动崩溃，
#      所以这里做一次硬校验，缺了就让打包直接失败，而不是打出不能用的 exe。
REQUIRED_FILES = {
    # PyQt5 的 QtWebEngine 导入链
    'qt5webenginewidgets.dll', 'qt5webenginecore.dll', 'qt5webengine.dll',
    'qt5webchannel.dll', 'qt5quickwidgets.dll', 'qt5quick.dll', 'qt5qml.dll',
    'qt5qmlmodels.dll', 'qt5positioning.dll', 'qt5network.dll',
    'qt5widgets.dll', 'qt5gui.dll', 'qt5core.dll', 'qt5printsupport.dll',
    # Chromium 子进程与渲染资源
    'qtwebengineprocess.exe', 'libegl.dll', 'libglesv2.dll',
    'd3dcompiler_47.dll', 'qtwebengine_resources.pak', 'icudtl.dat',
    'qwindows.dll',
}

_present = set()
for _entry in list(a.binaries) + list(a.datas):
    _present.add(_entry[0].replace('\\', '/').rsplit('/', 1)[-1].lower())

_missing = sorted(REQUIRED_FILES - _present)
if _missing:
    raise SystemExit('[trim][FATAL] 裁剪掉了必需文件，exe 会启动失败: %s' % _missing)
print('[trim] 必需文件校验通过（%d 项）' % len(REQUIRED_FILES))

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='异色逮捕计划',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['application-note.ico'],
)
