#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
洛克王国·异色捕捉大师 - 最终版（含未知精灵）
- 支持未知捕捉：混抓时先记录消耗，后确认具体精灵
- 无属性球统一显示为“无”，且正确计入消耗统计
- 赛季仅在预设库中设置，已捕捉自动继承
- 支持奇遇/非奇遇分组与属性传递模式
- 新增：每日需抓轮数统计（首页顶部），参数可在设置中调整
- 新增：可自定义球种顺序（上下移动）
- 新增：赛季开始/结束时间，动态计算剩余天数，自动切换当前赛季
- 优化：未知捕捉可合并多次消耗记录为一条未知记录
- 新增：已捕捉记录可编辑、删除
- 修复：确认未知记录时移除所有同名待捕捉精灵
- 新增：最终捕捉后必须立即确认精灵，且未确认前禁止继续未知捕捉
- 优化：未知记录确认时按赛季筛选精灵
- 新增：预设精灵库删除功能（二次确认）
- 新增：各模块独立导入导出（标题旁按钮）
- 新增：当前捕捉目标持久化 + 取消目标按钮
- 新增：新增预设精灵自动归属当前赛季
- 新增：“统一球数”与“每只精灵所需球数”双向同步
- 新增：切换 Tab 时记住滚动位置，切回时自动恢复（使用 requestAnimationFrame 消除跳帧）
- 移除：最优捕捉顺序板块，替换为外部链接卡片
- 新增：侧边栏快速导航（每个 Tab 内的小板块快速跳转）
- 优化：侧边栏调大，超链接跳转修复
- 修复：非奇遇精灵图标显示错误（非奇遇应为🍃）
- 新增：捕捉记录增加“获取方式”字段（朋友赠送/赛季特色/自己捕捉），平均消耗统计仅统计“自己捕捉”
- 修复：咕噜球仓库编辑弹窗保存后未自动关闭
- 优化：预设精灵库新增精灵默认显示在最前面，并按赛季降序排列
- 新增：周本精灵成长计划（V1.2.0）
- 优化：成长计划位置调整至“设置”左侧，图标显示修复，添加精灵改为手动输入，新增升星按钮
- 更新：成长计划星级明细（0→5星：2,4,8,16,30合计60），每次周本默认3材料
- 修复：周数计算改为向上取整（ceil）
- 新增：用户当前升星材料数量，升星时自动检查并消耗
- 新增：软件自动更新（检查更新 / 一键自更新，版本号语义化比对防止常见异常）
- 版本：V1.3.1
"""

import sys
import tempfile
import os
import json
from pathlib import Path
from PyQt5 import QtCore, QtWidgets, QtWebEngineWidgets
from PyQt5.QtCore import QUrl, QObject, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtGui import QIcon
from PyQt5.QtWebChannel import QWebChannel
from datetime import datetime, timedelta
import re
import io
import base64
import hashlib
import threading
import subprocess
import time
import urllib.request
import urllib.error
import urllib.parse

# ----------------------------- 版本号（单一来源，自动更新会读取此处）--------------------------------
APP_VERSION = "1.3.12"
DEFAULT_UPDATE_REPO = "https://raw.githubusercontent.com/H-ZHOWEI/iseki-arrest/main/version.json"  # 默认更新清单（仓库根目录 version.json，模仿「喵想奇记」把 exe 提交进仓库 dist/ 的方式）
DEFAULT_DATA_URL = "https://raw.githubusercontent.com/H-ZHOWEI/iseki-arrest/main/data/game_data.json"  # 游戏数据包（预设精灵库 + 赛季），检查更新时顺带同步
GITHUB_API = "https://api.github.com"  # 发布者上传数据包用（单独定义便于测试指向本地 mock）

# ----------------------------- HTML 界面（前端逻辑）--------------------------------
HTML_CONTENT = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover, user-scalable=no">
    <title>洛克王国 异色逮捕大师 - __APP_VERSION__</title>
    <style>
        * {
            box-sizing: border-box;
            -webkit-tap-highlight-color: transparent;
        }
        body {
            background: #eef2e6;
            font-family: system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, sans-serif;
            margin: 0;
            padding: 0 0 80px 0;
            color: #1e2f1c;
        }
        .app-container {
            max-width: 600px;
            margin: 0 auto;
            padding: 16px 12px;
            position: relative;
        }
        .bottom-nav {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: rgba(255, 255, 255, 0.96);
            backdrop-filter: blur(12px);
            display: flex;
            justify-content: space-around;
            padding: 8px 16px 12px;
            border-top: 1px solid #d9e3cf;
            z-index: 100;
            max-width: 600px;
            margin: 0 auto;
        }
        .nav-item {
            flex: 1;
            text-align: center;
            padding: 6px 0;
            border-radius: 40px;
            font-weight: 600;
            font-size: 0.7rem;
            color: #7c9670;
            cursor: pointer;
        }
        .nav-item.active {
            background: #4c9e2c20;
            color: #3d7a24;
        }
        .card {
            background: rgba(255, 255, 255, 0.96);
            border-radius: 28px;
            box-shadow: 0 6px 14px rgba(0, 20, 0, 0.05);
            padding: 18px 16px;
            margin-bottom: 20px;
            border: 1px solid #d9e3cf;
            scroll-margin-top: 16px;
        }
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            margin-bottom: 16px;
            gap: 8px;
        }
        .card-header h2 {
            margin: 0;
            font-size: 1.35rem;
            font-weight: 700;
            background: linear-gradient(135deg, #2b6e2f, #4c9e2c);
            background-clip: text;
            -webkit-background-clip: text;
            color: transparent;
        }
        .card-header .header-actions {
            display: flex;
            gap: 4px;
            flex-wrap: wrap;
        }
        .badge {
            background: #eef2e9;
            padding: 4px 12px;
            border-radius: 40px;
            font-size: 0.7rem;
            font-weight: 500;
        }
        .flex-between {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
        }
        .tab-content {
            display: none;
        }
        .tab-content.active-tab {
            display: block;
        }
        .total-gap-panel {
            background: #fff1df;
            border-radius: 28px;
            padding: 16px;
            margin-bottom: 20px;
            border-left: 8px solid #f5bc70;
        }
        .order-controls {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-top: 8px;
            margin-bottom: 8px;
        }
        .gap-number {
            font-weight: 800;
            color: #c25d2e;
        }
        .spirit-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
            gap: 12px;
            margin-top: 8px;
        }
        .spirit-card {
            background: #fefef9;
            border-radius: 24px;
            padding: 12px;
            border-left: 5px solid #8fc96e;
            transition: 0.1s;
            box-shadow: 0 2px 6px rgba(0,0,0,0.03);
            cursor: pointer;
            position: relative;
        }
        .spirit-card.highlight {
            background: #fff0cc;
            border-left-color: #f5a623;
            box-shadow: 0 0 0 2px #f5a623;
        }
        .spirit-card.selected-delete {
            background: #ffe0db;
            border-left-color: #c23d2b;
            opacity: 0.8;
        }
        .spirit-name {
            font-weight: 700;
            font-size: 0.95rem;
            margin-bottom: 6px;
            word-break: break-word;
        }
        .spirit-attrs {
            font-size: 0.7rem;
            background: #eef2e4;
            display: inline-block;
            padding: 2px 10px;
            border-radius: 20px;
            margin-bottom: 8px;
        }
        .match-badge {
            font-size: 0.65rem;
            background: #e0f0d8;
            border-radius: 16px;
            padding: 3px 8px;
            display: inline-block;
            margin: 4px 0;
        }
        .capture-check {
            display: flex;
            gap: 8px;
            margin-top: 8px;
            font-size: 0.7rem;
            flex-wrap: wrap;
        }
        .edit-need-small {
            width: 70px;
            padding: 4px 6px;
            font-size: 0.7rem;
            margin-left: 4px;
        }
        .consumption-summary {
            font-size: 0.65rem;
            background: #f0f4ea;
            border-radius: 16px;
            padding: 4px 8px;
            margin-top: 6px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
        }
        .consumption-detail {
            font-size: 0.65rem;
            background: #e6efde;
            border-radius: 16px;
            padding: 6px 8px;
            margin-top: 4px;
            display: none;
        }
        .balls-grid {
            display: grid;
            grid-template-columns: repeat(6, 1fr);  /* 从 repeat(auto-fill, minmax(100px, 1fr)) 改为固定6列 */
            gap: 12px;
            margin-top: 8px;
        }
        .ball-card {
            background: #fef9ef;
            border-radius: 20px;
            padding: 10px 6px;
            text-align: center;
            cursor: pointer;
            transition: 0.1s;
            border: 1px solid #e2e8d5;
            position: relative;
        }
        .ball-card .move-buttons {
            display: flex;
            justify-content: center;
            gap: 4px;
            margin-top: 4px;
        }
        .ball-card .move-buttons button {
            background: #eef2e6;
            border: 1px solid #cbdcc0;
            border-radius: 12px;
            padding: 0 6px;
            font-size: 0.7rem;
            cursor: pointer;
        }
        .ball-name {
            font-weight: 700;
            font-size: 0.85rem;
        }
        .ball-attrs {
            font-size: 0.7rem;
            color: #5a7a4a;
            margin: 4px 0;
        }
        .ball-stock {
            font-size: 0.75rem;
            background: #eef2e4;
            display: inline-block;
            padding: 2px 8px;
            border-radius: 20px;
        }
        .preset-scroll {
            max-height: 320px;
            overflow-y: auto;
            padding-right: 4px;
        }
        .preset-item {
            background: #f4f7ef;
            border-radius: 20px;
            padding: 8px 12px;
            margin-bottom: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .search-box {
            width: 100%;
            padding: 8px 14px;
            border-radius: 40px;
            border: 1px solid #cbdcc0;
            margin-bottom: 12px;
        }
        .synthesis-log {
            max-height: 200px;
            overflow-y: auto;
            background: #f4f7ef;
            border-radius: 20px;
            padding: 8px;
            font-size: 0.75rem;
            margin-top: 10px;
        }
        .captured-item {
            background: #eef3e8;
            border-radius: 20px;
            padding: 10px;
            margin-bottom: 8px;
            font-size: 0.85rem;
            position: relative;
        }
        .captured-item .captured-actions {
            margin-top: 8px;
            display: flex;
            gap: 6px;
            flex-wrap: wrap;
        }
        .avg-stats {
            background: #eef2e9;
            border-radius: 20px;
            padding: 8px 12px;
            margin-bottom: 16px;
            font-size: 0.75rem;
        }
        button {
            background: #eef2e6;
            border: none;
            border-radius: 40px;
            padding: 8px 16px;
            font-weight: 600;
            font-size: 0.8rem;
            cursor: pointer;
        }
        button.primary {
            background: #4c9e2c;
            color: white;
        }
        button.danger {
            background: #f9e0db;
            color: #c23d2b;
        }
        button.small {
            padding: 4px 12px;
            font-size: 0.7rem;
        }
        input, select {
            background: #f9fbf5;
            border: 1px solid #cbdcc0;
            border-radius: 24px;
            padding: 8px 12px;
            font-size: 0.85rem;
        }
        .modal {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
        }
        .modal-content {
            background: white;
            border-radius: 32px;
            max-width: 340px;
            width: 90%;
            padding: 20px;
            max-height: 80vh;
            overflow-y: auto;
        }
        .highlight-ball {
            background: #fff0cc !important;
            border: 2px solid #f5a623 !important;
        }
        .chain-step {
            background: #fff3e0;
            border-radius: 20px;
            padding: 6px 12px;
            margin: 4px 0;
            font-size: 0.8rem;
        }
        .json-export-area {
            background: #f4f7ef;
            border-radius: 20px;
            padding: 8px;
            margin-top: 8px;
        }
        textarea {
            width: 100%;
            font-size: 0.7rem;
            font-family: monospace;
        }
        .log-detail {
            margin-top: 6px;
            border-top: 1px dashed #cbdcc0;
            padding-top: 6px;
            font-size: 0.7rem;
        }
        .date-filter {
            display: flex;
            gap: 8px;
            align-items: center;
            margin-bottom: 12px;
        }
        .delete-mode-tip {
            background: #ffe0db;
            border-radius: 20px;
            padding: 6px 12px;
            margin-bottom: 12px;
            font-size: 0.7rem;
            text-align: center;
        }
        .lock-badge {
            background: #ffd966;
            border-radius: 20px;
            padding: 2px 8px;
            font-size: 0.7rem;
            margin-left: 6px;
        }
        .synthesis-btn-area {
            margin-top: 16px;
            text-align: center;
        }
        .json-textarea {
            font-size: 0.65rem;
            white-space: pre-wrap;
            word-break: break-all;
            background: #faf9f2;
            border-radius: 16px;
            padding: 8px;
            margin-top: 8px;
            max-height: 300px;
            overflow: auto;
        }
        .record-entry {
            background: #f9f7ef;
            border-radius: 20px;
            padding: 12px;
            margin-bottom: 12px;
            border: 1px solid #e2e8d5;
        }
        .remove-record {
            background: none;
            color: #c23d2b;
            padding: 2px 8px;
            font-size: 0.7rem;
        }
        .season-group {
            margin-bottom: 20px;
            border-left: 4px solid #8fc96e;
            background: #fafef7;
            border-radius: 20px;
            overflow: hidden;
        }
        .season-header {
            background: #eef2e6;
            padding: 8px 12px;
            font-weight: bold;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .season-content {
            padding: 8px;
            display: block;
        }
        .season-content.collapsed {
            display: none;
        }
        .season-select {
            max-height: 200px;
            overflow-y: auto;
        }
        .import-export-buttons {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 12px;
            justify-content: center;
        }
        .import-export-buttons button {
            font-size: 0.7rem;
            padding: 4px 8px;
        }
        .paste-import-area {
            background: #f4f7ef;
            border-radius: 20px;
            padding: 12px;
            margin-top: 16px;
        }
        .group-mode-buttons {
            display: flex;
            gap: 8px;
            margin-bottom: 12px;
            flex-wrap: wrap;
        }
        .group-mode-btn {
            flex: 1;
            text-align: center;
            padding: 6px;
            border-radius: 40px;
            background: #eef2e6;
            cursor: pointer;
            font-size: 0.75rem;
        }
        .group-mode-btn.active {
            background: #4c9e2c;
            color: white;
        }
        .spirit-group-tabs {
            display: flex;
            gap: 8px;
            margin-bottom: 12px;
            border-bottom: 1px solid #cbdcc0;
        }
        .group-tab {
            padding: 6px 12px;
            cursor: pointer;
            border-radius: 20px 20px 0 0;
            background: #eef2e6;
        }
        .group-tab.active {
            background: #4c9e2c;
            color: white;
        }
        .stat-badge {
            font-size: 0.7rem;
            background: rgba(0, 20, 0, 0.05);
            border-radius: 20px;
            padding: 2px 8px;
            margin-left: 8px;
        }
        .unknown-card {
            background: #fff8e7;
            border-left: 5px solid #f5a623;
            margin-bottom: 12px;
            border-radius: 20px;
            padding: 12px;
        }
        .unknown-actions button {
            margin-right: 6px;
        }
        .settings-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }
        .settings-grid label {
            font-size: 0.8rem;
            font-weight: 500;
            display: block;
            margin-bottom: 4px;
        }
        .settings-grid input, .settings-grid select {
            width: 100%;
        }
        .season-date-inputs {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }
        .season-date-inputs label {
            font-size: 0.75rem;
        }
        .season-date-inputs input {
            width: auto;
            flex: 1;
            min-width: 120px;
        }
        .recommend-content {
            display: none;
        }
        .recommend-content.open {
            display: block;
        }
        .toggle-recommend-btn {
            margin-left: 8px;
            font-size: 0.7rem;
        }
        .header-actions button {
            font-size: 0.65rem;
            padding: 2px 8px;
        }
        /* 侧边栏样式 - 调大 */
        .tab-sidebar {
            position: fixed;
            right: 12px;
            top: 50%;
            transform: translateY(-50%);
            z-index: 90;
            background: rgba(255,255,255,0.92);
            backdrop-filter: blur(10px);
            border-radius: 30px;
            padding: 12px 8px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.1);
            border: 1px solid #d9e3cf;
            display: flex;
            flex-direction: column;
            gap: 8px;
            max-height: 70vh;
            overflow-y: auto;
        }
        .tab-sidebar a {
            display: block;
            padding: 6px 14px;
            border-radius: 24px;
            font-size: 0.8rem;
            color: #5a7a4a;
            text-decoration: none;
            text-align: center;
            white-space: nowrap;
            font-weight: 600;
            transition: 0.15s;
            cursor: pointer;
            line-height: 1.4;
            letter-spacing: 0.3px;
        }
        .tab-sidebar a:hover {
            background: #4c9e2c20;
            color: #3d7a24;
        }
        .tab-sidebar a.active {
            background: #4c9e2c;
            color: white;
        }
        .link-card {
            background: linear-gradient(135deg, #e8f5e9, #c8e6c9);
            border-radius: 28px;
            padding: 18px 16px;
            margin-bottom: 20px;
            border: 1px solid #a5d6a7;
            text-align: center;
        }
        .link-card a {
            display: inline-block;
            background: #2b6e2f;
            color: white;
            padding: 12px 28px;
            border-radius: 40px;
            text-decoration: none;
            font-weight: 700;
            font-size: 1.1rem;
            box-shadow: 0 4px 8px rgba(43,110,47,0.3);
            transition: 0.2s;
            cursor: pointer;
        }
        .link-card a:hover {
            background: #1e4f21;
            transform: scale(1.02);
        }
        .link-card .sub {
            margin-top: 8px;
            font-size: 0.75rem;
            color: #3d7a24;
        }
        /* 侧边栏适配小屏 */
        @media (max-width: 480px) {
            .tab-sidebar {
                right: 4px;
                padding: 8px 4px;
            }
            .tab-sidebar a {
                font-size: 0.7rem;
                padding: 4px 10px;
            }
        }
        /* 获取方式标签 */
        .capture-method {
            font-size: 0.7rem;
            background: #e0e7ff;
            border-radius: 12px;
            padding: 2px 8px;
            display: inline-block;
            margin-left: 6px;
        }
        /* 成长计划样式 */
        .growth-spirit-item {
            background: #f6faf5;
            border-radius: 20px;
            padding: 12px;
            margin-bottom: 10px;
            border-left: 5px solid #8fc96e;
        }
        .growth-spirit-item .row {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 8px;
            margin-top: 6px;
        }
        .growth-spirit-item .row label {
            font-size: 0.75rem;
            font-weight: 500;
            color: #3d5a3d;
            min-width: 60px;
        }
        .growth-spirit-item .row .value {
            font-weight: 600;
            color: #1e3a1e;
        }
        .growth-summary {
            background: #fff5e6;
            border-radius: 20px;
            padding: 12px 16px;
            margin-top: 12px;
            border-left: 6px solid #f5a623;
            font-weight: 600;
        }
        .growth-materials-display {
            background: #e8f0e6;
            border-radius: 16px;
            padding: 8px 12px;
            display: flex;
            align-items: center;
            gap: 12px;
            flex-wrap: wrap;
        }
        .growth-materials-display label {
            font-size: 0.8rem;
            font-weight: 600;
            color: #2b4a2b;
        }
        .growth-materials-display input {
            width: 80px;
            padding: 4px 8px;
            font-size: 0.85rem;
        }
        .growth-materials-display .hint {
            font-size: 0.7rem;
            color: #5a7a4a;
        }
        .spirit-card .category-note {
            font-size: 0.7rem;
            color: #5a7a4a;
            background: #f4f8f0;
            border-radius: 12px;
            padding: 3px 10px;
            margin: 4px 0;
            display: inline-block;
        }
        .spirit-card .category-badge {
            background: #e8f0e6;
            border-radius: 12px;
            padding: 2px 10px;
            font-size: 0.7rem;
            display: inline-block;
            margin: 2px 0;
        }
    </style>
</head>
<body>
<div class="app-container" id="app">
    <!-- Tab1: 捕捉规划 -->
    <div id="tab1" class="tab-content active-tab">
        <!-- 每日需抓轮数统计 -->
        <div class="card" id="dailyStatsCard">
            <div class="flex-between">
                <span style="font-weight:700; font-size:1.1rem;">📊 每日需抓轮数</span>
                <span class="badge" id="dailyRoundValue" style="font-size:1rem;">计算中...</span>
            </div>
            <div style="font-size:0.8rem; color:#5a7a4a; margin-top:4px;">
                基于设置：轮数 <span id="roundBallsDisplay">240</span>，当前赛季剩余 <span id="seasonDaysDisplay">56</span>天，人数 <span id="peopleDisplay">2</span>，每只所需球 <span id="ballsPerSpiritDisplay">1200</span>
            </div>
            <!-- 在 dailyStatsCard 下方添加 -->
            <div id="categoryNotesContainer" style="margin-top: -10px; margin-bottom: 16px;"></div>
        </div>

        <!-- 超链接卡片 -->
        <div class="link-card" id="link-card">
            <div style="font-size:1.2rem; font-weight:700; margin-bottom:6px;">🎯 前往异色捕捉查询</div>
            <a href="https://qize-roco-d4gmue7dt620963b7-1455001032.tcloudbaseapp.com/s3-mix/"
id="externalLink">🔗 打开查询工具</a>
            <div class="sub">点击在新窗口打开，快速查询异色精灵捕捉信息</div>
        </div>

        <div class="total-gap-panel" id="card-total-gap">
            <div style="font-weight: 700; margin-bottom: 8px;">📊 动态总缺口分析 (优先消耗库存多的球)</div>
            <div id="totalGapContent">计算中...</div>
            <button id="startCaptureBtn" class="primary" style="margin-top: 16px; width: 100%;">🎯 开始捕捉 (记录初始库存)</button>
            <div id="captureStatus" style="font-size:0.7rem; margin-top: 8px;"></div>
        </div>

        <div class="card" id="card-target">
            <div class="card-header">
                <h2>🎯 当前捕捉目标</h2>
                <div class="header-actions">
                    <button id="clearTargetBtn" class="small danger">✖️ 取消目标</button>
                </div>
            </div>
            <div id="activeTargetSelector" style="margin-bottom: 8px;">
                <select id="selectTargetSpirit" style="width:100%"></select>
                <button id="confirmTargetBtn" class="primary" style="margin-top: 6px; width:100%">确认捕捉目标</button>
            </div>
            <div id="targetHighlightInfo" style="font-size:0.75rem; background:#fff9e8; border-radius:16px; padding:8px;"></div>
        </div>

        <div class="card" id="card-spirits">
            <div class="card-header">
                <h2>✨ 待捕捉异色精灵 <span id="spiritStats" class="stat-badge"></span></h2>
                <div>
                    <button id="globalSetNeedBtn" class="small">🔢 统一设置球数</button>
                    <button id="toggleDeleteModeBtn" class="small danger" style="margin-left:4px;">🗑️ 删除模式</button>
                    <button id="historyRecordBtn" class="small primary" style="margin-left:4px;">📜 补录历史消耗</button>
                </div>
            </div>
            <div class="spirit-group-tabs" id="spiritDisplayTabs">
                <div class="group-tab active" data-display="all">全部</div>
                <div class="group-tab" data-display="wonder">✨ 奇遇</div>
                <div class="group-tab" data-display="normal">🍃 非奇遇</div>
            </div>
            <div id="deleteModeTip" style="display:none;" class="delete-mode-tip">
                ⚠️ 删除模式已开启，点击卡片可选中/取消，点击下方按钮确认删除。
            </div>
            <div id="spiritGridContainer" class="spirit-grid"></div>
            <div id="deleteModeBar" style="display:none; margin-top:12px; text-align:center;">
                <button id="confirmDeleteSpiritsBtn" class="danger small">确认删除选中精灵</button>
                <button id="cancelDeleteModeBtn" class="small">取消删除模式</button>
            </div>
            <hr>
            <div class="flex-between"><strong>➕ 新增目标 (从预设库)</strong><span style="font-size:0.7rem;">已添加的不重复</span></div>
            <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px;">
                <select id="selectPresetSpirit" style="flex:3">
                    <option value="">-- 选择预设精灵 --</option>
                </select>
                <button id="addSpiritFromPresetBtn" class="primary">添加</button>
            </div>
            <hr>
            <div style="margin-top: 12px; background: #fff8e7; border-radius: 20px; padding: 12px;" id="card-unknown">
                <div style="font-weight: 700; margin-bottom: 6px;">🎲 未知捕捉（混抓）</div>
                <div style="font-size: 0.8rem; margin-bottom: 8px;">先记录消耗，之后确认具体精灵（支持所有球种）</div>
                <button id="unknownCaptureBtn" class="primary small">📝 记录未知捕捉消耗</button>
            </div>
        </div>
    </div>

    <!-- Tab2: 已捕捉 -->
    <div id="tab2" class="tab-content">
        <div class="card" id="card-captured">
            <div class="card-header">
                <h2>📜 已捕捉记录</h2>
                <div class="header-actions">
                    <button id="exportCapturedBtn" class="small">📤 导出</button>
                    <button id="importCapturedBtn" class="small">📥 导入</button>
                    <button id="addCapturedRecordBtn" class="small primary">➕ 新增</button>
                </div>
            </div>
            <div class="flex-between" style="margin-bottom: 12px;">
                <label>🏆 赛季筛选：</label>
                <select id="seasonFilterSelect" class="season-select" style="flex:2; max-height: 200px; overflow-y: auto;"></select>
            </div>
            <div id="avgStatsContainer" class="avg-stats">加载中...</div>
            <div id="capturedListContainer">暂无记录</div>
        </div>

        <div class="card" id="card-unknown-list">
            <div class="card-header">
                <h2>❓ 未知记录（待确认）</h2>
                <div class="header-actions">
                    <button id="exportUnknownBtn" class="small">📤 导出</button>
                    <button id="importUnknownBtn" class="small">📥 导入</button>
                    <span class="badge" id="unknownCount">0</span>
                </div>
            </div>
            <div id="unknownListContainer">暂无未知记录</div>
        </div>
    </div>

    <!-- Tab3: 成长计划 -->
    <div id="tab3" class="tab-content">
        <div class="card">
            <div class="card-header">
                <h2>📈 周本精灵成长计划</h2>
                <div class="header-actions">
                    <button id="addGrowthSpiritBtn" class="small primary">+ 添加精灵</button>
                </div>
            </div>
            <div style="background:#f4f7ef; border-radius:20px; padding:12px; margin-bottom:16px;">
                <div style="display:flex; flex-direction:column; gap:4px;">
                    <span><strong>当前赛季剩余天数：</strong><span id="growthRemainingDays">--</span> 天</span>
                    <span><strong>剩余周数：</strong><span id="growthRemainingWeeks">--</span> 周</span>
                    <span><strong>每周可获材料：</strong><span id="growthWeeklyMaterials">9</span> 个</span>
                    <span><strong>满星合计需：</strong>60 材料</span>
                </div>
                <div class="growth-materials-display" style="margin-top:10px;">
                    <label>📦 当前升星材料：</label>
                    <button id="growthMaterialsDec3" class="small" style="padding:4px 8px;">-3</button>
                    <input type="number" id="growthCurrentMaterials" value="0" min="0" style="width:80px;">
                    <button id="growthMaterialsInc3" class="small" style="padding:4px 8px;">+3</button>
                    <button id="growthSaveMaterialsBtn" class="small primary">保存</button>
                    <span class="hint">升星时将自动消耗</span>
                </div>
            </div>
            <div id="growthSpiritList"></div>
            <div id="growthSummary" class="growth-summary">加载中...</div>
        </div>
    </div>

    <!-- Tab4: 设置 -->
    <div id="tab4" class="tab-content">
        <div class="card" id="card-warehouse">
            <div class="card-header">
                <h2>🎒 咕噜球仓库</h2>
                <div class="header-actions">
                    <button id="exportWarehouseBtn" class="small">📤 导出</button>
                    <button id="importWarehouseBtn" class="small">📥 导入</button>
                    <button id="addBallTypeBtn" class="small">+ 添加球种</button>
                </div>
            </div>
            <div id="ballsGridContainer" class="balls-grid"></div>
            <div class="synthesis-btn-area">
                <button id="synthesisInWarehouseBtn" class="primary">⚗️ 合成属性球 (消耗普通咕噜球)</button>
            </div>
            <div class="badge" style="margin-top:8px;">💡 点击球种可修改库存。捕捉进行中时修改库存会同步更新快照，影响后续消耗计算。</div>
            <div class="badge" style="margin-top:4px;">💡 点击 ↑/↓ 可调整球种顺序，顺序会同步到所有下拉列表。</div>
        </div>

        <div class="card" id="card-battle">
            <div class="card-header"><h2>⚔️ 战斗·购买获得</h2></div>
            <div style="display: flex; flex-wrap: wrap; gap: 10px;">
                <select id="battleBallSelect" style="flex:2"></select>
                <input type="number" id="battleAmount" value="1" min="1" style="flex:1">
                <button id="doBattleGetBtn" class="primary">✨ 获得 (不消耗资源)</button>
            </div>
            <div class="date-filter">
                <label style="font-size:0.7rem;">📅 显示日期：</label>
                <input type="date" id="recordDateFilter" style="flex:1">
                <button id="resetDateFilterBtn" class="small">今天</button>
            </div>
            <div class="synthesis-log"><div style="font-weight:600;">📋 获得记录</div><div id="battleLogList">暂无</div></div>
        </div>

        <div class="card" id="card-preset">
            <div class="card-header">
                <h2>📚 预设精灵库</h2>
                <div class="header-actions">
                    <button id="exportPresetBtn" class="small">📤 导出</button>
                    <button id="importPresetBtn" class="small">📥 导入</button>
                    <button id="addPresetSpiritBtn" class="small">+ 新增</button>
                </div>
            </div>
            <input type="text" id="presetSearchInput" class="search-box" placeholder="🔍 搜索精灵名称或属性">
            <div id="presetSpiritsContainer" class="preset-scroll"></div>
            <div class="badge" style="margin-top:8px;">💡 编辑预设精灵时可设置【赛季】和【奇遇/非奇遇】类型。保存后自动同步所有同名记录。</div>
        </div>

        <div class="card" id="card-seasons">
            <div class="card-header">
                <h2>🏆 赛季管理</h2>
                <div class="header-actions">
                    <button id="exportSeasonsBtn" class="small">📤 导出</button>
                    <button id="importSeasonsBtn" class="small">📥 导入</button>
                    <button id="addSeasonBtn" class="small">+ 新增</button>
                </div>
            </div>
            <div id="seasonsListContainer" class="preset-scroll" style="max-height: 200px;"></div>
            <div class="badge" style="margin-top:8px;">💡 每个赛季可设置专属精灵分类，在新增预设精灵时选择。</div>
        </div>

        <div class="card" id="card-stats">
            <div class="card-header"><h2>📐 捕捉统计设置</h2></div>
            <div class="settings-grid">
                <div>
                    <label>一轮咕噜球数</label>
                    <input type="number" id="settingRoundBalls" value="240" min="1">
                </div>
                <div>
                    <label>人数</label>
                    <input type="number" id="settingPeople" value="2" min="1">
                </div>
                <div>
                    <label>每只精灵所需球数</label>
                    <input type="number" id="settingBallsPerSpirit" value="1200" min="1">
                </div>
                <div>
                    <label>当前赛季</label>
                    <select id="settingCurrentSeason"></select>
                </div>
            </div>
            <div class="badge" style="margin-top:8px;">💡 这些设置将用于首页“每日需抓轮数”的计算，并影响“统一设置球数”的默认值。赛季的剩余天数根据开始/结束日期自动计算，当前赛季会自动切换。</div>
        </div>

        <!-- 软件更新 -->
        <div class="card" id="card-update">
            <div class="card-header">
                <h2 id="updateCardTitle" style="cursor:default; user-select:none;">🔄 软件更新</h2>
                <span id="publisherBadge" style="display:none; font-size:0.68rem; color:#2b6e2f; background:#eef7e4; border:1px solid #cfe0bf; border-radius:10px; padding:2px 8px;">🔓 发布者模式</span>
            </div>
            <div class="settings-grid">
                <div style="grid-column: 1 / -1;">
                    <label>GitHub 仓库（仅走 GitHub Releases 时填写；本软件用下面的 version.json 清单发布，日常留空即可）</label>
                    <input type="text" id="updateGithubRepo" class="search-box" style="width:100%;" placeholder="H-ZHOWEI/iseki-arrest">
                </div>
                <div style="grid-column: 1 / -1;">
                    <label>更新清单直链（version.json，默认已填仓库内清单；检查更新以此框为准）</label>
                    <input type="text" id="updateManifestUrl" class="search-box" style="width:100%;" placeholder="https://raw.githubusercontent.com/H-ZHOWEI/iseki-arrest/main/version.json">
                </div>
            </div>
            <div style="display:flex; gap:8px; margin-top:10px; align-items:center; flex-wrap:wrap;">
                <button id="checkUpdateBtn" class="primary small">检查更新</button>
                <button id="resetUpdateUrlBtn" class="small">恢复默认更新地址</button>
                <span id="updateStatus" style="font-size:0.75rem; color:#5a7a4a;"></span>
            </div>

            <div style="border-top:1px dashed #cfe0bf; margin-top:14px; padding-top:12px;">
                <label style="font-weight:600;" id="gameDataLabel">📦 游戏数据（预设精灵库 / 赛季）</label>
                <div style="margin-top:8px;">
                    <label>数据包直链（留空用默认；国内网络拉不动时可在地址前加 https://ghproxy.net/ 走加速，不要用 jsDelivr——它会缓存旧内容）</label>
                    <input type="text" id="updateDataUrl" class="search-box" style="width:100%;" placeholder="https://raw.githubusercontent.com/H-ZHOWEI/iseki-arrest/main/data/game_data.json">
                </div>
                <div style="display:flex; gap:8px; margin-top:8px; align-items:center; flex-wrap:wrap;">
                    <button id="syncDataBtn" class="small">检查数据更新</button>
                    <button id="testDataUrlBtn" class="small">测试地址</button>
                    <button id="importDataPackBtn" class="small">从文件导入数据包</button>
                    <span id="dataSyncStatus" style="font-size:0.75rem; color:#5a7a4a;"></span>
                </div>
                <!-- 发布者工具：默认隐藏，在「🔄 软件更新」标题上连点 5 次显示 -->
                <div id="publisherPanel" style="display:none; margin-top:12px; padding:10px 12px; background:#f4f9ec; border:1px solid #dfeacf; border-radius:12px;">
                    <div style="font-size:0.78rem; font-weight:600; color:#2b6e2f; margin-bottom:6px;">🔐 发布者工具（仅本机可见）</div>
                    <div>
                        <label>GitHub Token（需该仓库 Contents 读写权限；只保存在本机，换机器要重填）</label>
                        <input type="password" id="publishToken" class="search-box" style="width:100%;" placeholder="ghp_xxxxxxxx 或 github_pat_xxxxxxxx" autocomplete="off">
                    </div>
                    <div style="display:flex; gap:8px; margin-top:8px; align-items:center; flex-wrap:wrap;">
                        <button id="exportDataPackBtn" class="small">导出数据包（发布用）</button>
                        <button id="publishDataPackBtn" class="small">📤 上传数据包到 GitHub</button>
                        <span id="publishStatus" style="font-size:0.75rem; color:#5a7a4a;"></span>
                    </div>
                    <div style="font-size:0.7rem; color:#7d9870; margin-top:6px; line-height:1.5;">
                        上传会直接提交到仓库 <b>data/game_data.json</b>（分支 main），用户下次检查更新即可收到新赛季。<br>
                        注意：<b>只有「新赛季」及其中的精灵会被推送给用户</b>，给老赛季补精灵不会生效。
                    </div>
                </div>
                <div class="badge" style="margin-top:8px;">
                    💡 数据版本：<b><span id="dataVersionLabel">未同步</span></b>　来源：<span id="dataPackUrlLabel" style="word-break:break-all;">-</span><br>
                    点「检查更新」时<b>先查软件版本，再查有没有新赛季</b>；也可单独点「检查数据更新」。<br>
                    主地址（GitHub raw）拉不动时会<b>自动换 github.com 直链 / ghproxy 系列镜像</b>重试，也可点「测试地址」逐条探测；<b>V1.3.12 起已移除 jsDelivr</b>（它会把清单缓存成 12 小时前的旧内容，导致漏报新版本）。<br>
                    发现新赛季时会<b>弹窗列出清单，由你决定是否更新进来</b>；合并规则：<b>只加新赛季及其中的精灵</b>——<b>已有赛季不参与比对</b>，你原有的赛季、精灵（包括你改过的和手动新增的）一律不动、不删。<br>
                    发布新数据：在本机把赛季和预设精灵维护好 → 点「导出数据包（发布用）」存成 <b>game_data.json</b> → 覆盖仓库 <b>data/game_data.json</b> 并提交，用户下次检查更新就会收到新赛季提示。<br>
                    <span style="color:#8a9a80;">提示：用户只会收到「新赛季」及其精灵，所以给老赛季补精灵不会推送给别人。</span>
                </div>
            </div>
            <div class="badge" style="margin-top:8px;">💡 默认通过仓库根目录的 <b>version.json</b> 清单检查更新，其 <b>download_url</b> 指向仓库内 <b>dist/异色逮捕计划.exe</b>（与「喵想奇记」一致：把 exe 直接提交进仓库）。发布新版时，先把新 exe 放进 <b>dist/</b> 并提交，再更新 <b>version.json</b> 的 version 与 sha256 即可；也可改用 Releases（在仓库 Releases 上传同名 exe 附件）。版本号按语义化比对（如 1.10.0 不会误判小于 1.9.0）。当前版本：<span id="currentVersionLabel">__APP_VERSION__</span></div>
        </div>

        <!-- 成长计划设置 -->
        <div class="card" id="card-growth-settings">
            <div class="card-header"><h2>📈 成长计划设置</h2></div>
            <div class="settings-grid">
                <div>
                    <label>每次周本获得材料数</label>
                    <input type="number" id="growthMaterialsPerRun" value="3" min="1">
                </div>
                <div>
                    <label>每周可打周本次数</label>
                    <input type="number" id="growthRunsPerWeek" value="3" min="1">
                </div>
                <div>
                    <label>每次周本消耗印记数</label>
                    <input type="number" id="growthSealsPerRun" value="1" min="1">
                </div>
                <div>
                    <label style="font-size:0.75rem;">满星材料明细</label>
                    <div style="font-size:0.7rem; background:#eef2e6; border-radius:12px; padding:6px;">
                        1星:2 | 2星:4 | 3星:8 | 4星:16 | 5星:30<br>
                        <strong>合计: 60</strong>
                    </div>
                </div>
            </div>
            <div style="margin-top:12px;">
                <button id="growthSaveSettingsBtn" class="primary small">保存成长设置</button>
            </div>
            <div class="badge" style="margin-top:8px;">💡 修改每次周本获得材料数或每周次数后需点击保存生效。</div>
        </div>

        <!-- 全部数据备份区域 -->
        <div class="card" id="card-full-backup">
            <div class="card-header">
                <h2>💾 全部数据备份</h2>
                <div class="header-actions">
                    <button id="exportAllDataBtn" class="primary small">📤 导出全部数据</button>
                    <button id="importAllDataBtn" class="small">📥 导入全部数据</button>
                </div>
            </div>
            <div class="badge">💡 导出将包含：仓库、预设精灵、待捕捉目标、已捕捉记录、未知记录、赛季、成长计划、战斗记录、统计设置等全部数据。</div>
        </div>

        <!-- 粘贴导入区域 -->
        <div class="card" id="card-paste">
            <div class="card-header"><h2>📋 快速粘贴导入</h2></div>
            <div class="paste-import-area">
                <textarea id="pasteJsonText" rows="3" placeholder="在此粘贴 JSON 文本..."></textarea>
                <div style="display: flex; gap: 8px; margin-top: 8px; align-items: center;">
                    <select id="pasteModuleSelect" style="flex:1;">
                        <option value="captured">✅ 已捕捉记录</option>
                        <option value="warehouse">🎒 仓库数据</option>
                        <option value="preset">📚 预设精灵库</option>
                        <option value="seasons">🏆 赛季数据</option>
                        <option value="unknown">❓ 未知记录</option>
                    </select>
                    <button id="pasteImportBtn" class="primary small">从文本导入</button>
                </div>
                <div class="badge" style="margin-top:8px;">💡 复制任意模块的 JSON 后，选择对应类型，点击按钮即可导入（无需保存文件）。</div>
            </div>
        </div>
    </div>

    <!-- 底部导航 -->
    <div class="bottom-nav">
        <div class="nav-item active" data-tab="tab1">📊 捕捉规划</div>
        <div class="nav-item" data-tab="tab2">✅ 已捕捉</div>
        <div class="nav-item" data-tab="tab3">📈 成长计划</div>
        <div class="nav-item" data-tab="tab4">⚙️ 设置</div>
    </div>

    <!-- 侧边栏（由JS动态注入到每个tab-content中） -->
</div>

<script src="qrc:///qtwebchannel/qwebchannel.js"></script>
<script>
    // ---------- 与 Python 桥接对象 ----------
    let pythonAPI = null;
    const APP_VERSION = "__APP_VERSION__";
    const DEFAULT_UPDATE_REPO = "__DEFAULT_REPO__";
    const DEFAULT_DATA_URL = "__DATA_URL__";   // 游戏数据包（预设精灵库 + 赛季）

    // ---------- 数据结构 ----------
    let ballTypes = []; let inventory = {}; let presetSpirits = []; let spirits = []; let capturedSpirits = [];
    let seasons = [];
    let unknownRecords = [];  // 未知记录 { id, consumptionLogs, capturedAt, status:'pending' }
    let captureSnapshot = null; let lastCaptureStock = null;
    let battleRecords = []; let captureStartDate = null; let activeTargetId = null;
    let deleteMode = false; let selectedDeleteSpiritIds = new Set();
    let nextBallId = 100, nextPresetId = 1000, nextSpiritId = 2000, nextCapturedId = 3000, nextSeasonId = 4000, nextUnknownId = 5000;
    const NEUTRAL_BALL_NAMES = ["普通咕噜球", "高级咕噜球", "捕光球", "国王球", "棱镜球"];
    const STORAGE = { BALLS: 'ball_final', INVENTORY: 'inv_final', PRESET: 'preset_final', SPIRITS: 'target_final', CAPTURED: 'captured_final', SNAPSHOT: 'snap_final', LASTSTOCK: 'laststock_final', BATTLEREC: 'battle_rec_final', STARTDATE: 'start_date_final', ORDERLOCK: 'order_lock_final', LOCKEDORDER: 'locked_order_final', CUSTOMSTART: 'custom_start_final', SEASONS: 'seasons_final', UNKNOWN: 'unknown_final', ACTIVETARGET: 'active_target_final' };
    const GROWTH_STORAGE = 'growth_plan_data';

    let orderLocked = false;
    let lockedOrderIds = [];
    let customStartId = null;
    let currentSeasonFilter = null;
    let currentTransferMode = "all";
    let currentDisplayGroup = "all";

    // ===== 统计设置变量 =====
    let settingRoundBalls = 240;
    let settingPeople = 2;
    let settingBallsPerSpirit = 1200;
    let currentSeasonId = null;

    // ===== 推荐面板折叠状态（已废弃，保留变量以防冲突） =====
    let recommendOpen = false;

    // ===== 滚动位置存储 =====
    if (!window.scrollPositions) window.scrollPositions = {};

    // ===== 成长计划数据 =====
    // 升星所需材料明细: 从0星到1星需2，1→2需4，2→3需8，3→4需16，4→5需30
    // 累计: 0→5 = 60
    const STAR_MATERIALS = [0, 2, 4, 8, 16, 30]; // starIndex: 0->1:2, 1->2:4, 2->3:8, 3->4:16, 4->5:30
    const MAX_STAR = 5;
    const TOTAL_MATERIALS = 60;

    let growthData = {
        materialsPerRun: 3,
        runsPerWeek: 3,
        sealsPerRun: 1,
        currentMaterials: 0,      // 用户当前拥有的升星材料
        spirits: []               // { id, name, currentStar (0-5) }
    };
    let nextGrowthId = 1;

    // ---------- 通用函数 ----------
    function getFirstAttr(spirit) {
        return (spirit.attrs && spirit.attrs.length > 0) ? spirit.attrs[0] : null;
    }
    function isAttributeBall(ball) {
        let a1 = ball.attr1 ? ball.attr1.trim() : "";
        let a2 = ball.attr2 ? ball.attr2.trim() : "";
        return (a1 && a1 !== "无") || (a2 && a2 !== "无");
    }
    function getBallAttrDisplay(ball) {
        let attrs = [];
        if (ball.attr1 && ball.attr1.trim() && ball.attr1.trim() !== "无") attrs.push(ball.attr1.trim());
        if (ball.attr2 && ball.attr2.trim() && ball.attr2.trim() !== "无") attrs.push(ball.attr2.trim());
        if (attrs.length === 0) return "无";
        return attrs.join(" + ");
    }

    function getDefaultBalls() {
        return [
            { id: nextBallId++, name: "普通咕噜球", attr1: "", attr2: "" },
            { id: nextBallId++, name: "高级咕噜球", attr1: "", attr2: "" },
            { id: nextBallId++, name: "光合球", attr1: "草", attr2: "光" },
            { id: nextBallId++, name: "网兜球", attr1: "水", attr2: "翼" },
            { id: nextBallId++, name: "调温球", attr1: "火", attr2: "冰" },
            { id: nextBallId++, name: "淘沙球", attr1: "地", attr2: "虫" },
            { id: nextBallId++, name: "绝缘球", attr1: "电", attr2: "毒" },
            { id: nextBallId++, name: "美妙球", attr1: "萌", attr2: "普通" },
            { id: nextBallId++, name: "好战球", attr1: "武", attr2: "龙" },
            { id: nextBallId++, name: "暗星球", attr1: "幽", attr2: "恶" },
            { id: nextBallId++, name: "变幻球", attr1: "幻", attr2: "机械" },
            { id: nextBallId++, name: "捕光球", attr1: "", attr2: "" },
            { id: nextBallId++, name: "国王球", attr1: "", attr2: "" },
            { id: nextBallId++, name: "棱镜球", attr1: "", attr2: "" }
        ];
    }
    function getDefaultPreset() {
        return [
            { id: nextPresetId++, name: "燃薪虫", attrs: ["草","火"], type: "normal", defaultSeasonId: null },
            { id: nextPresetId++, name: "呼呼猪", attrs: ["冰","地"], type: "normal", defaultSeasonId: null },
            { id: nextPresetId++, name: "月牙雪熊", attrs: ["冰","幻"], type: "wonder", defaultSeasonId: null },
            { id: nextPresetId++, name: "粉星仔", attrs: ["幻"], type: "wonder", defaultSeasonId: null },
            { id: nextPresetId++, name: "粉粉星", attrs: ["电","幻"], type: "wonder", defaultSeasonId: null },
            { id: nextPresetId++, name: "空空颅", attrs: ["幽","幽"], type: "normal", defaultSeasonId: null },
            { id: nextPresetId++, name: "绒仙子", attrs: ["虫","光"], type: "normal", defaultSeasonId: null },
            { id: nextPresetId++, name: "疾光千兽", attrs: ["光","光"], type: "wonder", defaultSeasonId: null },
            { id: nextPresetId++, name: "嗜光嗡嗡", attrs: ["恶","光"], type: "normal", defaultSeasonId: null },
            { id: nextPresetId++, name: "奇丽草", attrs: ["草","草"], type: "normal", defaultSeasonId: null },
            { id: nextPresetId++, name: "格兰球", attrs: ["草","草"], type: "normal", defaultSeasonId: null },
            { id: nextPresetId++, name: "贝瑟", attrs: ["机械","火"], type: "wonder", defaultSeasonId: null }
        ];
    }
    function getDefaultSeasons() {
        const now = new Date();
        const end = new Date(now);
        end.setDate(end.getDate() + 56);
        return [
            { id: nextSeasonId++, name: "S1", order: 1, startDate: now.toISOString().slice(0,10), endDate: end.toISOString().slice(0,10) },
            { id: nextSeasonId++, name: "S2", order: 2, startDate: now.toISOString().slice(0,10), endDate: end.toISOString().slice(0,10) }
        ];
    }

    // ---------- 成长计划加载/保存 ----------
    function loadGrowthData() {
        let raw = localStorage.getItem(GROWTH_STORAGE);
        if (raw) {
            try {
                let data = JSON.parse(raw);
                growthData.materialsPerRun = data.materialsPerRun || 3;
                growthData.runsPerWeek = data.runsPerWeek || 3;
                growthData.sealsPerRun = data.sealsPerRun || 1;
                growthData.currentMaterials = data.currentMaterials || 0;
                growthData.spirits = data.spirits || [];
                let maxId = 0;
                growthData.spirits.forEach(s => { if (s.id > maxId) maxId = s.id; });
                nextGrowthId = maxId + 1;
            } catch (e) {
                console.warn("成长数据解析失败，重置");
                growthData = { materialsPerRun: 3, runsPerWeek: 3, sealsPerRun: 1, currentMaterials: 0, spirits: [] };
                nextGrowthId = 1;
            }
        } else {
            growthData = { materialsPerRun: 3, runsPerWeek: 3, sealsPerRun: 1, currentMaterials: 0, spirits: [] };
            nextGrowthId = 1;
        }
        // 同步设置UI
        document.getElementById("growthMaterialsPerRun").value = growthData.materialsPerRun;
        document.getElementById("growthRunsPerWeek").value = growthData.runsPerWeek;
        document.getElementById("growthSealsPerRun").value = growthData.sealsPerRun;
        document.getElementById("growthCurrentMaterials").value = growthData.currentMaterials;
    }

    function saveGrowthData() {
        localStorage.setItem(GROWTH_STORAGE, JSON.stringify(growthData));
    }

    // 计算从当前星级到满星所需材料（累计）
    function getMaterialsNeeded(currentStar) {
        let total = 0;
        for (let i = currentStar; i < MAX_STAR; i++) {
            total += STAR_MATERIALS[i + 1];
        }
        return total;
    }

    // 获取升到下一星所需材料
    function getNextStarMaterials(currentStar) {
        if (currentStar >= MAX_STAR) return 0;
        return STAR_MATERIALS[currentStar + 1];
    }

    // ---------- 成长计划渲染 ----------
    function renderGrowthPlan() {
        const container = document.getElementById("growthSpiritList");
        const summary = document.getElementById("growthSummary");
        if (!container || !summary) return;

        // 读取设置
        const materialsPerRun = growthData.materialsPerRun;
        const runsPerWeek = growthData.runsPerWeek;
        const sealsPerRun = growthData.sealsPerRun;
        document.getElementById("growthWeeklyMaterials").innerText = materialsPerRun * runsPerWeek;
        document.getElementById("growthCurrentMaterials").value = growthData.currentMaterials;

        // 计算赛季剩余 - 周数向上取整
        let season = null;
        if (currentSeasonId !== null) {
            season = seasons.find(s => s.id === currentSeasonId);
        }
        let remainingDays = 0;
        if (season) {
            remainingDays = getSeasonRemainingDays(season);
        } else if (seasons.length > 0) {
            season = seasons[0];
            remainingDays = getSeasonRemainingDays(season);
        }
        document.getElementById("growthRemainingDays").innerText = remainingDays;
        let remainingWeeks = Math.ceil(remainingDays / 7);
        document.getElementById("growthRemainingWeeks").innerText = remainingWeeks;

        // 每周可获材料
        const weeklyMaterials = materialsPerRun * runsPerWeek;
        let totalWeeklyGain = remainingWeeks * weeklyMaterials;

        // 渲染精灵列表
        let html = "";
        if (growthData.spirits.length === 0) {
            html = "<div style='text-align:center; padding:20px; color:#7c9670;'>暂无精灵，点击“添加精灵”开始规划</div>";
        } else {
            let totalSeals = 0;
            let remainingMaterialsGlobal = growthData.currentMaterials;
            growthData.spirits.forEach((gs, idx) => {
                const currentStar = gs.currentStar || 0;
                const neededMaterials = getMaterialsNeeded(currentStar);
                const nextStarCost = getNextStarMaterials(currentStar);
                const isMaxStar = currentStar >= MAX_STAR;

                // 计算可用材料：当前用户材料 + 周可获材料（按顺序分配）
                let availableForThis = 0;
                let needSeals = 0;
                let weekGain = 0;

                if (isMaxStar) {
                    // 已满星，不需要材料
                    availableForThis = 0;
                    weekGain = 0;
                    needSeals = 0;
                } else {
                    // 先使用当前用户剩余材料
                    let usedFromCurrent = Math.min(remainingMaterialsGlobal, neededMaterials);
                    remainingMaterialsGlobal -= usedFromCurrent;
                    let remainingNeed = neededMaterials - usedFromCurrent;

                    // 再用周可获材料
                    let usedFromWeekly = Math.min(totalWeeklyGain, remainingNeed);
                    totalWeeklyGain -= usedFromWeekly;
                    weekGain = usedFromWeekly;
                    remainingNeed -= usedFromWeekly;

                    // 剩余需要印记补足
                    if (remainingNeed > 0) {
                        needSeals = Math.ceil(remainingNeed / materialsPerRun);
                    }
                    // 但要注意印记消耗 = 需要的周本次数 * sealsPerRun
                    needSeals = needSeals * sealsPerRun;
                    totalSeals += needSeals;
                }

                const progress = Math.min(100, (currentStar / MAX_STAR) * 100);
                // 显示升星明细
                let detailStr = "";
                for (let i = currentStar; i < MAX_STAR; i++) {
                    detailStr += `${i+1}星:${STAR_MATERIALS[i+1]} `;
                }
                // 判断是否可以升星（有足够材料）
                const canUpgrade = !isMaxStar && growthData.currentMaterials >= nextStarCost;

                html += `<div class="growth-spirit-item" data-id="${gs.id}">
                    <div class="flex-between">
                        <strong>⭐ ${escapeHtml(gs.name)}</strong>
                        <div>
                            <button class="small primary growth-upgrade" data-id="${gs.id}" ${isMaxStar ? 'disabled style="opacity:0.5;"' : ''}>
                                ${canUpgrade ? '⭐ 升星' : (isMaxStar ? '已满星' : '材料不足')}
                            </button>
                            <button class="small danger delete-growth" data-id="${gs.id}">🗑️</button>
                        </div>
                    </div>
                    <div class="row">
                        <label>当前星级</label>
                        <span class="value">${currentStar} / ${MAX_STAR}</span>
                        <span class="badge">进度 ${progress.toFixed(0)}%</span>
                        ${isMaxStar ? '<span class="badge" style="background:#ffd966;">已满星</span>' : `<span class="badge" style="background:#e8f0e6;">升星需 ${nextStarCost} 材料</span>`}
                    </div>
                    <div style="display:flex; flex-direction:column; gap:2px; margin-top:4px;">
                        <div><label style="font-size:0.75rem; font-weight:500; color:#3d5a3d; min-width:60px;">剩余材料</label> <span class="value">${neededMaterials}</span></div>
                        <div><label style="font-size:0.75rem; font-weight:500; color:#3d5a3d; min-width:60px;">周可获</label> <span class="value">${weekGain}</span></div>
                        <div><label style="font-size:0.75rem; font-weight:500; color:#3d5a3d; min-width:60px;">需印记</label> <span class="value" style="color:${needSeals>0?'#c25d2e':'#4c9e2c'}">${needSeals}</span></div>
                        <div><label style="font-size:0.75rem; font-weight:500; color:#3d5a3d; min-width:60px;">每次</label> <span class="value">${materialsPerRun}材料</span></div>
                    </div>
                    ${!isMaxStar ? `<div style="font-size:0.65rem; color:#5a7a4a; margin-top:4px;">升星需求: ${detailStr}</div>` : ''}
                </div>`;
            });
            summary.innerHTML = `<span>📌 合计需要 <strong>${totalSeals}</strong> 个印记（每次周本消耗 ${sealsPerRun} 印记）</span>`;
        }
        container.innerHTML = html;

        // 绑定事件 - 删除
        container.querySelectorAll('.delete-growth').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                let id = parseInt(btn.dataset.id);
                if (confirm("确定从成长计划中移除该精灵吗？")) {
                    growthData.spirits = growthData.spirits.filter(g => g.id !== id);
                    saveGrowthData();
                    renderGrowthPlan();
                }
            });
        });
        // 绑定事件 - 升星（检查材料是否足够）
        container.querySelectorAll('.growth-upgrade').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                let id = parseInt(btn.dataset.id);
                let gs = growthData.spirits.find(g => g.id === id);
                if (gs && gs.currentStar < MAX_STAR) {
                    const cost = getNextStarMaterials(gs.currentStar);
                    if (growthData.currentMaterials < cost) {
                        alert(`材料不足！升到 ${gs.currentStar+1} 星需要 ${cost} 个升星材料，当前只有 ${growthData.currentMaterials} 个。`);
                        return;
                    }
                    // 扣除材料
                    growthData.currentMaterials -= cost;
                    gs.currentStar = (gs.currentStar || 0) + 1;
                    saveGrowthData();
                    renderGrowthPlan();
                    alert(`成功升星！当前剩余材料：${growthData.currentMaterials}`);
                }
            });
        });
    }

    // ---------- 添加成长精灵（手动输入名称） ----------
    function showAddGrowthSpiritDialog() {
        const modal = document.createElement('div'); modal.className = 'modal';
        let starOptions = [0,1,2,3,4,5].map(s => `<option value="${s}">${s}星</option>`).join('');
        modal.innerHTML = `<div class="modal-content">
            <h3>添加成长精灵</h3>
            <p>输入精灵名称并设置当前星级：</p>
            <div style="margin-bottom:12px;">
                <label>精灵名称</label>
                <input type="text" id="growthNameInput" placeholder="请输入精灵名称" style="width:100%;">
            </div>
            <div style="margin-bottom:12px;">
                <label>当前星级</label>
                <select id="growthStarSelect">
                    ${starOptions}
                </select>
            </div>
            <div style="display:flex; gap:8px; margin-top:16px;">
                <button id="growthAddConfirm" class="primary">添加</button>
                <button id="growthAddCancel">取消</button>
            </div>
        </div>`;
        document.body.appendChild(modal);
        modal.querySelector('#growthAddConfirm').onclick = function() {
            try {
                let name = modal.querySelector('#growthNameInput').value.trim();
                if (!name) { alert("请输入精灵名称"); return; }
                let star = parseInt(modal.querySelector('#growthStarSelect').value);
                if (isNaN(star) || star < 0) star = 0;
                if (star > MAX_STAR) star = MAX_STAR;
                growthData.spirits.push({
                    id: nextGrowthId++,
                    name: name,
                    currentStar: star
                });
                saveGrowthData();
                renderGrowthPlan();
                modal.remove();
            } catch(e) { alert('添加失败：' + e.message); } finally { modal.remove(); }
        };
        modal.querySelector('#growthAddCancel').onclick = function() { modal.remove(); };
    }

    // ---------- 成长计划设置保存 ----------
    function saveGrowthSettings() {
        let materialsPerRun = parseInt(document.getElementById("growthMaterialsPerRun").value);
        let runsPerWeek = parseInt(document.getElementById("growthRunsPerWeek").value);
        let sealsPerRun = parseInt(document.getElementById("growthSealsPerRun").value);
        if (isNaN(materialsPerRun) || materialsPerRun < 1) materialsPerRun = 3;
        if (isNaN(runsPerWeek) || runsPerWeek < 1) runsPerWeek = 3;
        if (isNaN(sealsPerRun) || sealsPerRun < 1) sealsPerRun = 1;

        growthData.materialsPerRun = materialsPerRun;
        growthData.runsPerWeek = runsPerWeek;
        growthData.sealsPerRun = sealsPerRun;
        saveGrowthData();
        renderGrowthPlan();
        alert("成长计划设置已保存");
    }

    // ---------- 保存当前材料数量 ----------
    function saveCurrentMaterials() {
        let val = parseInt(document.getElementById("growthCurrentMaterials").value);
        if (isNaN(val) || val < 0) val = 0;
        growthData.currentMaterials = val;
        saveGrowthData();
        renderGrowthPlan();
        alert("材料数量已更新");
    }

    // ---------- 同步结构（原函数） ----------
    function syncWithPreset() {
        for(let sp of spirits) {
            let preset = presetSpirits.find(p => p.name === sp.name);
            if(preset) sp.type = preset.type;
            else if(!sp.type) sp.type = "normal";
        }
        for(let cap of capturedSpirits) {
            let preset = presetSpirits.find(p => p.name === cap.name);
            if(preset && preset.defaultSeasonId !== null && (cap.seasonId === null || cap.seasonId === undefined)) {
                cap.seasonId = preset.defaultSeasonId;
            }
        }
        updateSpiritStats();
    }

    function updateSpiritStats() {
        let wonderCount = spirits.filter(s => s.type === "wonder").length;
        let normalCount = spirits.filter(s => s.type === "normal").length;
        let statSpan = document.getElementById("spiritStats");
        if(statSpan) statSpan.innerText = `✨奇遇:${wonderCount}  🍃非奇遇:${normalCount}`;
    }

    function getCurrentSeasonId() {
        const now = new Date();
        const today = now.toISOString().slice(0,10);
        for (let s of seasons) {
            if (s.startDate && s.endDate) {
                if (today >= s.startDate && today <= s.endDate) return s.id;
            }
        }
        return null;
    }

    function loadData() {
        window.scrollPositions = {};

        let sb = localStorage.getItem(STORAGE.BALLS); if(sb) { ballTypes = JSON.parse(sb); } else ballTypes = getDefaultBalls();
        let si = localStorage.getItem(STORAGE.INVENTORY); if(si) inventory = JSON.parse(si); else inventory = {};
        let sp = localStorage.getItem(STORAGE.PRESET); if(sp) { presetSpirits = JSON.parse(sp); } else presetSpirits = getDefaultPreset();
        let st = localStorage.getItem(STORAGE.SPIRITS); if(st) spirits = JSON.parse(st); else spirits = [];
        let sc = localStorage.getItem(STORAGE.CAPTURED); if(sc) capturedSpirits = JSON.parse(sc); else capturedSpirits = [];
        let ssn = localStorage.getItem(STORAGE.SEASONS); if(ssn) seasons = JSON.parse(ssn); else seasons = getDefaultSeasons();
        let uk = localStorage.getItem(STORAGE.UNKNOWN); if(uk) unknownRecords = JSON.parse(uk); else unknownRecords = [];
        let snap = localStorage.getItem(STORAGE.SNAPSHOT); if(snap) captureSnapshot = JSON.parse(snap); else captureSnapshot = null;
        let last = localStorage.getItem(STORAGE.LASTSTOCK); if(last) lastCaptureStock = JSON.parse(last); else lastCaptureStock = null;
        let brec = localStorage.getItem(STORAGE.BATTLEREC); if(brec) battleRecords = JSON.parse(brec); else battleRecords = [];
        let startDateStr = localStorage.getItem(STORAGE.STARTDATE); if(startDateStr) captureStartDate = startDateStr; else captureStartDate = null;
        let orderLock = localStorage.getItem(STORAGE.ORDERLOCK); if(orderLock) orderLocked = JSON.parse(orderLock); else orderLocked = false;
        let lockedOrd = localStorage.getItem(STORAGE.LOCKEDORDER); if(lockedOrd) lockedOrderIds = JSON.parse(lockedOrd); else lockedOrderIds = [];
        let custom = localStorage.getItem(STORAGE.CUSTOMSTART); if(custom) customStartId = JSON.parse(custom); else customStartId = null;
        let active = localStorage.getItem(STORAGE.ACTIVETARGET); if(active) activeTargetId = parseInt(active); else activeTargetId = null;

        let rb = localStorage.getItem('setting_round_balls'); if(rb) settingRoundBalls = parseInt(rb) || 240;
        let pp = localStorage.getItem('setting_people'); if(pp) settingPeople = parseInt(pp) || 2;
        let bps = localStorage.getItem('setting_balls_per_spirit'); if(bps) settingBallsPerSpirit = parseInt(bps) || 1200;
        let cs = localStorage.getItem('setting_current_season'); if(cs) currentSeasonId = parseInt(cs); else currentSeasonId = null;
        // 废弃 recommendOpen 读取，但保留

        seasons.forEach(s => {
            if (!s.startDate || !s.endDate) {
                const now = new Date();
                const end = new Date(now);
                end.setDate(end.getDate() + 56);
                s.startDate = now.toISOString().slice(0,10);
                s.endDate = end.toISOString().slice(0,10);
            }
            if (!s.categories) s.categories = [];  // 每个赛季的分类列表

            // ---- 新增：分类备注存储结构 ----
            if (!s.categoryNotes) s.categoryNotes = {};  // { "分类名称": "备注内容" }

            if (!s.order && s.order !== 0) s.order = 0;
        });

        ballTypes.forEach(bt => { if(inventory[bt.id]===undefined) inventory[bt.id]=0; if(bt.attr2===undefined) bt.attr2=""; });
        spirits.forEach(s=>{ if(!s.requiredCount) s.requiredCount=1500; if(!s.attrs) s.attrs=[]; if(!s.consumptionLogs) s.consumptionLogs = []; if(s.prismWarning === undefined) s.prismWarning = false; if(!s.type) s.type = "normal"; });
        capturedSpirits.forEach(cap=>{ if(cap.seasonId === undefined) cap.seasonId = null; if(cap.captureMethod === undefined) cap.captureMethod = "自己捕捉"; });
        presetSpirits.forEach(p => {
            if (!p.updatedAt) {
                p.updatedAt = new Date(0).toISOString();
            }
        });
        unknownRecords.forEach(u=>{ if(!u.consumptionLogs) u.consumptionLogs = []; if(u.status === undefined) u.status = "pending"; });
        battleRecords.forEach(rec => { if(!rec.date) { let d = rec.timestamp ? new Date(rec.timestamp) : new Date(); rec.date = d.toISOString().slice(0,10); } });
        if(lockedOrderIds.length) {
            lockedOrderIds = lockedOrderIds.filter(id => spirits.some(s=>s.id===id));
        }
        if (activeTargetId !== null && !spirits.some(s=>s.id===activeTargetId)) {
            activeTargetId = null;
        }
        syncWithPreset();
        refreshIdSequences();
        setSettingsUI();
        populateSeasonDropdown();
        if (currentSeasonId === null || !seasons.some(s => s.id === currentSeasonId)) {
            const autoId = getCurrentSeasonId();
            if (autoId !== null) currentSeasonId = autoId;
            else if (seasons.length > 0) currentSeasonId = seasons[0].id;
            localStorage.setItem('setting_current_season', String(currentSeasonId));
        }
        const sel = document.getElementById("settingCurrentSeason");
        if (sel) sel.value = currentSeasonId !== null ? String(currentSeasonId) : "";
        if (activeTargetId !== null) {
            const targetSelect = document.getElementById("selectTargetSpirit");
            if (targetSelect) targetSelect.value = String(activeTargetId);
        }
        // 初始化侧边栏
        initSidebar();
        // 修复超链接点击
        document.getElementById('externalLink')?.addEventListener('click', function(e) {
            e.stopPropagation();
        });

        // 加载成长计划数据
        loadGrowthData();
        renderGrowthPlan();
    }

    function refreshIdSequences() {
        let maxBallId = 0, maxPresetId = 0, maxSpiritId = 0, maxCapturedId = 0, maxSeasonId = 0, maxUnknownId = 0;
        ballTypes.forEach(b => { if(b.id > maxBallId) maxBallId = b.id; });
        presetSpirits.forEach(p => { if(p.id > maxPresetId) maxPresetId = p.id; });
        spirits.forEach(s => { if(s.id > maxSpiritId) maxSpiritId = s.id; });
        capturedSpirits.forEach(c => { if(c.id > maxCapturedId) maxCapturedId = c.id; });
        seasons.forEach(s => { if(s.id > maxSeasonId) maxSeasonId = s.id; });
        unknownRecords.forEach(u => { if(u.id > maxUnknownId) maxUnknownId = u.id; });
        nextBallId = maxBallId + 1;
        nextPresetId = maxPresetId + 1;
        nextSpiritId = maxSpiritId + 1;
        nextCapturedId = maxCapturedId + 1;
        nextSeasonId = maxSeasonId + 1;
        nextUnknownId = maxUnknownId + 1;
    }

    function persistAll() {
        localStorage.setItem(STORAGE.BALLS, JSON.stringify(ballTypes));
        localStorage.setItem(STORAGE.INVENTORY, JSON.stringify(inventory));
        localStorage.setItem(STORAGE.PRESET, JSON.stringify(presetSpirits));
        localStorage.setItem(STORAGE.SPIRITS, JSON.stringify(spirits));
        localStorage.setItem(STORAGE.CAPTURED, JSON.stringify(capturedSpirits));
        localStorage.setItem(STORAGE.SEASONS, JSON.stringify(seasons));
        localStorage.setItem(STORAGE.UNKNOWN, JSON.stringify(unknownRecords));
        if(captureSnapshot) localStorage.setItem(STORAGE.SNAPSHOT, JSON.stringify(captureSnapshot)); else localStorage.removeItem(STORAGE.SNAPSHOT);
        if(lastCaptureStock) localStorage.setItem(STORAGE.LASTSTOCK, JSON.stringify(lastCaptureStock)); else localStorage.removeItem(STORAGE.LASTSTOCK);
        localStorage.setItem(STORAGE.BATTLEREC, JSON.stringify(battleRecords));
        if(captureStartDate) localStorage.setItem(STORAGE.STARTDATE, captureStartDate); else localStorage.removeItem(STORAGE.STARTDATE);
        localStorage.setItem(STORAGE.ORDERLOCK, JSON.stringify(orderLocked));
        localStorage.setItem(STORAGE.LOCKEDORDER, JSON.stringify(lockedOrderIds));
        localStorage.setItem(STORAGE.CUSTOMSTART, JSON.stringify(customStartId));
        localStorage.setItem(STORAGE.ACTIVETARGET, JSON.stringify(activeTargetId));
        localStorage.setItem('setting_round_balls', String(settingRoundBalls));
        localStorage.setItem('setting_people', String(settingPeople));
        localStorage.setItem('setting_balls_per_spirit', String(settingBallsPerSpirit));
        localStorage.setItem('setting_current_season', String(currentSeasonId));
        // 成长数据单独保存
        saveGrowthData();
    }

    function setSettingsUI() {
        document.getElementById("settingRoundBalls").value = settingRoundBalls;
        document.getElementById("settingPeople").value = settingPeople;
        document.getElementById("settingBallsPerSpirit").value = settingBallsPerSpirit;
    }

    function populateSeasonDropdown() {
        const sel = document.getElementById("settingCurrentSeason");
        if (!sel) return;
        sel.innerHTML = '';
        seasons.forEach(s => {
            const opt = document.createElement('option');
            opt.value = s.id;
            opt.textContent = s.name + (s.startDate && s.endDate ? ` (${s.startDate} ~ ${s.endDate})` : '');
            sel.appendChild(opt);
        });
        if (currentSeasonId !== null && seasons.some(s => s.id === currentSeasonId)) {
            sel.value = String(currentSeasonId);
        } else {
            const autoId = getCurrentSeasonId();
            if (autoId !== null) {
                sel.value = String(autoId);
                currentSeasonId = autoId;
                localStorage.setItem('setting_current_season', String(autoId));
            } else if (seasons.length > 0) {
                sel.value = String(seasons[0].id);
                currentSeasonId = seasons[0].id;
                localStorage.setItem('setting_current_season', String(currentSeasonId));
            }
        }
    }

    function getSeasonRemainingDays(season) {
        if (!season || !season.startDate || !season.endDate) return 0;
        const now = new Date();
        const start = new Date(season.startDate + 'T00:00:00');
        const end = new Date(season.endDate + 'T00:00:00');
        const totalDays = Math.ceil((end - start) / (1000 * 60 * 60 * 24)) + 1;
        if (now < start) return totalDays;
        else if (now > end) return 0;
        else {
            const remaining = Math.ceil((end - now) / (1000 * 60 * 60 * 24));
            return Math.max(0, remaining);
        }
    }

    function renderDailyStats() {
        const total = spirits.length;
        let rounds = 0;
        let season = null;
        if (currentSeasonId !== null) season = seasons.find(s => s.id === currentSeasonId);
        let remainingDays = 0;
        if (season) remainingDays = getSeasonRemainingDays(season);
        else if (seasons.length > 0) {
            season = seasons[0];
            remainingDays = getSeasonRemainingDays(season);
        }
        if (total > 0 && remainingDays > 0 && settingRoundBalls > 0) {
            const numerator = total * settingPeople * settingBallsPerSpirit;
            const denominator = remainingDays * settingRoundBalls;
            rounds = Math.round(numerator / denominator);
            if (rounds < 0) rounds = 0;
        }
        document.getElementById("dailyRoundValue").innerText = rounds + " 轮/天";
        document.getElementById("roundBallsDisplay").innerText = settingRoundBalls;
        document.getElementById("seasonDaysDisplay").innerText = remainingDays;
        document.getElementById("peopleDisplay").innerText = settingPeople;
        document.getElementById("ballsPerSpiritDisplay").innerText = settingBallsPerSpirit;
    }

    function getConsumableBallsForSpirit(spirit) {
        const attrBalls = ballTypes.filter(b => {
            if(!isAttributeBall(b)) return false;
            let attrs = [b.attr1, b.attr2].filter(a=>a && a.trim() && a !== "无");
            return (spirit.attrs || []).some(sa=>attrs.includes(sa));
        });
        const neutralBalls = ballTypes.filter(b => !isAttributeBall(b));
        const all = [...attrBalls, ...neutralBalls];
        const map = new Map();
        all.forEach(b => map.set(b.id, b));
        return Array.from(map.values());
    }

    function getMatchedAttributeBallsForSpirit(spirit) {
        return ballTypes.filter(b => {
            if(!isAttributeBall(b)) return false;
            let attrs = [b.attr1, b.attr2].filter(a=>a && a.trim() && a !== "无");
            return (spirit.attrs || []).some(sa=>attrs.includes(sa));
        });
    }

    function computeBallGapsDetailed() {
        let remainingStock = {}; ballTypes.forEach(b=>{ remainingStock[b.id]=inventory[b.id]||0; });
        let totalNeeded = new Map(); ballTypes.forEach(b=>totalNeeded.set(b.id,0));
        const spiritUsage = [];
        for(let sp of spirits) {
            let need = sp.requiredCount;
            let remainingNeed = need;
            let matched = ballTypes.filter(b => isAttributeBall(b) && (sp.attrs || []).some(sa=> [b.attr1, b.attr2].filter(a=>a && a.trim() && a !== "无").includes(sa)));
            matched.sort((a,b) => (remainingStock[b.id]||0) - (remainingStock[a.id]||0));
            const used = [];
            for(let ball of matched) {
                if(remainingNeed<=0) break;
                let avail = remainingStock[ball.id]||0;
                let take = Math.min(avail, remainingNeed);
                if(take>0) {
                    remainingStock[ball.id]-=take;
                    remainingNeed-=take;
                    totalNeeded.set(ball.id, totalNeeded.get(ball.id)+take);
                    used.push({ballName:ball.name, amount:take});
                }
            }
            if(remainingNeed>0 && matched.length) {
                let first = matched[0];
                totalNeeded.set(first.id, totalNeeded.get(first.id)+remainingNeed);
                used.push({ballName:first.name, amount:remainingNeed, isGap:true});
            }
            spiritUsage.push({name:sp.name, need, used, deficit:remainingNeed});
        }
        let ballGaps = new Map();
        ballTypes.forEach(b=>{
            if(!isAttributeBall(b)) return;
            let total = totalNeeded.get(b.id)||0;
            let stock = inventory[b.id]||0;
            ballGaps.set(b.id, Math.max(0, total-stock));
        });
        return {ballGaps, totalNeeded, spiritUsage};
    }

    function getSharedFirstAttr(a,b) {
        let firstA = getFirstAttr(a);
        let firstB = getFirstAttr(b);
        if(firstA && firstB && firstA === firstB) return [firstA];
        return [];
    }

    function getFilteredSpiritsForTransfer() {
        if(currentTransferMode === "all") return spirits.slice();
        if(currentTransferMode === "wonder") return spirits.filter(s => s.type === "wonder");
        return spirits.filter(s => s.type === "normal");
    }

    function getFilteredSpiritsForDisplay() {
        if(currentDisplayGroup === "all") return spirits.slice();
        if(currentDisplayGroup === "wonder") return spirits.filter(s => s.type === "wonder");
        return spirits.filter(s => s.type === "normal");
    }

    // 以下函数原本用于最优顺序，现已不使用，但保留以防其他调用
    function computeOptimalOrderWithStart(startId) {
        return { ordered: [], details: [], score: 0, length: 0 };
    }
    function getDisplayOrder() {
        return spirits.slice();
    }
    function renderRecommendation() { /* 不再使用 */ }
    function updateRecommendToggle() { /* 不再使用 */ }
    function toggleRecommend() { /* 不再使用 */ }

    function lockCurrentOrder() { alert("此功能已移除"); }
    function refreshOrder() { alert("此功能已移除"); }
    function setCustomStart() { alert("此功能已移除"); }

    function renderTotalGap() {
        const container = document.getElementById("totalGapContent");
        if(!container) return;
        if(spirits.length===0) { container.innerHTML="<div>✨ 暂无待捕捉精灵</div>"; return; }
        const {ballGaps, totalNeeded, spiritUsage} = computeBallGapsDetailed();
        let targetBallIds = new Set();
        if(activeTargetId) {
            let ts=spirits.find(s=>s.id===activeTargetId);
            if(ts) {
                targetBallIds = new Set(ballTypes.filter(b => isAttributeBall(b) && (ts.attrs || []).some(sa=> [b.attr1, b.attr2].filter(a=>a && a.trim() && a !== "无").includes(sa))).map(b=>b.id));
            }
        }
        let hasGap=false;
        let gapsHtml = `<div style="display:flex; flex-direction:column; gap:8px;">`;
        for(let b of ballTypes) {
            if(!isAttributeBall(b)) continue;
            let deficit=ballGaps.get(b.id)||0; if(deficit>0) hasGap=true;
            if(deficit===0 && (totalNeeded.get(b.id)||0)===0) continue;
            let highlight = targetBallIds.has(b.id) ? 'background:#fff0cc; padding:4px 8px; border-radius:20px;' : '';
            gapsHtml += `<div class="flex-between" style="${highlight}"><span><strong>${b.name}</strong> (${getBallAttrDisplay(b)})</span>
                         <span>需 ${totalNeeded.get(b.id)||0} | 库存 ${inventory[b.id]||0} | <span class="gap-number">缺口 ${deficit}</span></span></div>`;
        }
        gapsHtml += `</div>`;
        let detailHtml = `<div style="margin-top:12px; font-size:0.75rem; background:#fff5e6; border-radius:20px; padding:10px;"><strong>🔍 各精灵消耗预测</strong>`;
        for(let u of spiritUsage) {
            detailHtml += `<div>✨ ${u.name} 需 ${u.need} → `;
            if(u.used.length) detailHtml += u.used.map(v=>`${v.ballName} ${v.amount}${v.isGap?'(缺)':''}`).join(' + ');
            else detailHtml += `无匹配属性球`;
            if(u.deficit>0) detailHtml += ` <span class="badge">缺口${u.deficit}</span>`;
            detailHtml += `</div>`;
        }
        detailHtml += `</div>`;
        container.innerHTML = (hasGap ? gapsHtml : `<div style="text-align:center;">🎉 库存充足，无需补充！</div>`) + detailHtml;
    }

    // ---------- 未知捕捉相关 ----------
    function hasUnconfirmedFinalRecord() {
        for (let rec of unknownRecords) {
            if (rec.status === 'pending' && rec.consumptionLogs.some(log => log.type === 'final')) {
                return true;
            }
        }
        return false;
    }

    function showRemainingStockForAllBalls(title, callback) {
        if(!lastCaptureStock) {
            alert("请先点击「开始捕捉」初始化库存快照");
            return;
        }
        const modal = document.createElement('div'); modal.className = 'modal';
        let html = `<div class="modal-content"><h3>${title}</h3>`;
        html += `<div style="font-size:0.7rem; margin-bottom:8px;">请填写当前背包中<b>剩余</b>的咕噜球数量：</div>`;
        for(let ball of ballTypes) {
            let currentStock = inventory[ball.id] || 0;
            html += `<div style="margin-bottom:8px;">
                        <label>${ball.name} (当前库存 ${currentStock}): </label>
                        <input type="number" id="remain_${ball.id}" min="0" max="${currentStock}" value="${currentStock}" style="width:90px;">
                     </div>`;
        }
        html += `<div style="display:flex; gap:8px; margin-top:16px;"><button id="confirmRemain">确认</button><button id="cancelRemain">取消</button></div></div>`;
        modal.innerHTML = html;
        document.body.appendChild(modal);
        modal.querySelector('#confirmRemain').onclick = () => {
            const remaining = {};
            let valid = true;
            for(let ball of ballTypes) {
                let val = parseInt(modal.querySelector(`#remain_${ball.id}`).value);
                if(isNaN(val)) val = inventory[ball.id] || 0;
                if(val < 0) val = 0;
                if(val > (inventory[ball.id] || 0)) val = inventory[ball.id] || 0;
                remaining[ball.id] = val;
            }
            const consumption = {};
            for(let ball of ballTypes) {
                let prev = lastCaptureStock[ball.id] || 0;
                let remain = remaining[ball.id];
                let used = prev - remain;
                if(used < 0) {
                    if(confirm(`检测到 ${ball.name} 库存增加了 ${-used} 个（可能通过战斗/购买获得）。是否将当前库存同步为新快照，并忽略本次消耗记录？`)) {
                        lastCaptureStock = { ...inventory };
                        persistAll();
                        used = 0;
                    } else {
                        valid = false;
                        break;
                    }
                }
                if(used > 0) consumption[ball.id] = used;
            }
            if(!valid) {
                modal.remove();
                return;
            }
            for(let ball of ballTypes) {
                inventory[ball.id] = remaining[ball.id];
            }
            lastCaptureStock = { ...inventory };
            persistAll();
            modal.remove();
            callback(consumption, remaining);
        };
        modal.querySelector('#cancelRemain').onclick = () => modal.remove();
    }

    function confirmUnknownRecord(unknownId, onSuccess) {
        const record = unknownRecords.find(u => u.id === unknownId);
        if(!record) {
            if (onSuccess) onSuccess(false);
            return;
        }
        if(presetSpirits.length === 0) {
            alert("请先添加预设精灵");
            if (onSuccess) onSuccess(false);
            return;
        }
        const modal = document.createElement('div'); modal.className = 'modal';
        let seasonOptions = `<option value="__ALL__">🏆 全部赛季</option>`;
        seasons.slice().sort((a,b)=>b.order - a.order).forEach(s => {
            seasonOptions += `<option value="${s.id}">${escapeHtml(s.name)}</option>`;
        });
        let defaultSeasonId = getCurrentSeasonId();
        if (defaultSeasonId === null) defaultSeasonId = '__ALL__';

        modal.innerHTML = `<div class="modal-content">
            <h3>确认未知精灵</h3>
            <p>选择赛季和具体精灵：</p>
            <div style="margin-bottom:12px;">
                <label>赛季</label>
                <select id="confirmSeasonSelect" style="width:100%;">${seasonOptions}</select>
            </div>
            <div style="margin-bottom:12px;">
                <label>精灵</label>
                <select id="confirmSpiritSelect" style="width:100%;"></select>
            </div>
            <div style="margin-top:12px;">
                <label>捕捉起始日期（可选）：</label>
                <input type="datetime-local" id="confirmStartDate" value="">
            </div>
            <div style="display:flex; gap:8px; margin-top:16px;">
                <button id="confirmUnknownOk" class="primary">确认</button>
                <button id="confirmUnknownCancel">取消</button>
            </div>
        </div>`;
        document.body.appendChild(modal);

        function populateSpiritSelect(seasonId) {
            const sel = document.getElementById('confirmSpiritSelect');
            sel.innerHTML = '';
            let filtered = presetSpirits;
            if (seasonId !== '__ALL__') {
                filtered = presetSpirits.filter(p => p.defaultSeasonId === parseInt(seasonId) || p.defaultSeasonId === null);
            }
            filtered.forEach(p => {
                const opt = document.createElement('option');
                opt.value = p.id;
                opt.textContent = p.name + ' (' + p.attrs.join('·') + ')';
                sel.appendChild(opt);
            });
            if (filtered.length === 0) {
                const opt = document.createElement('option');
                opt.value = '';
                opt.textContent = '无匹配精灵';
                sel.appendChild(opt);
            }
            sel.selectedIndex = 0;
        }

        const seasonSel = modal.querySelector('#confirmSeasonSelect');
        if (defaultSeasonId !== null) {
            seasonSel.value = String(defaultSeasonId);
        } else {
            seasonSel.value = '__ALL__';
        }
        populateSpiritSelect(seasonSel.value);
        seasonSel.addEventListener('change', function() {
            populateSpiritSelect(this.value);
        });

        modal.querySelector('#confirmUnknownOk').onclick = () => {
            const spiritSelect = modal.querySelector('#confirmSpiritSelect');
            const selectedOption = spiritSelect.options[spiritSelect.selectedIndex];
            const presetId = parseInt(spiritSelect.value);
            if (!presetId) { alert("请选择有效的精灵"); return; }
            const preset = presetSpirits.find(p => p.id === presetId);
            if(!preset) { alert("精灵不存在"); return; }
            const startDate = modal.querySelector('#confirmStartDate').value;
            const totalConsumption = {};
            for(let log of record.consumptionLogs) {
                for(let [bid, amt] of Object.entries(log.consumedBalls)) {
                    totalConsumption[bid] = (totalConsumption[bid] || 0) + amt;
                }
            }
            // 未知记录确认时默认获取方式为“自己捕捉”
            const newCaptured = {
                id: nextCapturedId++,
                name: preset.name,
                attrs: [...preset.attrs],
                requiredCount: 0,
                consumedBalls: totalConsumption,
                consumptionLogs: record.consumptionLogs,
                capturedAt: new Date().toISOString(),
                startDate: startDate || captureStartDate || "未知",
                seasonId: preset.defaultSeasonId || null,
                captureMethod: "自己捕捉"  // 未知捕捉默认为自己捕捉
            };
            capturedSpirits.push(newCaptured);
            unknownRecords = unknownRecords.filter(u => u.id !== unknownId);
            spirits = spirits.filter(s => s.name !== preset.name);
            if (activeTargetId && !spirits.some(s => s.id === activeTargetId)) {
                activeTargetId = null;
            }
            refreshIdSequences();
            persistAll();
            modal.remove();
            fullRender();
            alert(`未知记录已转为 ${preset.name} 的捕捉记录，并已从待捕捉列表中移除同名精灵。`);
            if (onSuccess) onSuccess(true);
        };
        modal.querySelector('#confirmUnknownCancel').onclick = () => {
            modal.remove();
            if (onSuccess) onSuccess(false);
        };
    }

    function showUnknownCaptureDialog() {
        if (hasUnconfirmedFinalRecord()) {
            alert("存在未确认的最终捕捉记录，请先确认或删除该记录，才能继续记录新的未知捕捉。");
            return;
        }
        if(!lastCaptureStock) {
            alert("请先点击「开始捕捉」初始化库存快照");
            return;
        }
        let pendingRecord = null;
        for (let rec of unknownRecords) {
            if (rec.status === 'pending' && !rec.consumptionLogs.some(log => log.type === 'final')) {
                pendingRecord = rec;
                break;
            }
        }

        function startCaptureFlow(appendToId) {
            const typeModal = document.createElement('div'); typeModal.className = 'modal';
            typeModal.innerHTML = `<div class="modal-content">
                <h3>🎲 未知捕捉 - 记录消耗</h3>
                <p>选择记录类型：</p>
                <select id="unknownRecordType" style="width:100%; margin-bottom:12px;">
                    <option value="pause">⏸️ 暂停/中间记录</option>
                    <option value="final">🎯 最终捕捉（将生成一条未知记录）</option>
                </select>
                <div style="display:flex; gap:8px;"><button id="confirmType" class="primary">下一步</button><button id="cancelType">取消</button></div>
            </div>`;
            document.body.appendChild(typeModal);
            typeModal.querySelector('#confirmType').onclick = () => {
                const recordType = typeModal.querySelector('#unknownRecordType').value;
                typeModal.remove();
                showRemainingStockForAllBalls("记录未知捕捉消耗", function(consumption, remaining) {
                    if(Object.keys(consumption).length === 0) {
                        alert("没有消耗任何咕噜球，无需记录");
                        return;
                    }
                    const now = new Date();
                    const logEntry = {
                        timestamp: now.toISOString(),
                        consumedBalls: consumption,
                        type: recordType,
                        remainingAfter: remaining
                    };
                    let targetId = null;
                    if (appendToId !== null) {
                        const target = unknownRecords.find(r => r.id === appendToId);
                        if (target) {
                            target.consumptionLogs.push(logEntry);
                            targetId = target.id;
                            persistAll();
                            fullRender();
                            alert(`已追加消耗记录，总消耗已更新。`);
                        } else {
                            const newRecord = {
                                id: nextUnknownId++,
                                consumptionLogs: [logEntry],
                                capturedAt: now.toISOString(),
                                status: 'pending'
                            };
                            unknownRecords.push(newRecord);
                            targetId = newRecord.id;
                            persistAll();
                            fullRender();
                            alert(`未知记录已保存，消耗 ${Object.values(consumption).reduce((a,b)=>a+b,0)} 个咕噜球。`);
                        }
                    } else {
                        const newRecord = {
                            id: nextUnknownId++,
                            consumptionLogs: [logEntry],
                            capturedAt: now.toISOString(),
                            status: 'pending'
                        };
                        unknownRecords.push(newRecord);
                        targetId = newRecord.id;
                        persistAll();
                        fullRender();
                        alert(`未知记录已保存，消耗 ${Object.values(consumption).reduce((a,b)=>a+b,0)} 个咕噜球。`);
                    }
                    if (recordType === 'final' && targetId !== null) {
                        const finalRecord = unknownRecords.find(r => r.id === targetId);
                        if (finalRecord) {
                            confirmUnknownRecord(targetId, function(success) {
                                if (!success) {
                                    alert("最终记录已保存，请尽快确认精灵，否则无法继续记录未知捕捉。");
                                }
                            });
                        }
                    }
                });
            };
            typeModal.querySelector('#cancelType').onclick = () => typeModal.remove();
        }

        if (pendingRecord) {
            const confirmModal = document.createElement('div'); confirmModal.className = 'modal';
            confirmModal.innerHTML = `<div class="modal-content">
                <h3>继续未知捕捉</h3>
                <p>检测到未完成的未知记录（ID: ${pendingRecord.id}），是否追加消耗到该记录？</p>
                <div style="display:flex; gap:8px; margin-top:16px;">
                    <button id="appendYes" class="primary">追加到当前记录</button>
                    <button id="appendNo">新建记录</button>
                    <button id="appendCancel">取消</button>
                </div>
            </div>`;
            document.body.appendChild(confirmModal);
            confirmModal.querySelector('#appendYes').onclick = () => {
                confirmModal.remove();
                startCaptureFlow(pendingRecord.id);
            };
            confirmModal.querySelector('#appendNo').onclick = () => {
                confirmModal.remove();
                startCaptureFlow(null);
            };
            confirmModal.querySelector('#appendCancel').onclick = () => confirmModal.remove();
        } else {
            startCaptureFlow(null);
        }
    }

    function deleteUnknownRecord(unknownId) {
        if(confirm("确定删除该未知记录吗？（消耗不会恢复）")) {
            unknownRecords = unknownRecords.filter(u => u.id !== unknownId);
            persistAll();
            fullRender();
        }
    }

    function renderUnknownList() {
        const container = document.getElementById("unknownListContainer");
        if(!container) return;
        if(unknownRecords.length === 0) {
            container.innerHTML = "<div>暂无未知记录</div>";
            document.getElementById("unknownCount").innerText = "0";
            return;
        }
        document.getElementById("unknownCount").innerText = unknownRecords.length;
        let html = "";
        unknownRecords.forEach(u => {
            let totalConsumption = {};
            for(let log of u.consumptionLogs) {
                for(let [bid, amt] of Object.entries(log.consumedBalls)) {
                    totalConsumption[bid] = (totalConsumption[bid] || 0) + amt;
                }
            }
            let parts = Object.entries(totalConsumption).map(([bid, amt]) => {
                let ball = ballTypes.find(b => b.id == bid);
                return ball ? `${ball.name}:${amt}` : '';
            }).filter(t=>t).join(', ');
            let logCount = u.consumptionLogs.length;
            let hasFinal = u.consumptionLogs.some(log => log.type === 'final');
            html += `<div class="unknown-card">
                        <div><strong>❓ 未知记录 #${u.id}</strong>
                            <span class="badge">${logCount} 次消耗</span>
                            ${hasFinal ? '<span class="badge" style="background:#ffd966;">最终</span>' : ''}
                            <span class="badge">${new Date(u.capturedAt).toLocaleString()}</span>
                        </div>
                        <div style="font-size:0.75rem; margin-top:4px;">总消耗：${parts || "无"}</div>
                        <div class="unknown-actions" style="margin-top:8px;">
                            <button class="small primary" data-id="${u.id}">✅ 确认精灵</button>
                            <button class="small danger" data-id="${u.id}">🗑️ 删除</button>
                        </div>
                    </div>`;
        });
        container.innerHTML = html;
        container.querySelectorAll('.unknown-actions .primary').forEach(btn => {
            btn.addEventListener('click', (e) => {
                let id = parseInt(btn.dataset.id);
                confirmUnknownRecord(id, function(success) {});
            });
        });
        container.querySelectorAll('.unknown-actions .danger').forEach(btn => {
            btn.addEventListener('click', (e) => {
                let id = parseInt(btn.dataset.id);
                deleteUnknownRecord(id);
            });
        });
    }

    // ---------- 其他功能 ----------
    function showHistoryConsumptionDialog() {
        if(spirits.length === 0) {
            alert("没有待捕捉精灵，请先添加目标");
            return;
        }
        return new Promise((resolve) => {
            let spiritOptions = `<select id="historySpiritSelect" style="width:100%; margin-bottom:12px;">`;
            spirits.forEach(sp => {
                spiritOptions += `<option value="${sp.id}">${sp.name} (${sp.attrs.join("·")})</option>`;
            });
            spiritOptions += `</select>`;
            let html = `<div class="modal-content">
                <h3>📜 补录历史消耗</h3>
                <p>选择精灵并填写之前已经消耗的咕噜球数量（不会影响当前库存）</p>
                <div class="input-group"><label>选择精灵</label>${spiritOptions}</div>
                <div style="margin-top:12px;"><strong>历史消耗的咕噜球数量：</strong></div>`;
            for(let ball of ballTypes) {
                html += `<div style="margin-bottom:6px;"><label>${ball.name}: </label><input type="number" id="hist_consume_${ball.id}" min="0" value="0" style="width:80px;"></div>`;
            }
            html += `<div style="display:flex; gap:8px; margin-top:16px;"><button id="confirmHistory">确认补录</button><button id="cancelHistory">取消</button></div></div>`;
            const modal = document.createElement('div'); modal.className = 'modal';
            modal.innerHTML = html;
            document.body.appendChild(modal);
            modal.querySelector('#confirmHistory').onclick = () => {
                const spiritId = parseInt(modal.querySelector('#historySpiritSelect').value);
                const spirit = spirits.find(s => s.id === spiritId);
                if(!spirit) { alert("精灵不存在"); modal.remove(); resolve(false); return; }
                const consumption = {};
                for(let ball of ballTypes) {
                    let val = parseInt(modal.querySelector(`#hist_consume_${ball.id}`).value);
                    if(isNaN(val)) val = 0;
                    if(val > 0) consumption[ball.id] = val;
                }
                if(Object.keys(consumption).length === 0) {
                    alert("至少填写一种咕噜球的消耗数量");
                    return;
                }
                if(!spirit.consumptionLogs) spirit.consumptionLogs = [];
                spirit.consumptionLogs.push({
                    timestamp: new Date().toISOString(),
                    consumedBalls: consumption,
                    type: "history",
                    note: "历史补录"
                });
                persistAll();
                modal.remove();
                resolve(true);
                fullRender();
                alert(`已为 ${spirit.name} 补录历史消耗，累计消耗已更新。`);
            };
            modal.querySelector('#cancelHistory').onclick = () => { modal.remove(); resolve(false); };
        });
    }

    function editCapturedRecord(capturedId) {
        const record = capturedSpirits.find(c => c.id === capturedId);
        if (!record) return;
        const modal = document.createElement('div'); modal.className = 'modal';
        let seasonOpts = `<option value="">-- 无 --</option>`;
        seasons.sort((a,b)=>b.order - a.order).forEach(s => {
            seasonOpts += `<option value="${s.id}" ${record.seasonId === s.id ? 'selected' : ''}>${escapeHtml(s.name)}</option>`;
        });
        let consumeInputs = '';
        for (let ball of ballTypes) {
            let val = record.consumedBalls[ball.id] || 0;
            consumeInputs += `<div style="margin-bottom:4px;"><label>${ball.name}:</label><input type="number" class="editConsume" data-ballid="${ball.id}" value="${val}" min="0" style="width:80px;"></div>`;
        }
        modal.innerHTML = `<div class="modal-content">
            <h3>编辑捕捉记录 - ${escapeHtml(record.name)}</h3>
            <div><label>精灵名称</label><input id="editCapturedName" value="${escapeHtml(record.name)}"></div>
            <div><label>捕捉日期</label><input type="datetime-local" id="editCapturedDate" value="${record.capturedAt.slice(0,16)}"></div>
            <div><label>开始日期</label><input type="datetime-local" id="editCapturedStart" value="${record.startDate && record.startDate !== '未知' && record.startDate !== '历史补录' ? record.startDate.slice(0,16) : ''}"></div>
            <div><label>赛季</label><select id="editCapturedSeason">${seasonOpts}</select></div>
            <div><label>获取方式</label>
                <select id="editCapturedMethod">
                    <option value="自己捕捉" ${record.captureMethod === '自己捕捉' ? 'selected' : ''}>自己捕捉</option>
                    <option value="朋友赠送" ${record.captureMethod === '朋友赠送' ? 'selected' : ''}>朋友赠送</option>
                    <option value="赛季特色" ${record.captureMethod === '赛季特色' ? 'selected' : ''}>赛季特色</option>  <!-- 从"赛季特色"改为"赛季特色" -->
                </select>
            </div>
            <div style="margin-top:12px;"><strong>消耗数量</strong></div>
            ${consumeInputs}
            <div style="display:flex; gap:8px; margin-top:16px;">
                <button id="saveCapturedEdit" class="primary">保存</button>
                <button id="cancelCapturedEdit">取消</button>
            </div>
        </div>`;
        document.body.appendChild(modal);
        modal.querySelector('#saveCapturedEdit').onclick = () => {
            const newName = modal.querySelector('#editCapturedName').value.trim();
            if (!newName) { alert("名称不能为空"); return; }
            const newDate = modal.querySelector('#editCapturedDate').value;
            const newStart = modal.querySelector('#editCapturedStart').value;
            const newSeason = parseInt(modal.querySelector('#editCapturedSeason').value) || null;
            const newMethod = modal.querySelector('#editCapturedMethod').value;
            const newConsumption = {};
            document.querySelectorAll('.editConsume').forEach(inp => {
                let bid = parseInt(inp.dataset.ballid);
                let val = parseInt(inp.value);
                if (!isNaN(val) && val > 0) newConsumption[bid] = val;
            });
            record.name = newName;
            if (newDate) record.capturedAt = new Date(newDate).toISOString();
            if (newStart) record.startDate = new Date(newStart).toISOString();
            else if (newStart === '') record.startDate = '未知';
            record.seasonId = newSeason;
            record.captureMethod = newMethod;
            record.consumedBalls = newConsumption;
            persistAll();
            modal.remove();
            fullRender();
            alert("已更新记录");
        };
        modal.querySelector('#cancelCapturedEdit').onclick = () => modal.remove();
    }

    function deleteCapturedRecord(capturedId) {
        if (confirm("确定要删除这条捕捉记录吗？此操作不可撤销。")) {
            capturedSpirits = capturedSpirits.filter(c => c.id !== capturedId);
            persistAll();
            fullRender();
        }
    }

    function showAddCapturedRecordDialog() {
        let spiritSelectHtml = `<select id="newRecordSpiritSelect" style="width:100%; margin-bottom:12px;"><option value="">-- 选择精灵 --</option>`;
        presetSpirits.forEach(p => {
            spiritSelectHtml += `<option value="${p.id}" data-name="${escapeHtml(p.name)}" data-attrs='${JSON.stringify(p.attrs)}' data-defaultSeason="${p.defaultSeasonId !== null ? p.defaultSeasonId : ''}">${p.name} (${p.attrs.join("·")})</option>`;
        });
        spiritSelectHtml += `</select>`;
        let recordsHtml = `<div id="recordsContainer"></div><button id="addRecordBtn" type="button" class="small" style="margin-top:8px;">+ 添加记录</button>`;
        const modal = document.createElement('div'); modal.className = 'modal';
        modal.innerHTML = `<div class="modal-content">
            <h3>➕ 新增已捕捉记录</h3>
            <div class="input-group"><label>选择精灵</label>${spiritSelectHtml}</div>
            <div class="input-group"><label>捕捉起始日期（可选）</label><input type="datetime-local" id="captureStartDateInput" value=""></div>
            <div class="input-group"><label>获取方式</label>
                <select id="newRecordMethod">
                    <option value="自己捕捉">自己捕捉</option>
                    <option value="朋友赠送">朋友赠送</option>
                    <option value="赛季特色">赛季特色</option>
                </select>
            </div>
            ${recordsHtml}
            <div style="display:flex; gap:8px; margin-top:16px;"><button id="confirmAddRecords" class="primary">确认添加</button><button id="cancelAddRecords">取消</button></div>
        </div>`;
        document.body.appendChild(modal);
        let recordIndex = 0;
        function addRecordEntry() {
            const container = document.getElementById('recordsContainer');
            const recordDiv = document.createElement('div');
            recordDiv.className = 'record-entry';
            recordDiv.dataset.index = recordIndex;
            recordDiv.innerHTML = `
                <div class="flex-between"><strong>记录 ${recordIndex+1}</strong><button class="remove-record small" data-index="${recordIndex}">✖️ 删除</button></div>
                <div class="input-group"><label>记录类型</label><select class="recordType" data-index="${recordIndex}"><option value="pause">⏸️ 暂停</option><option value="final">🎯 最终</option><option value="history">📜 历史补录</option></select></div>
                <div class="input-group"><label>时间</label><input type="datetime-local" class="recordTime" data-index="${recordIndex}"></div>
                <div><strong>消耗数量：</strong></div>
                <div class="recordBalls" data-index="${recordIndex}">
                    ${ballTypes.map(ball => `<div style="margin-bottom:4px;"><label>${ball.name}:</label><input type="number" class="ballConsume" data-ballid="${ball.id}" data-index="${recordIndex}" min="0" value="0" style="width:80px;"></div>`).join('')}
                </div>
            `;
            container.appendChild(recordDiv);
            recordIndex++;
            recordDiv.querySelector('.remove-record').addEventListener('click', () => {
                recordDiv.remove();
            });
        }
        addRecordEntry();
        modal.querySelector('#addRecordBtn').addEventListener('click', addRecordEntry);
        modal.querySelector('#confirmAddRecords').onclick = () => {
            const spiritSelect = modal.querySelector('#newRecordSpiritSelect');
            const selectedOption = spiritSelect.options[spiritSelect.selectedIndex];
            const spiritId = spiritSelect.value;
            if(!spiritId) { alert("请选择精灵"); return; }
            const spiritName = selectedOption.dataset.name;
            const spiritAttrs = JSON.parse(selectedOption.dataset.attrs);
            const customStartDate = modal.querySelector('#captureStartDateInput').value;
            const defaultSeasonId = selectedOption.dataset.defaultSeason ? parseInt(selectedOption.dataset.defaultSeason) : null;
            const method = modal.querySelector('#newRecordMethod').value;
            const recordEntries = document.querySelectorAll('#recordsContainer .record-entry');
            if(recordEntries.length === 0) { alert("请至少添加一条记录"); return; }
            const consumptionLogs = [];
            let totalConsumption = {};
            let finalCaptureTime = null;
            let hasFinal = false;
            for(let entry of recordEntries) {
                const type = entry.querySelector('.recordType').value;
                let time = entry.querySelector('.recordTime').value;
                if(!time) { alert("请为每条记录填写时间"); return; }
                if(type === 'final') { hasFinal = true; finalCaptureTime = time; }
                const ballConsumes = entry.querySelectorAll('.ballConsume');
                const consumption = {};
                for(let inp of ballConsumes) {
                    let ballId = parseInt(inp.dataset.ballid);
                    let val = parseInt(inp.value);
                    if(isNaN(val) || val<=0) continue;
                    consumption[ballId] = val;
                }
                if(Object.keys(consumption).length === 0) {
                    alert(`记录 ${entry.querySelector('.recordType').selectedOptions[0].text} 没有填写任何消耗，请至少填写一种球的数量`);
                    return;
                }
                consumptionLogs.push({
                    timestamp: new Date(time).toISOString(),
                    consumedBalls: consumption,
                    type: type,
                    note: type === 'history' ? '历史补录' : (type === 'pause' ? '暂停记录' : '最终捕捉')
                });
                for(let [bid,amt] of Object.entries(consumption)) {
                    totalConsumption[bid] = (totalConsumption[bid] || 0) + amt;
                }
            }
            if(!hasFinal) {
                alert("必须包含一条「最终」类型的记录，用于确定捕捉完成时间");
                return;
            }
            const existingSpiritIndex = spirits.findIndex(s => s.name === spiritName);
            if(existingSpiritIndex !== -1) {
                spirits.splice(existingSpiritIndex, 1);
                if(activeTargetId && !spirits.some(s=>s.id===activeTargetId)) activeTargetId = null;
            }
            const newCapturedId = nextCapturedId++;
            capturedSpirits.push({
                id: newCapturedId,
                name: spiritName,
                attrs: spiritAttrs,
                requiredCount: 0,
                consumedBalls: totalConsumption,
                consumptionLogs: consumptionLogs,
                capturedAt: new Date(finalCaptureTime).toISOString(),
                startDate: customStartDate || captureStartDate || "未知",
                seasonId: defaultSeasonId,
                captureMethod: method
            });
            refreshIdSequences();
            persistAll();
            modal.remove();
            fullRender();
            alert(`成功添加 ${spiritName} 的捕捉记录，共 ${consumptionLogs.length} 条消耗记录。`);
        };
        modal.querySelector('#cancelAddRecords').onclick = () => modal.remove();
    }

    function showRemainingStockDialog(spirit, title) {
        return new Promise((resolve) => {
            if(!lastCaptureStock) {
                alert("缺少上次库存快照，请先开始捕捉");
                resolve(null);
                return;
            }
            const consumableBalls = getConsumableBallsForSpirit(spirit);
            let html = `<div class="modal-content"><h3>${title}</h3><p>${escapeHtml(spirit.name)}</p>`;
            html += `<div style="font-size:0.7rem; margin-bottom:8px;">请填写当前背包中<b>剩余</b>的咕噜球数量：</div>`;
            for(let ball of consumableBalls) {
                let currentStock = inventory[ball.id] || 0;
                html += `<div style="margin-bottom:8px;">
                            <label>${ball.name} (当前库存 ${currentStock}): </label>
                            <input type="number" id="remain_${ball.id}" min="0" max="${currentStock}" value="${currentStock}" style="width:90px;">
                         </div>`;
            }
            html += `<div style="display:flex; gap:8px; margin-top:16px;"><button id="confirmRemain">确认</button><button id="cancelRemain">取消</button></div></div>`;
            const modal = document.createElement('div'); modal.className = 'modal';
            modal.innerHTML = html;
            document.body.appendChild(modal);
            modal.querySelector('#confirmRemain').onclick = () => {
                const remaining = {};
                for(let ball of consumableBalls) {
                    let val = parseInt(modal.querySelector(`#remain_${ball.id}`).value);
                    if(isNaN(val)) val = inventory[ball.id] || 0;
                    if(val < 0) val = 0;
                    if(val > (inventory[ball.id] || 0)) val = inventory[ball.id] || 0;
                    remaining[ball.id] = val;
                }
                const consumption = {};
                let valid = true;
                for(let ball of consumableBalls) {
                    let prev = lastCaptureStock[ball.id] || 0;
                    let remain = remaining[ball.id];
                    let used = prev - remain;
                    if(used < 0) {
                        if(confirm(`检测到 ${ball.name} 库存增加了 ${-used} 个（可能通过战斗/购买获得）。是否将当前库存同步为新快照，并忽略本次消耗记录？`)) {
                            lastCaptureStock = { ...inventory };
                            persistAll();
                            used = 0;
                        } else {
                            valid = false;
                            break;
                        }
                    }
                    if(used > 0) consumption[ball.id] = used;
                }
                if(!valid) {
                    modal.remove();
                    resolve(null);
                    return;
                }
                for(let ball of consumableBalls) {
                    inventory[ball.id] = remaining[ball.id];
                }
                lastCaptureStock = { ...inventory };
                persistAll();
                modal.remove();
                resolve({ consumption, remaining });
            };
            modal.querySelector('#cancelRemain').onclick = () => { modal.remove(); resolve(null); };
        });
    }

    async function pauseCapture(spirit) {
        if(!captureSnapshot){ alert("请先开始捕捉"); return; }
        const result = await showRemainingStockDialog(spirit, "⏸️ 暂停捕捉 - 记录当前剩余库存");
        if(!result) return;
        const { consumption, remaining } = result;
        if(Object.keys(consumption).length === 0) {
            alert("没有消耗任何咕噜球，无需记录");
            return;
        }
        if(!spirit.consumptionLogs) spirit.consumptionLogs = [];
        spirit.consumptionLogs.push({
            timestamp: new Date().toISOString(),
            consumedBalls: consumption,
            remainingAfter: remaining,
            type: "pause"
        });
        persistAll();
        fullRender();
        alert(`已记录暂停消耗，${spirit.name} 累计消耗已更新。`);
    }
    async function finalCapture(spirit) {
        if(!captureSnapshot){ alert("请先开始捕捉"); return; }
        // 弹出获取方式选择
        const methodPromise = new Promise((resolve) => {
            const modal = document.createElement('div'); modal.className = 'modal';
            modal.innerHTML = `<div class="modal-content">
                <h3>选择获取方式</h3>
                <p>请选择该精灵的获取方式：</p>
                <select id="captureMethodSelect" style="width:100%; margin:10px 0;">
                    <option value="自己捕捉">自己捕捉</option>
                    <option value="朋友赠送">朋友赠送</option>
                    <option value="赛季特色">赛季特色</option>
                </select>
                <div style="display:flex; gap:8px;">
                    <button id="confirmMethod" class="primary">确认</button>
                    <button id="cancelMethod">取消</button>
                </div>
            </div>`;
            document.body.appendChild(modal);
            modal.querySelector('#confirmMethod').onclick = () => {
                const method = modal.querySelector('#captureMethodSelect').value;
                modal.remove();
                resolve(method);
            };
            modal.querySelector('#cancelMethod').onclick = () => {
                modal.remove();
                resolve(null);
            };
        });
        const method = await methodPromise;
        if (!method) {
            alert("已取消捕捉记录");
            return;
        }

        const result = await showRemainingStockDialog(spirit, "🎯 我已捕捉 - 记录当前剩余库存");
        if(!result) return;
        const { consumption, remaining } = result;
        if(!spirit.consumptionLogs) spirit.consumptionLogs = [];
        spirit.consumptionLogs.push({
            timestamp: new Date().toISOString(),
            consumedBalls: consumption,
            remainingAfter: remaining,
            type: "final"
        });
        const totalConsumption = {};
        for(let log of spirit.consumptionLogs) {
            for(let [bid,amt] of Object.entries(log.consumedBalls)) {
                totalConsumption[bid] = (totalConsumption[bid] || 0) + amt;
            }
        }
        let preset = presetSpirits.find(p => p.name === spirit.name);
        let seasonId = preset ? preset.defaultSeasonId : null;
        capturedSpirits.push({
            id: nextCapturedId++,
            name: spirit.name,
            attrs: [...spirit.attrs],
            requiredCount: spirit.requiredCount,
            consumedBalls: totalConsumption,
            consumptionLogs: spirit.consumptionLogs,
            capturedAt: new Date().toISOString(),
            startDate: captureStartDate || "未知",
            seasonId: seasonId,
            captureMethod: method
        });
        spirits = spirits.filter(s=>s.id!==spirit.id);
        if(activeTargetId===spirit.id) activeTargetId=null;
        refreshIdSequences();
        persistAll();
        fullRender();
        alert(`成功捕捉 ${spirit.name}！`);
    }

    function updateSeasonFilterSelect() {
        let sel = document.getElementById("seasonFilterSelect");
        if(!sel) return;
        let sortedSeasons = [...seasons].sort((a,b)=>b.order - a.order);
        let html = `<option value="__ALL__" ${currentSeasonFilter === null ? 'selected' : ''}>🏆 全部赛季</option>`;
        sortedSeasons.forEach(s => {
            html += `<option value="${s.id}" ${currentSeasonFilter === s.id ? 'selected' : ''}>${escapeHtml(s.name)}</option>`;
        });
        sel.innerHTML = html;
    }
    function renderAvgStats() {
        const container = document.getElementById("avgStatsContainer");
        if(!container) return;
        let filtered = capturedSpirits;
        if(currentSeasonFilter !== null) {
            filtered = capturedSpirits.filter(cap => cap.seasonId === currentSeasonFilter);
        }
        // 仅统计“自己捕捉”的记录
        filtered = filtered.filter(cap => cap.captureMethod === "自己捕捉");
        if(filtered.length === 0) {
            container.innerHTML = "<div>暂无自己捕捉的记录，无法统计平均消耗</div>";
            return;
        }
        let totals = [];
        for(let cap of filtered) {
            let total = 0;
            for(let [bid, num] of Object.entries(cap.consumedBalls)) {
                total += num;
            }
            totals.push(total);
        }
        totals.sort((a,b)=>a-b);
        const count = totals.length;
        const sumAll = totals.reduce((a,b)=>a+b,0);
        const avgAll = sumAll / count;
        let avgTrimmed = null;
        if(count > 2) {
            const trimmed = totals.slice(1, -1);
            const sumTrimmed = trimmed.reduce((a,b)=>a+b,0);
            avgTrimmed = sumTrimmed / trimmed.length;
        }
        container.innerHTML = `<strong>📊 平均消耗统计 (${currentSeasonFilter === null ? '全部赛季' : (seasons.find(s=>s.id===currentSeasonFilter)?.name || '未知赛季')})</strong><br>
        🎯 所有精灵平均: ${avgAll.toFixed(1)} 个咕噜球<br>
        ✨ 去除最高/最低后平均: ${avgTrimmed !== null ? avgTrimmed.toFixed(1) : '不足3只，无法计算'} 个咕噜球`;
    }
    function renderCapturedList() {
        const container = document.getElementById("capturedListContainer");
        if(!container) return;
        if(capturedSpirits.length===0){ container.innerHTML="<div>暂无记录</div>"; return; }
        let filtered = capturedSpirits;
        if(currentSeasonFilter !== null) {
            filtered = capturedSpirits.filter(cap => cap.seasonId === currentSeasonFilter);
        }
        let groups = new Map();
        for(let cap of filtered) {
            let sid = cap.seasonId;
            if(!groups.has(sid)) groups.set(sid, []);
            groups.get(sid).push(cap);
        }
        let sortedSeasonIds = Array.from(groups.keys()).sort((a,b) => {
            if(a === null) return 1;
            if(b === null) return -1;
            let sa = seasons.find(s=>s.id===a);
            let sb = seasons.find(s=>s.id===b);
            let orderA = sa ? sa.order : 0;
            let orderB = sb ? sb.order : 0;
            return orderB - orderA;
        });
        let html = "";
        let latestSeasonId = null;
        if(seasons.length) {
            let sortedSeasons = [...seasons].sort((a,b)=>b.order - a.order);
            if(sortedSeasons.length) latestSeasonId = sortedSeasons[0].id;
        }
        for(let sid of sortedSeasonIds) {
            let caps = groups.get(sid);
            let seasonName = sid === null ? "📭 未分类" : (seasons.find(s=>s.id===sid)?.name || "未知赛季");
            let groupId = `season_group_${sid === null ? 'null' : sid}`;
            let isLatest = (sid !== null && sid === latestSeasonId);
            let collapsedClass = (isLatest) ? "" : "collapsed";
            html += `<div class="season-group">
                        <div class="season-header" data-group="${groupId}">
                            <span>🏆 ${escapeHtml(seasonName)} (${caps.length})</span>
                            <span class="badge">${collapsedClass ? '展开' : '折叠'}</span>
                        </div>
                        <div id="${groupId}" class="season-content ${collapsedClass}">`;
            for(let cap of caps) {
                const totalMap = {};
                for(let [bid, num] of Object.entries(cap.consumedBalls)) {
                    totalMap[bid] = (totalMap[bid] || 0) + num;
                }
                let totalParts = [];
                let totalBalls = 0;
                for(let [bid, num] of Object.entries(totalMap)) {
                    let ball = ballTypes.find(b=>b.id==bid);
                    if(ball) { totalParts.push(`${num}${ball.name}`); totalBalls += num; }
                }
                let totalSummary = totalParts.join('+') + `=${totalBalls}咕噜球`;
                let logsHtml = "";
                if(cap.consumptionLogs && cap.consumptionLogs.length) {
                    logsHtml = `<div class="log-detail"><strong>📋 消耗记录详情：</strong>`;
                    cap.consumptionLogs.forEach(log => {
                        let logParts = Object.entries(log.consumedBalls).map(([bid,amt])=>{
                            let ball = ballTypes.find(b=>b.id==bid);
                            return ball ? `${ball.name}:${amt}` : '';
                        }).filter(t=>t).join(', ');
                        let typeLabel = log.type === 'history' ? '📜 历史补录' : (log.type === 'pause' ? '⏸️ 暂停' : '🎯 最终');
                        logsHtml += `<div>${typeLabel} ${new Date(log.timestamp).toLocaleString()} → 消耗: ${logParts}</div>`;
                    });
                    logsHtml += `</div>`;
                }
                // 获取方式标签
                let methodLabel = cap.captureMethod || "自己捕捉";
                let methodEmoji = methodLabel === '自己捕捉' ? '🎯' : (methodLabel === '朋友赠送' ? '🎁' : '📖');
                html += `<div class="captured-item">
                            <div><strong>✅ ${escapeHtml(cap.name)}</strong> ${cap.consumptionLogs?.some(l=>l.type==='history') ? '<span class="badge">📜 历史补录</span>' : ''} <span class="capture-method">${methodEmoji} ${methodLabel}</span></div>
                            <div>${cap.attrs.join("·")}</div>
                            <div><strong>总消耗:</strong> ${totalSummary}</div>
                            <div>开始: ${cap.startDate ? (cap.startDate === "历史补录" ? "历史补录" : new Date(cap.startDate).toLocaleString()) : "未知"} | 捕捉: ${new Date(cap.capturedAt).toLocaleString()}</div>
                            ${logsHtml}
                            <div class="captured-actions">
                                <button class="small edit-captured" data-id="${cap.id}">✏️ 编辑</button>
                                <button class="small danger delete-captured" data-id="${cap.id}">🗑️ 删除</button>
                            </div>
                        </div>`;
            }
            html += `</div></div>`;
        }
        container.innerHTML = html;
        document.querySelectorAll('.season-header').forEach(header => {
            header.addEventListener('click', () => {
                let groupId = header.dataset.group;
                let content = document.getElementById(groupId);
                if(content) {
                    content.classList.toggle('collapsed');
                    let badgeSpan = header.querySelector('.badge');
                    if(badgeSpan) {
                        badgeSpan.innerText = content.classList.contains('collapsed') ? '展开' : '折叠';
                    }
                }
            });
        });
        document.querySelectorAll('.edit-captured').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                let id = parseInt(btn.dataset.id);
                editCapturedRecord(id);
            });
        });
        document.querySelectorAll('.delete-captured').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                let id = parseInt(btn.dataset.id);
                deleteCapturedRecord(id);
            });
        });
    }

    function renderSpiritGrid() {
        const container = document.getElementById("spiritGridContainer");
        if(!container) return;
        let displaySpirits = getFilteredSpiritsForDisplay();
        if(displaySpirits.length===0) {
            container.innerHTML="<div style='grid-column:1/-1; text-align:center; padding:20px;'>✨ 暂无待捕捉精灵</div>";
            return;
        }
        let html = "";
        for(let sp of displaySpirits) {
            // ---- 查找该精灵在预设库中的分类信息 ----
            let preset = presetSpirits.find(p => p.name === sp.name);
            let categoryDisplay = '';
            let categoryHint = '';
            if (preset && preset.category) {
                let categoryIcon = preset.category === '通行证精灵' ? '📜' : '🏷️';
                categoryDisplay = `<span class="badge" style="background:#e8f0e6;">${categoryIcon} ${escapeHtml(preset.category)}</span>`;

                // ---- 根据分类显示不同的备注提示 ----
                if (preset.category === '通行证精灵') {
                    categoryHint = '💡 通行证精灵：可通过赛季通行证获取';
                } else {
                    // 尝试查找该分类所属赛季，获取更多信息
                    let season = seasons.find(s => s.id === preset.defaultSeasonId);
                    if (season) {
                        categoryHint = `💡 ${preset.category}：${season.name} 赛季专属精灵`;
                    } else {
                        categoryHint = `💡 ${preset.category}：赛季专属精灵`;
                    }
                }
            }

            const matchedAttrBalls = getMatchedAttributeBallsForSpirit(sp).map(b=>b.name).join(", ");
            const isActive = (activeTargetId === sp.id);
            const isSelected = deleteMode && selectedDeleteSpiritIds.has(sp.id);
            let typeIcon = sp.type === 'wonder' ? '✨' : '🍃';

            // 消耗预览（保持不变）
            let totalConsumptionPreview = {};
            if(sp.consumptionLogs && sp.consumptionLogs.length) {
                for(let log of sp.consumptionLogs) {
                    for(let [bid,amt] of Object.entries(log.consumedBalls)) {
                        totalConsumptionPreview[bid] = (totalConsumptionPreview[bid] || 0) + amt;
                    }
                }
            }
            let previewText = Object.entries(totalConsumptionPreview).map(([bid,amt]) => {
                let ball = ballTypes.find(b=>b.id==bid);
                return ball ? `${ball.name}:${amt}` : '';
            }).filter(t=>t).join(', ');

            html += `<div class="spirit-card ${isActive?'highlight':''} ${isSelected?'selected-delete':''}" data-id="${sp.id}">
                        <div class="spirit-name">${typeIcon} ${escapeHtml(sp.name)} ${sp.type === 'wonder' ? '<span class="badge">奇遇</span>' : ''}</div>
                        <div class="spirit-attrs">${sp.attrs.join(" · ")}</div>
                        ${categoryDisplay ? `<div style="margin: 4px 0;">${categoryDisplay}</div>` : ''}
                        ${categoryHint ? `<div style="font-size:0.7rem; color:#5a7a4a; margin: 2px 0 4px 0;">${categoryHint}</div>` : ''}
                        <div class="match-badge">🎯 可匹配: ${matchedAttrBalls || "无"}</div>
                        <div class="flex-between" style="margin-top: 6px;">
                            <span style="font-size:0.7rem;">所需球数</span>
                            <input type="number" class="edit-need-small" data-id="${sp.id}" value="${sp.requiredCount}" step="50" min="1" style="width:80px;">
                        </div>
                        <div class="capture-check">
                            <button class="small pause-btn" data-id="${sp.id}">⏸️ 暂停捕捉</button>
                            <button class="small primary capture-final-btn" data-id="${sp.id}">🎯 我已捕捉</button>
                        </div>
                        ${sp.consumptionLogs && sp.consumptionLogs.length ? `
                        <div class="consumption-summary" data-id="${sp.id}">
                            <span>📊 已消耗: ${previewText || "无"}</span>
                            <span>▼</span>
                        </div>
                        <div class="consumption-detail" data-id="${sp.id}" id="detail_${sp.id}">
                            ${sp.consumptionLogs.map((log,idx)=>`<div>${log.type==='history'?'📜 历史补录':(log.type==='pause'?'⏸️ 暂停': '🎯 最终')}: ${new Date(log.timestamp).toLocaleString()} - 消耗: ${Object.entries(log.consumedBalls).map(([bid,amt])=>`${ballTypes.find(b=>b.id==bid)?.name}:${amt}`).join(', ')}</div>`).join('')}
                        </div>
                        ` : ''}
                    </div>`;
        }
        container.innerHTML = html;
        attachSpiritCardEvents();
    }
    function attachSpiritCardEvents() {
        document.querySelectorAll(".edit-need-small").forEach(inp=>{
            inp.addEventListener("change",(e)=>{
                let id=parseInt(inp.dataset.id);
                let val=parseInt(inp.value);
                if(isNaN(val)||val<1) val=1;
                let sp=spirits.find(s=>s.id===id);
                if(sp) sp.requiredCount=val;
                persistAll(); fullRender();
            });
        });
        document.querySelectorAll(".pause-btn").forEach(btn=>{
            btn.addEventListener("click",async(e)=>{
                e.stopPropagation();
                let id=parseInt(btn.dataset.id);
                let sp=spirits.find(s=>s.id===id);
                if(sp) await pauseCapture(sp);
            });
        });
        document.querySelectorAll(".capture-final-btn").forEach(btn=>{
            btn.addEventListener("click",async(e)=>{
                e.stopPropagation();
                let id=parseInt(btn.dataset.id);
                let sp=spirits.find(s=>s.id===id);
                if(sp) await finalCapture(sp);
            });
        });
        document.querySelectorAll(".toggle-prism").forEach(btn=>{
            btn.addEventListener("click",(e)=>{
                e.stopPropagation();
                let id=parseInt(btn.dataset.id);
                let sp=spirits.find(s=>s.id===id);
                if(sp) {
                    sp.prismWarning = !sp.prismWarning;
                    persistAll();
                    fullRender();
                }
            });
        });
        document.querySelectorAll(".consumption-summary").forEach(sum=>{
            sum.addEventListener("click",(e)=>{
                e.stopPropagation();
                let id=parseInt(sum.dataset.id);
                let detailDiv = document.getElementById(`detail_${id}`);
                if(detailDiv) {
                    if(detailDiv.style.display === "none" || detailDiv.style.display === "") detailDiv.style.display = "block";
                    else detailDiv.style.display = "none";
                }
            });
        });
        if(deleteMode){
            document.querySelectorAll(".spirit-card").forEach(card=>{
                card.addEventListener("click",(e)=>{
                    if(e.target.tagName==="BUTTON" || e.target.classList.contains("edit-need-small") || e.target.classList.contains("consumption-summary")) return;
                    let id=parseInt(card.dataset.id);
                    if(selectedDeleteSpiritIds.has(id)) selectedDeleteSpiritIds.delete(id);
                    else selectedDeleteSpiritIds.add(id);
                    renderSpiritGrid();
                });
            });
        }
    }

    function openBallEditDialog(ballId) {
        const ball = ballTypes.find(b=>b.id===ballId); if(!ball) return;
        const allAttrs = getAllAttributes();
        const modal=document.createElement('div'); modal.className='modal';
        modal.innerHTML=`<div class="modal-content"><h3>编辑球种</h3><div><label>名称</label><input id="editBallName" value="${escapeHtml(ball.name)}"></div><div><label>属性1</label><select id="editAttr1"><option value="">无</option>${allAttrs.map(a=>`<option value="${a}" ${ball.attr1===a?'selected':''}>${a}</option>`).join('')}</select></div><div><label>属性2</label><select id="editAttr2"><option value="">无</option>${allAttrs.map(a=>`<option value="${a}" ${ball.attr2===a?'selected':''}>${a}</option>`).join('')}</select></div><div><label>库存</label><input id="editStock" type="number" value="${inventory[ball.id]||0}" min="0"></div><div style="display:flex; gap:8px; margin-top:16px;"><button id="saveBallEdit">保存</button><button id="cancelModal">取消</button></div></div>`;
        document.body.appendChild(modal);
        modal.querySelector('#saveBallEdit').onclick=function() {
            try {
                let newName = modal.querySelector('#editBallName').value.trim()||ball.name;
                let newAttr1 = modal.querySelector('#editAttr1').value;
                let newAttr2 = modal.querySelector('#editAttr2').value;
                if(newAttr1 === "无" || newAttr1 === "") newAttr1 = "";
                if(newAttr2 === "无" || newAttr2 === "") newAttr2 = "";
                let newStock = parseInt(modal.querySelector('#editStock').value);
                if(isNaN(newStock)||newStock<0) newStock=0;
                let stockChanged = (newStock !== (inventory[ball.id]||0));
                if(captureSnapshot && stockChanged) {
                    if(confirm(`库存已修改，是否将当前库存同步为新的快照？这将影响后续捕捉消耗计算。`)) {
                        lastCaptureStock = { ...inventory };
                        lastCaptureStock[ball.id] = newStock;
                    }
                }
                ball.name = newName;
                ball.attr1 = newAttr1;
                ball.attr2 = newAttr2;
                inventory[ball.id] = newStock;
                persistAll();
                fullRender();
            } finally {
                modal.remove();
            }
        };
        modal.querySelector('#cancelModal').onclick=function() {
            modal.remove();
        };
    }

    function moveBallUp(index) {
        if (index <= 0) return;
        [ballTypes[index], ballTypes[index-1]] = [ballTypes[index-1], ballTypes[index]];
        persistAll();
        fullRender();
    }
    function moveBallDown(index) {
        if (index >= ballTypes.length - 1) return;
        [ballTypes[index], ballTypes[index+1]] = [ballTypes[index+1], ballTypes[index]];
        persistAll();
        fullRender();
    }

    function battleGet() {
        if(!captureSnapshot){ alert("请先开始捕捉，才能记录获得"); return; }
        let ballId = parseInt(document.getElementById("battleBallSelect").value);
        let amount = parseInt(document.getElementById("battleAmount").value);
        if(isNaN(amount) || amount <= 0) { alert("数量无效"); return; }
        inventory[ballId] = (inventory[ballId] || 0) + amount;
        const now = new Date();
        battleRecords.push({
            ballId, amount,
            timestamp: now.toISOString(),
            date: now.toISOString().slice(0,10),
            type: "战斗/购买"
        });
        lastCaptureStock = { ...inventory };
        persistAll();
        fullRender();
        alert(`获得 ${amount} 个 ${ballTypes.find(b=>b.id===ballId)?.name}`);
    }

    function openSynthesisDialog() {
        if(!captureSnapshot){ alert("请先开始捕捉，才能记录合成增量"); return; }
        const normalBall = ballTypes.find(b=>b.name === "普通咕噜球");
        if(!normalBall) { alert("未找到普通咕噜球"); return; }
        const normalStock = inventory[normalBall.id] || 0;
        if(normalStock <= 0) { alert("普通咕噜球库存不足，无法合成"); return; }
        const attributeBalls = ballTypes.filter(b => isAttributeBall(b));
        if(attributeBalls.length === 0) { alert("没有可合成的属性球"); return; }
        const modal = document.createElement('div'); modal.className = 'modal';
        let ballOptions = `<select id="synthesisTargetBall" style="width:100%; margin-bottom:12px;">`;
        attributeBalls.forEach(b => ballOptions += `<option value="${b.id}">${b.name} (${getBallAttrDisplay(b)})</option>`);
        ballOptions += `</select>`;
        modal.innerHTML = `<div class="modal-content"><h3>合成属性球</h3><p>消耗 1 个普通咕噜球 合成 1 个属性球 (1:1)</p><div>选择目标球种: ${ballOptions}</div><div><label>数量</label><input type="number" id="synthesisAmount" min="1" max="${normalStock}" value="1"></div><div style="display:flex; gap:8px; margin-top:16px;"><button id="confirmSynthesis">合成</button><button id="cancelSynthesis">取消</button></div></div>`;
        document.body.appendChild(modal);
        modal.querySelector('#confirmSynthesis').onclick = () => {
            let targetId = parseInt(modal.querySelector('#synthesisTargetBall').value);
            let amount = parseInt(modal.querySelector('#synthesisAmount').value);
            if(isNaN(amount) || amount <= 0) { alert("数量无效"); modal.remove(); return; }
            if(amount > (inventory[normalBall.id] || 0)) { alert("普通咕噜球不足"); modal.remove(); return; }
            inventory[normalBall.id] -= amount;
            inventory[targetId] = (inventory[targetId] || 0) + amount;
            const now = new Date();
            battleRecords.push({
                ballId: targetId, amount,
                timestamp: now.toISOString(),
                date: now.toISOString().slice(0,10),
                type: "合成"
            });
            lastCaptureStock = { ...inventory };
            persistAll(); fullRender();
            modal.remove();
            alert(`成功合成 ${amount} 个 ${ballTypes.find(b=>b.id===targetId)?.name}`);
        };
        modal.querySelector('#cancelSynthesis').onclick = () => modal.remove();
    }

    function renderBattlePanel() {
        let sel = document.getElementById("battleBallSelect");
        if(sel) sel.innerHTML = ballTypes.map(b=>`<option value="${b.id}">${b.name}</option>`).join('');
        let filterDate = document.getElementById("recordDateFilter").value;
        if(!filterDate) {
            filterDate = new Date().toISOString().slice(0,10);
            document.getElementById("recordDateFilter").value = filterDate;
        }
        const filtered = battleRecords.filter(rec => rec.date === filterDate);
        let logDiv = document.getElementById("battleLogList");
        if(logDiv) {
            if(filtered.length===0) logDiv.innerHTML="<div>暂无记录</div>";
            else logDiv.innerHTML = filtered.slice().reverse().map(rec=>{
                let ball = ballTypes.find(b=>b.id===rec.ballId);
                let timeStr = rec.timestamp ? new Date(rec.timestamp).toLocaleTimeString() : "";
                return `<div class="log-entry">+${rec.amount} ${ball?.name||"球"} (${timeStr}) ${rec.type||""}</div>`;
            }).join('');
        }
    }

    function startCapture() {
        captureSnapshot = { ...inventory };
        lastCaptureStock = { ...inventory };
        battleRecords = [];
        captureStartDate = new Date().toISOString();
        persistAll();
        document.getElementById("captureStatus").innerHTML = `📸 捕捉已开始 ${new Date(captureStartDate).toLocaleString()} (初始快照已记录)`;
        fullRender();
    }
    function renderBallsGrid() {
        const container = document.getElementById("ballsGridContainer");
        if(!container) return;
        let html = "";
        ballTypes.forEach((ball, index) => {
            let attrText = getBallAttrDisplay(ball);
            let stock = inventory[ball.id]||0;
            html += `<div class="ball-card" data-ball-id="${ball.id}">
                        <div class="ball-name">${escapeHtml(ball.name)}</div>
                        <div class="ball-attrs">${attrText}</div>
                        <div class="ball-stock">📦 ${stock}</div>
                        <div class="move-buttons">
                            <button class="ball-move-up" data-index="${index}" title="上移">↑</button>
                            <button class="ball-move-down" data-index="${index}" title="下移">↓</button>
                        </div>
                     </div>`;
        });
        container.innerHTML = html;
        document.querySelectorAll(".ball-card").forEach(card=>card.addEventListener("click",(e)=>{
            if(e.target.closest('button')) return;
            openBallEditDialog(parseInt(card.dataset.ballId));
        }));
        document.querySelectorAll(".ball-move-up").forEach(btn => {
            btn.addEventListener("click", (e) => {
                e.stopPropagation();
                let index = parseInt(btn.dataset.index);
                moveBallUp(index);
            });
        });
        document.querySelectorAll(".ball-move-down").forEach(btn => {
            btn.addEventListener("click", (e) => {
                e.stopPropagation();
                let index = parseInt(btn.dataset.index);
                moveBallDown(index);
            });
        });
    }
    function renderPresetSpirits() {
        const container = document.getElementById("presetSpiritsContainer");
        if (!container) return;
        let search = document.getElementById("presetSearchInput")?.value.toLowerCase() || "";
        let filtered = presetSpirits.filter(p =>
            p.name.toLowerCase().includes(search) ||
            p.attrs.some(a => a.toLowerCase().includes(search))
        );

        filtered.sort((a, b) => {
            const aHasSeason = a.defaultSeasonId !== null && a.defaultSeasonId !== undefined;
            const bHasSeason = b.defaultSeasonId !== null && b.defaultSeasonId !== undefined;
            if (aHasSeason !== bHasSeason) {
                return aHasSeason ? 1 : -1;
            }
            if (aHasSeason && bHasSeason) {
                const orderA = seasons.find(s => s.id === a.defaultSeasonId)?.order || 0;
                const orderB = seasons.find(s => s.id === b.defaultSeasonId)?.order || 0;
                if (orderA !== orderB) return orderB - orderA;
            }
            const timeA = a.updatedAt ? new Date(a.updatedAt).getTime() : 0;
            const timeB = b.updatedAt ? new Date(b.updatedAt).getTime() : 0;
            return timeB - timeA;
        });

        if (filtered.length === 0) {
            container.innerHTML = "<div class='badge'>无匹配</div>";
            return;
        }
        let html = "";
        for (let p of filtered) {
            let typeIcon = p.type === 'wonder' ? '✨' : '🍃';
            let seasonName = p.defaultSeasonId ? (seasons.find(s => s.id === p.defaultSeasonId)?.name || '未知赛季') : '无';
            let categoryDisplay = p.category || '未分类';
            let categoryIcon = categoryDisplay === '通行证精灵' ? '📜' : '🏷️';

            html += `<div class="preset-item" data-id="${p.id}">
                        <div>
                            <strong>${escapeHtml(p.name)}</strong>
                            <span class="badge">${p.attrs.join("·")}</span>
                            ${typeIcon}
                            <span class="badge">赛季:${seasonName}</span>
                            <span class="badge">${categoryIcon} ${escapeHtml(categoryDisplay)}</span>
                        </div>
                        <div>
                            <button class="small edit-preset" data-id="${p.id}">✏️</button>
                            <button class="small danger delete-preset" data-id="${p.id}">🗑️ 删除</button>
                        </div>
                    </div>`;
        }
        container.innerHTML = html;
        document.querySelectorAll(".edit-preset").forEach(btn =>
            btn.addEventListener("click", () => openPresetEditDialog(presetSpirits.find(p => p.id == parseInt(btn.dataset.id))))
        );
        document.querySelectorAll(".delete-preset").forEach(btn => {
            btn.addEventListener("click", (e) => {
                e.stopPropagation();
                let id = parseInt(btn.dataset.id);
                deletePresetSpirit(id);
            });
        });
    }
    function deletePresetSpirit(presetId) {
        const preset = presetSpirits.find(p => p.id === presetId);
        if(!preset) return;
        if(confirm(`确定要删除预设精灵 "${preset.name}" 吗？\n此操作将同时清除所有同名待捕捉精灵和已捕捉记录的赛季关联，但不会删除已捕捉记录本身。`)) {
            presetSpirits = presetSpirits.filter(p => p.id !== presetId);
            spirits.forEach(s => {
                if (s.name === preset.name) {
                    s.type = "normal";
                }
            });
            capturedSpirits.forEach(c => {
                if (c.name === preset.name) {
                    c.seasonId = null;
                }
            });
            refreshIdSequences();
            persistAll();
            fullRender();
            alert(`已删除预设精灵 "${preset.name}"，并清除了相关赛季关联。`);
        }
    }

    function openPresetEditDialog(preset){
        const allAttrs=getAllAttributes();
        const modal=document.createElement('div'); modal.className='modal';

        // ---- 构建赛季和分类选项 ----
        let seasonOptions = `<select id="editPresetSeason"><option value="">-- 无 --</option>`;
        let sortedSeasons = [...seasons].sort((a,b)=>b.order - a.order);
        sortedSeasons.forEach(s=>{
            seasonOptions += `<option value="${s.id}" ${preset.defaultSeasonId === s.id ? 'selected' : ''}>${escapeHtml(s.name)}</option>`;
        });
        seasonOptions += `</select>`;

        // 分类选项（根据当前选中的赛季动态变化）
        let categoryOptions = `<option value="__通用__" ${preset.category === '通行证精灵' ? 'selected' : ''}>📜 通行证精灵（通用）</option>`;
        let currentSeason = seasons.find(s => s.id === preset.defaultSeasonId);
        if (currentSeason && currentSeason.categories) {
            currentSeason.categories.forEach(cat => {
                categoryOptions += `<option value="${escapeHtml(cat)}" ${preset.category === cat ? 'selected' : ''}>${escapeHtml(cat)}</option>`;
            });
        }

        modal.innerHTML=`<div class="modal-content"><h3>修改预设精灵</h3>
            <div><label>名称</label><input id="editPresetName" value="${escapeHtml(preset.name)}"></div>
            <div><label>属性1</label><select id="editPresetAttr1">${allAttrs.map(a=>`<option value="${a}" ${preset.attrs[0]===a?'selected':''}>${a}</option>`).join('')}</select></div>
            <div><label>属性2</label><select id="editPresetAttr2"><option value="none">无</option>${allAttrs.map(a=>`<option value="${a}" ${preset.attrs[1]===a?'selected':''}>${a}</option>`).join('')}</select></div>
            <div><label>类型</label><select id="editPresetType"><option value="normal" ${preset.type==='normal'?'selected':''}>🍃 非奇遇精灵</option><option value="wonder" ${preset.type==='wonder'?'selected':''}>✨ 奇遇精灵</option></select></div>
            <div><label>默认赛季</label>${seasonOptions}</div>
            <div><label>精灵分类</label>
                <select id="editPresetCategory" style="width:100%;">${categoryOptions}</select>
            </div>
            <div style="font-size:0.7rem; color:#5a7a4a; margin-top:4px;" id="editCategoryHint">💡 通行证精灵为通用分类</div>
            <div style="display:flex; gap:8px; margin-top:16px;"><button id="savePresetEdit">保存</button><button id="cancelModal">取消</button></div>
        </div>`;
        document.body.appendChild(modal);

        // ---- 当赛季变化时，更新分类下拉 ----
        const seasonSelect = modal.querySelector('#editPresetSeason');
        const categorySelect = modal.querySelector('#editPresetCategory');
        const hintDiv = modal.querySelector('#editCategoryHint');

        seasonSelect.addEventListener('change', function() {
            let seasonId = parseInt(this.value);
            let selectedSeason = seasons.find(s => s.id === seasonId);
            let options = `<option value="__通用__" ${preset.category === '通行证精灵' ? 'selected' : ''}>📜 通行证精灵（通用）</option>`;
            if (selectedSeason && selectedSeason.categories && selectedSeason.categories.length > 0) {
                selectedSeason.categories.forEach(cat => {
                    options += `<option value="${escapeHtml(cat)}" ${preset.category === cat ? 'selected' : ''}>${escapeHtml(cat)}</option>`;
                });
                hintDiv.textContent = `💡 当前赛季 "${selectedSeason.name}" 的专属分类`;
            } else if (selectedSeason) {
                hintDiv.textContent = `💡 当前赛季暂无专属分类，请在赛季管理中先添加分类`;
            } else {
                hintDiv.textContent = `💡 通行证精灵为通用分类，所有赛季均可使用`;
            }
            categorySelect.innerHTML = options;
        });

        modal.querySelector('#savePresetEdit').onclick = function() {
            try {
                const oldName = preset.name;
                preset.name = modal.querySelector('#editPresetName').value.trim() || preset.name;
                let a1 = modal.querySelector('#editPresetAttr1').value;
                let a2 = modal.querySelector('#editPresetAttr2').value;
                preset.attrs = a2 && a2 !== "none" ? [a1, a2] : [a1];
                preset.type = modal.querySelector('#editPresetType').value;
                let seasonVal = modal.querySelector('#editPresetSeason').value;
                preset.defaultSeasonId = seasonVal ? parseInt(seasonVal) : null;
                let category = modal.querySelector('#editPresetCategory').value;
                preset.category = category === '__通用__' ? '通行证精灵' : category;
                preset.updatedAt = new Date().toISOString();
                persistAll();
                syncWithPreset();
                persistAll();
                fullRender();
                alert(`预设精灵已更新，同时同步了所有同名待捕捉精灵的类型和已捕捉记录的赛季归属。`);
            } catch(e) {
                alert('保存失败：' + e.message);
            } finally {
                modal.remove();
            }
        };
        modal.querySelector('#cancelModal').onclick = function() {
            modal.remove();
        };
    }

    function renderSeasonsList() {
        const container = document.getElementById("seasonsListContainer");
        if(!container) return;
        if(seasons.length===0) { container.innerHTML="<div class='badge'>暂无赛季，请点击「新增赛季」</div>"; return; }
        let sorted = [...seasons].sort((a,b)=>b.order - a.order);
        let html = "";
        for(let s of sorted) {
            let dateInfo = s.startDate && s.endDate ? ` (${s.startDate} ~ ${s.endDate})` : '';
            html += `<div class="preset-item" data-id="${s.id}">
                        <div><strong>${escapeHtml(s.name)}</strong> <span class="badge">序号:${s.order}</span> ${dateInfo}</div>
                        <div>
                            <button class="small edit-season" data-id="${s.id}">✏️</button>
                            <button class="small danger delete-season" data-id="${s.id}">🗑️</button>
                        </div>
                    </div>`;
        }
        container.innerHTML = html;
        document.querySelectorAll('.edit-season').forEach(btn=>{
            btn.addEventListener('click',()=>{
                let id = parseInt(btn.dataset.id);
                let season = seasons.find(s=>s.id===id);
                if(season) editSeason(season);
            });
        });
        document.querySelectorAll('.delete-season').forEach(btn=>{
            btn.addEventListener('click',()=>{
                let id = parseInt(btn.dataset.id);
                deleteSeason(id);
            });
        });
    }
    function editSeason(season) {
        const modal = document.createElement('div'); modal.className='modal';

        // ---- 构建分类列表（含备注输入） ----
        let categoriesHtml = '';
        if (season.categories && season.categories.length > 0) {
            season.categories.forEach((cat, idx) => {
                let note = season.categoryNotes ? (season.categoryNotes[cat] || '') : '';
                categoriesHtml += `
                    <div style="display:flex; flex-direction:column; gap:4px; margin-bottom:8px; padding:8px; background:#f9fbf5; border-radius:12px; border:1px solid #e2e8d5;">
                        <div style="display:flex; gap:4px; align-items:center;">
                            <input type="text" class="season-category-input" value="${escapeHtml(cat)}" data-index="${idx}" style="flex:2;">
                            <button class="small remove-category-btn" data-index="${idx}">✖️</button>
                        </div>
                        <div style="display:flex; gap:4px; align-items:center;">
                            <span style="font-size:0.7rem; color:#5a7a4a; min-width:60px;">📝 备注：</span>
                            <input type="text" class="season-category-note" value="${escapeHtml(note)}" placeholder="分类备注（选填）" style="flex:3; font-size:0.75rem;">
                        </div>
                    </div>
                `;
            });
        }

        modal.innerHTML = `<div class="modal-content">
            <h3>编辑赛季</h3>
            <div><label>赛季名称</label><input id="editSeasonName" value="${escapeHtml(season.name)}"></div>
            <div><label>显示顺序 (数字越大越靠前)</label><input type="number" id="editSeasonOrder" value="${season.order}"></div>
            <div class="season-date-inputs">
                <div><label>开始日期</label><input type="date" id="editSeasonStart" value="${season.startDate || ''}"></div>
                <div><label>结束日期</label><input type="date" id="editSeasonEnd" value="${season.endDate || ''}"></div>
            </div>
            <div style="margin-top:12px;">
                <label><strong>精灵分类</strong> (每个赛季专属，通行证精灵为通用分类)</label>
                <div id="categoriesContainer">${categoriesHtml || '<div style="color:#7c9670; font-size:0.75rem;">暂无分类，点击下方添加</div>'}</div>
                <button id="addCategoryBtn" class="small" style="margin-top:4px;">+ 添加分类</button>
            </div>
            <div style="display:flex; gap:8px; margin-top:16px;">
                <button id="saveEdit" class="primary">保存</button>
                <button id="cancelEdit">取消</button>
            </div>
        </div>`;
        document.body.appendChild(modal);

        // ---- 添加分类（含备注输入） ----
        modal.querySelector('#addCategoryBtn').onclick = function() {
            const container = modal.querySelector('#categoriesContainer');
            // 移除"暂无分类"提示
            if (container.querySelector('div[style]') && container.children.length === 1) {
                container.innerHTML = '';
            }
            const newDiv = document.createElement('div');
            newDiv.style.cssText = 'display:flex; flex-direction:column; gap:4px; margin-bottom:8px; padding:8px; background:#f9fbf5; border-radius:12px; border:1px solid #e2e8d5;';
            newDiv.innerHTML = `
                <div style="display:flex; gap:4px; align-items:center;">
                    <input type="text" class="season-category-input" value="" style="flex:2;" placeholder="输入分类名称">
                    <button class="small remove-category-btn">✖️</button>
                </div>
                <div style="display:flex; gap:4px; align-items:center;">
                    <span style="font-size:0.7rem; color:#5a7a4a; min-width:60px;">📝 备注：</span>
                    <input type="text" class="season-category-note" value="" placeholder="分类备注（选填）" style="flex:3; font-size:0.75rem;">
                </div>
            `;
            container.appendChild(newDiv);
            newDiv.querySelector('.remove-category-btn').onclick = function() {
                newDiv.remove();
                // 如果容器为空，显示提示
                if (container.children.length === 0) {
                    container.innerHTML = '<div style="color:#7c9670; font-size:0.75rem;">暂无分类，点击下方添加</div>';
                }
            };
        };

        // ---- 删除分类（绑定已有按钮） ----
        modal.querySelectorAll('.remove-category-btn').forEach(btn => {
            btn.onclick = function() {
                this.closest('div[style*="display:flex; flex-direction:column"]').remove();
                const container = modal.querySelector('#categoriesContainer');
                if (container.children.length === 0) {
                    container.innerHTML = '<div style="color:#7c9670; font-size:0.75rem;">暂无分类，点击下方添加</div>';
                }
            };
        });

        modal.querySelector('#saveEdit').onclick = function() {
            try {
                let newName = modal.querySelector('#editSeasonName').value.trim();
                if (!newName) { alert("赛季名称不能为空"); return; }
                let newOrder = parseInt(modal.querySelector('#editSeasonOrder').value);
                if (isNaN(newOrder)) newOrder = season.order;
                let startDate = modal.querySelector('#editSeasonStart').value;
                let endDate = modal.querySelector('#editSeasonEnd').value;
                if (!startDate || !endDate) { alert("请填写开始日期和结束日期"); return; }
                if (new Date(startDate) > new Date(endDate)) { alert("结束日期不能早于开始日期"); return; }

                // ---- 收集分类及备注 ----
                let categories = [];
                let categoryNotes = {};
                modal.querySelectorAll('.season-category-input').forEach(input => {
                    let val = input.value.trim();
                    if (val) {
                        categories.push(val);
                        // 获取对应的备注
                        let parentDiv = input.closest('div[style*="display:flex; flex-direction:column"]');
                        let noteInput = parentDiv ? parentDiv.querySelector('.season-category-note') : null;
                        if (noteInput) {
                            let noteVal = noteInput.value.trim();
                            if (noteVal) categoryNotes[val] = noteVal;
                        }
                    }
                });

                season.name = newName;
                season.order = newOrder;
                season.startDate = startDate;
                season.endDate = endDate;
                season.categories = categories;
                season.categoryNotes = categoryNotes;

                persistAll();
                fullRender();
                alert('赛季已更新');
            } catch(e) {
                alert('保存失败：' + e.message);
            } finally {
                modal.remove();
            }
        };
        modal.querySelector('#cancelEdit').onclick = function() {
            modal.remove();
        };
    }
    function deleteSeason(id) {
        let used = capturedSpirits.some(cap => cap.seasonId === id);
        if(used) {
            alert("无法删除：已有精灵关联此赛季，请先修改这些精灵的赛季归属。");
            return;
        }
        if(confirm("确定删除该赛季吗？")) {
            seasons = seasons.filter(s => s.id !== id);
            if (currentSeasonId === id) {
                const autoId = getCurrentSeasonId();
                if (autoId !== null) currentSeasonId = autoId;
                else if (seasons.length > 0) currentSeasonId = seasons[0].id;
                else currentSeasonId = null;
                localStorage.setItem('setting_current_season', String(currentSeasonId));
            }
            persistAll();
            fullRender();
        }
    }
    function addSeason() {
        const modal = document.createElement('div'); modal.className='modal';
        modal.innerHTML = `<div class="modal-content">
            <h3>新增赛季</h3>
            <div><label>赛季名称</label><input id="newSeasonName" placeholder="例如: S3"></div>
            <div><label>显示顺序 (数字越大越靠前)</label><input type="number" id="newSeasonOrder" value="0"></div>
            <div class="season-date-inputs">
                <div><label>开始日期</label><input type="date" id="newSeasonStart"></div>
                <div><label>结束日期</label><input type="date" id="newSeasonEnd"></div>
            </div>
            <div style="display:flex; gap:8px; margin-top:16px;"><button id="confirmAdd">添加</button><button id="cancelAdd">取消</button></div>
        </div>`;
        document.body.appendChild(modal);
        const now = new Date();
        const end = new Date(now);
        end.setDate(end.getDate() + 56);
        modal.querySelector('#newSeasonStart').value = now.toISOString().slice(0,10);
        modal.querySelector('#newSeasonEnd').value = end.toISOString().slice(0,10);
        modal.querySelector('#confirmAdd').onclick = function() {
            try {
                let name = modal.querySelector('#newSeasonName').value.trim();
                if (!name) { alert("请输入赛季名称"); return; }
                let order = parseInt(modal.querySelector('#newSeasonOrder').value);
                if (isNaN(order)) order = 0;
                let startDate = modal.querySelector('#newSeasonStart').value;
                let endDate = modal.querySelector('#newSeasonEnd').value;
                if (!startDate || !endDate) { alert("请填写开始日期和结束日期"); return; }
                if (new Date(startDate) > new Date(endDate)) { alert("结束日期不能早于开始日期"); return; }
                let maxId = Math.max(...seasons.map(s=>s.id), 0);
                let newId = maxId + 1;
                seasons.push({ id: newId, name: name, order: order, startDate: startDate, endDate: endDate });
                nextSeasonId = newId + 1;
                persistAll();
                fullRender();
                alert('赛季已添加');
            } catch(e) {
                alert('添加失败：' + e.message);
            } finally {
                modal.remove();
            }
        };
        modal.querySelector('#cancelAdd').onclick = function() {
            modal.remove();
        };
    }

    // ------------------- 导入导出 (通过Python桥接) -------------------
    function pasteImport() {
        let text = document.getElementById("pasteJsonText").value;
        if(!text.trim()) { alert("请先在文本框中粘贴 JSON 数据"); return; }
        let module = document.getElementById("pasteModuleSelect").value;
        if(pythonAPI) pythonAPI.importFromText(module, text);
        else alert("Python API 未就绪");
    }

    function initPythonAPI() {
        new QWebChannel(qt.webChannelTransport, function(channel) {
            pythonAPI = channel.objects.pythonAPI;
            // 注意：这个回调是异步的，init() 跑完时 pythonAPI 可能还是 null。
            // 数据包检测统一由 maybeAutoCheckUpdate() 在通道就绪后触发（先查版本，再查新增数据），
            // 这里不再单独发起，避免一次启动重复请求两次数据包。
            document.getElementById("exportWarehouseBtn")?.addEventListener("click", function() {
                if(pythonAPI) pythonAPI.exportWarehouse(JSON.stringify({ ballTypes, inventory }));
            });
            document.getElementById("importWarehouseBtn")?.addEventListener("click", function() {
                if(pythonAPI) pythonAPI.importWarehouse();
            });
            document.getElementById("exportPresetBtn")?.addEventListener("click", function() {
                if(pythonAPI) pythonAPI.exportPreset(JSON.stringify(presetSpirits));
            });
            document.getElementById("importPresetBtn")?.addEventListener("click", function() {
                if(pythonAPI) pythonAPI.importPreset();
            });
            document.getElementById("exportSeasonsBtn")?.addEventListener("click", function() {
                if(pythonAPI) pythonAPI.exportSeasons(JSON.stringify(seasons));
            });
            document.getElementById("importSeasonsBtn")?.addEventListener("click", function() {
                if(pythonAPI) pythonAPI.importSeasons();
            });
            document.getElementById("exportCapturedBtn")?.addEventListener("click", function() {
                if(pythonAPI) pythonAPI.exportCaptured(JSON.stringify(capturedSpirits));
            });
            document.getElementById("importCapturedBtn")?.addEventListener("click", function() {
                if(pythonAPI) pythonAPI.importCaptured();
            });
            document.getElementById("exportUnknownBtn")?.addEventListener("click", function() {
                if(pythonAPI) pythonAPI.exportUnknown(JSON.stringify(unknownRecords));
            });
            document.getElementById("exportAllDataBtn")?.addEventListener("click", function() {
                if(pythonAPI) pythonAPI.exportAllData(JSON.stringify({
                    ballTypes,
                    inventory,
                    presetSpirits,
                    spirits,
                    capturedSpirits,
                    seasons,
                    unknownRecords,
                    battleRecords,
                    growthData,
                    settings: {
                        settingRoundBalls,
                        settingPeople,
                        settingBallsPerSpirit,
                        currentSeasonId
                    },
                    exportTime: new Date().toISOString()
                }));
            });
            document.getElementById("importAllDataBtn")?.addEventListener("click", function() {
                if(pythonAPI) pythonAPI.importAllData();
            });
            document.getElementById("importUnknownBtn")?.addEventListener("click", function() {
                if(pythonAPI) pythonAPI.importUnknown();
            });
            document.getElementById("pasteImportBtn")?.addEventListener("click", pasteImport);
            document.getElementById("unknownCaptureBtn")?.addEventListener("click", showUnknownCaptureDialog);
            document.getElementById("checkUpdateBtn")?.addEventListener("click", function() { doCheckUpdate(false); });
            document.getElementById("resetUpdateUrlBtn")?.addEventListener("click", function() {
                // 清掉可能残留的旧清单地址（或指向缓存/失效镜像的自定义地址），恢复内置的 version.json 直链
                localStorage.removeItem('update_manifest_url');
                const def = DEFAULT_UPDATE_REPO || '';
                const defIsUrl = /^https?:\/\//i.test(def);
                const urlInp = document.getElementById('updateManifestUrl');
                if (urlInp) urlInp.value = defIsUrl ? def : '';
                if (!defIsUrl) {
                    const repoInp = document.getElementById('updateGithubRepo');
                    if (repoInp) repoInp.value = def;
                }
                const st = document.getElementById('updateStatus');
                if (st) { st.textContent = '已恢复默认更新地址，请再点一次「检查更新」'; st.style.color = '#5a7a4a'; }
            });
            console.log("Python API 已连接");
        });
    }

    function generateAttrOptions(sel, incNone=false){ let attrs=getAllAttributes(); let opts=incNone?`<option value="none">无</option>`:''; attrs.forEach(a=>opts+=`<option value="${a}" ${sel===a?'selected':''}>${a}</option>`); return opts; }
    function getAllAttributes(){ let s=new Set(); ballTypes.forEach(b=>{if(b.attr1 && b.attr1!=="无") s.add(b.attr1); if(b.attr2 && b.attr2!=="无") s.add(b.attr2);}); presetSpirits.forEach(p=>p.attrs.forEach(a=>s.add(a))); spirits.forEach(sp=>sp.attrs.forEach(a=>s.add(a))); if(s.size===0) return ["草","火","冰","地","幻","电","幽","虫","光","恶","机械","水","翼","毒","萌","普通","武","龙"]; return [...s]; }
    function updatePresetDropdown(){ let sel=document.getElementById("selectPresetSpirit"); if(!sel)return; let used=new Set([...spirits.map(s=>s.name),...capturedSpirits.map(c=>c.name)]); let available=presetSpirits.filter(p=>!used.has(p.name)); sel.innerHTML='<option value="">-- 选择 --</option>'; available.forEach(p=>sel.innerHTML+=`<option value="${escapeHtml(p.name)}">${p.name} (${p.attrs.join("·")})</option>`); }
    function updateTargetSelector(){ let sel=document.getElementById("selectTargetSpirit"); if(!sel)return; let displaySpirits = getFilteredSpiritsForDisplay(); sel.innerHTML='<option value="">-- 选择捕捉目标 --</option>'; displaySpirits.forEach(sp=>{ sel.innerHTML+=`<option value="${sp.id}" ${activeTargetId===sp.id?'selected':''}>${sp.name}</option>`; }); }
    function setActiveTarget(){ let sel=document.getElementById("selectTargetSpirit"); let val=parseInt(sel.value); if(!isNaN(val) && spirits.some(s=>s.id===val)) { activeTargetId=val; } else { activeTargetId=null; } persistAll(); fullRender(); }
    function clearActiveTarget(){ if(confirm("确定取消当前捕捉目标吗？")) { activeTargetId=null; persistAll(); fullRender(); } }
    function renderTargetHighlight(){ let cont=document.getElementById("targetHighlightInfo"); if(!cont)return; if(activeTargetId){ let sp=spirits.find(s=>s.id===activeTargetId); if(sp){ let matched=ballTypes.filter(b=>isAttributeBall(b) && (sp.attrs || []).some(sa=> [b.attr1, b.attr2].filter(a=>a && a.trim() && a !== "无").includes(sa))).map(b=>b.name).join(" → "); cont.innerHTML=`<strong>当前目标: ${sp.name}</strong><br>🎯 优先使用: ${matched || "无匹配属性球"}<br>（背包中对应属性球已高亮）`; } else cont.innerHTML=""; } else cont.innerHTML="请在上方选择捕捉目标"; }

    function syncBallsPerSpirit(newValue) {
        if (isNaN(newValue) || newValue < 1) return;
        spirits.forEach(s => s.requiredCount = newValue);
        settingBallsPerSpirit = newValue;
        localStorage.setItem('setting_balls_per_spirit', String(newValue));
        document.getElementById("settingBallsPerSpirit").value = newValue;
        renderDailyStats();
        persistAll();
        fullRender();
    }

    function globalSetNeed() {
        let defaultVal = settingBallsPerSpirit || 1200;
        let val = prompt("统一所需球数（此值将同步到「每只精灵所需球数」设置）", String(defaultVal));
        if(val===null)return;
        let num=parseInt(val);
        if(isNaN(num)||num<1) return;
        syncBallsPerSpirit(num);
        alert(`已将所有精灵所需球数设为 ${num}，并同步更新统计设置。`);
    }

    function toggleDeleteMode() {
        deleteMode = !deleteMode;
        selectedDeleteSpiritIds.clear();
        const bar = document.getElementById("deleteModeBar");
        const tip = document.getElementById("deleteModeTip");
        if(deleteMode) {
            bar.style.display = "block";
            tip.style.display = "block";
            alert("删除模式已开启，点击卡片即可选中/取消选中精灵，然后点击下方「确认删除选中精灵」按钮。");
        } else {
            bar.style.display = "none";
            tip.style.display = "none";
        }
        renderSpiritGrid();
    }
    function confirmDeleteSpirits() {
        if(selectedDeleteSpiritIds.size===0){ alert("未选中任何精灵"); return; }
        spirits = spirits.filter(s=>!selectedDeleteSpiritIds.has(s.id));
        if(activeTargetId && !spirits.some(s=>s.id===activeTargetId)) activeTargetId=null;
        selectedDeleteSpiritIds.clear();
        deleteMode=false;
        document.getElementById("deleteModeBar").style.display="none";
        document.getElementById("deleteModeTip").style.display="none";
        if(lockedOrderIds.length) {
            lockedOrderIds = lockedOrderIds.filter(id => spirits.some(s=>s.id===id));
            if(lockedOrderIds.length === 0 && orderLocked) {
                orderLocked = false;
            }
        }
        persistAll();
        fullRender();
        alert("已删除选中精灵");
    }
    function cancelDeleteMode() {
        deleteMode = false;
        selectedDeleteSpiritIds.clear();
        document.getElementById("deleteModeBar").style.display="none";
        document.getElementById("deleteModeTip").style.display="none";
        renderSpiritGrid();
    }
    function resetDateFilter() { document.getElementById("recordDateFilter").value = new Date().toISOString().slice(0,10); renderBattlePanel(); }
    function onSeasonFilterChange() {
        let sel = document.getElementById("seasonFilterSelect");
        let val = sel.value;
        if(val === "__ALL__") currentSeasonFilter = null;
        else currentSeasonFilter = parseInt(val);
        renderAvgStats();
        renderCapturedList();
    }
    function onTransferModeChange(mode) {
        currentTransferMode = mode;
        fullRender();
    }
    function onDisplayGroupChange(group) {
        currentDisplayGroup = group;
        fullRender();
    }

    let settingChangeTimer = null;
    function handleSettingChange() {
        if (settingChangeTimer) clearTimeout(settingChangeTimer);
        settingChangeTimer = setTimeout(() => {
            onSettingChange();
            settingChangeTimer = null;
        }, 50);
    }

    function onSettingChange() {
        let rb = parseInt(document.getElementById("settingRoundBalls").value);
        if (isNaN(rb) || rb < 1) rb = 240;
        settingRoundBalls = rb;
        localStorage.setItem('setting_round_balls', String(rb));
        let pp = parseInt(document.getElementById("settingPeople").value);
        if (isNaN(pp) || pp < 1) pp = 2;
        settingPeople = pp;
        localStorage.setItem('setting_people', String(pp));
        let bps = parseInt(document.getElementById("settingBallsPerSpirit").value);
        if (!isNaN(bps) && bps >= 1) {
            if (bps !== settingBallsPerSpirit) {
                syncBallsPerSpirit(bps);
            }
        }
        let cs = parseInt(document.getElementById("settingCurrentSeason").value);
        if (!isNaN(cs) && seasons.some(s => s.id === cs)) {
            currentSeasonId = cs;
            localStorage.setItem('setting_current_season', String(cs));
        } else {
            const autoId = getCurrentSeasonId();
            if (autoId !== null) {
                currentSeasonId = autoId;
                localStorage.setItem('setting_current_season', String(autoId));
                document.getElementById("settingCurrentSeason").value = String(autoId);
            } else if (seasons.length > 0) {
                currentSeasonId = seasons[0].id;
                localStorage.setItem('setting_current_season', String(currentSeasonId));
                document.getElementById("settingCurrentSeason").value = String(currentSeasonId);
            }
        }
        renderDailyStats();
        persistAll();
        fullRender();
        // 成长计划依赖赛季变化，重新渲染
        renderGrowthPlan();
    }

    // ===== 侧边栏导航 =====
    function initSidebar() {
        const sections = {
            tab1: [
                { label: '总缺口分析', id: 'card-total-gap' },
                { label: '当前捕捉目标', id: 'card-target' },
                { label: '待捕捉精灵', id: 'card-spirits' },
                { label: '未知捕捉', id: 'card-unknown' }
            ],
            tab2: [
                { label: '已捕捉记录', id: 'card-captured' },
                { label: '未知记录', id: 'card-unknown-list' }
            ],
            tab3: [],  // 成长计划无侧边栏
            tab4: [
                { label: '咕噜球仓库', id: 'card-warehouse' },
                { label: '战斗获得', id: 'card-battle' },
                { label: '预设精灵库', id: 'card-preset' },
                { label: '赛季管理', id: 'card-seasons' },
                { label: '捕捉统计设置', id: 'card-stats' },
                { label: '成长计划设置', id: 'card-growth-settings' },
                { label: '快速粘贴导入', id: 'card-paste' }
            ]
        };

        for (const [tabId, list] of Object.entries(sections)) {
            const tabContent = document.getElementById(tabId);
            if (!tabContent) continue;
            const oldSidebar = tabContent.querySelector('.tab-sidebar');
            if (oldSidebar) oldSidebar.remove();

            if (list.length === 0) continue;

            const sidebar = document.createElement('div');
            sidebar.className = 'tab-sidebar';
            list.forEach(item => {
                const a = document.createElement('a');
                a.textContent = item.label;
                a.dataset.target = item.id;
                a.addEventListener('click', (e) => {
                    e.preventDefault();
                    const target = document.getElementById(item.id);
                    if (target) {
                        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }
                    sidebar.querySelectorAll('a').forEach(el => el.classList.remove('active'));
                    a.classList.add('active');
                });
                sidebar.appendChild(a);
            });
            tabContent.appendChild(sidebar);
        }
    }

    // ===== 切换 Tab 记住滚动位置 =====
    function initTabs() {
        if (!window.scrollPositions) window.scrollPositions = {};
        document.querySelectorAll('.nav-item').forEach(tab => {
            tab.addEventListener('click', () => {
                let id = tab.dataset.tab;
                const currentActive = document.querySelector('.tab-content.active-tab');
                if (currentActive) {
                    window.scrollPositions[currentActive.id] = window.scrollY;
                }
                document.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active-tab'));
                document.getElementById(id).classList.add('active-tab');
                document.querySelectorAll('.nav-item').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                document.querySelectorAll('.tab-sidebar a').forEach(el => el.classList.remove('active'));
                requestAnimationFrame(() => {
                    if (window.scrollPositions[id] !== undefined) {
                        window.scrollTo(0, window.scrollPositions[id]);
                    } else {
                        window.scrollTo(0, 0);
                    }
                });
            });
        });
    }

    // ---- 新增：渲染分类备注（在每日需抓轮数下方） ----
    function renderCategoryNotes() {
        const container = document.getElementById("categoryNotesContainer");
        if (!container) return;

        // 收集所有精灵的分类及其备注
        let categoryInfo = {};
        let activeCategories = new Set();

        // 遍历所有待捕捉精灵，收集它们的分类
        for (let sp of spirits) {
            let preset = presetSpirits.find(p => p.name === sp.name);
            if (preset && preset.category) {
                let cat = preset.category;
                activeCategories.add(cat);
                // 查找该分类的备注
                if (preset.defaultSeasonId !== null) {
                    let season = seasons.find(s => s.id === preset.defaultSeasonId);
                    if (season && season.categoryNotes && season.categoryNotes[cat]) {
                        categoryInfo[cat] = {
                            note: season.categoryNotes[cat],
                            seasonName: season.name,
                            seasonId: season.id
                        };
                    } else if (cat === '通行证精灵') {
                        // 通行证精灵的默认备注
                        categoryInfo[cat] = {
                            note: '可通过赛季通行证获取',
                            seasonName: '通用',
                            seasonId: null
                        };
                    }
                } else if (cat === '通行证精灵') {
                    categoryInfo[cat] = {
                        note: '可通过赛季通行证获取',
                        seasonName: '通用',
                        seasonId: null
                    };
                }
            }
        }

        if (activeCategories.size === 0) {
            container.innerHTML = '';
            return;
        }

        // 构建显示HTML
        let html = `<div style="display:flex; flex-wrap:wrap; gap:8px; margin-top:8px; padding:8px 12px; background:#f8faf5; border-radius:16px; border:1px solid #e2e8d5;">`;
        html += `<span style="font-weight:600; font-size:0.8rem; color:#3d6b3d; margin-right:4px;">📌 分类备注：</span>`;

        for (let cat of activeCategories) {
            let info = categoryInfo[cat];
            let noteText = info ? info.note : '暂无备注';
            let seasonTag = info && info.seasonName !== '通用' ? `[${info.seasonName}]` : '';
            // ---- 判断该分类是否已被选中（即有精灵标记为当前目标） ----
            let isActive = false;
            if (activeTargetId !== null) {
                let targetSpirit = spirits.find(s => s.id === activeTargetId);
                if (targetSpirit) {
                    let targetPreset = presetSpirits.find(p => p.name === targetSpirit.name);
                    if (targetPreset && targetPreset.category === cat) {
                        isActive = true;
                    }
                }
            }
            // 如果没有设置目标，检查是否有任何精灵属于该分类（可根据需要调整）
            if (!isActive) {
                // 如果有精灵属于该分类且该精灵被高亮（比如在捕捉目标中），这里保持与目标一致
                // 实际上我们只用 activeTargetId 判断
            }

            let bgColor = isActive ? '#fff0cc' : '#eef2e6';
            let borderColor = isActive ? '#f5a623' : '#d9e3cf';
            html += `<span style="background:${bgColor}; border:1px solid ${borderColor}; border-radius:16px; padding:3px 12px; font-size:0.75rem; display:inline-flex; align-items:center; gap:4px;">
                <strong>${escapeHtml(cat)}</strong>
                ${seasonTag}
                <span style="color:#5a7a4a;">${escapeHtml(noteText)}</span>
                ${isActive ? ' ⭐' : ''}
            </span>`;
        }
        html += `</div>`;
        container.innerHTML = html;
    }

    function fullRender(){
        syncWithPreset();
        renderTotalGap();
        renderSpiritGrid();
        renderBallsGrid();
        renderPresetSpirits();
        renderCapturedList();
        renderUnknownList();
        renderBattlePanel();
        renderAvgStats();
        updatePresetDropdown();
        updateTargetSelector();
        renderTargetHighlight();
        renderSeasonsList();
        updateSeasonFilterSelect();
        populateSeasonDropdown();
        renderDailyStats();
        renderCategoryNotes();
        if(captureSnapshot) document.getElementById("captureStatus").innerHTML=captureStartDate?`✅ 开始于 ${new Date(captureStartDate).toLocaleString()} (已记录增量)`:`✅ 已记录库存`; else document.getElementById("captureStatus").innerHTML=`⚡ 未开始捕捉`;
        if(activeTargetId){ let sp=spirits.find(s=>s.id===activeTargetId); if(sp){ let matchedIds=new Set(ballTypes.filter(b=>isAttributeBall(b) && (sp.attrs || []).some(sa=> [b.attr1, b.attr2].filter(a=>a && a.trim() && a !== "无").includes(sa))).map(b=>b.id)); document.querySelectorAll(".ball-card").forEach(card=>{ let id=parseInt(card.dataset.ballId); if(matchedIds.has(id)) card.classList.add("highlight-ball"); else card.classList.remove("highlight-ball"); }); } else document.querySelectorAll(".ball-card").forEach(c=>c.classList.remove("highlight-ball")); } else document.querySelectorAll(".ball-card").forEach(c=>c.classList.remove("highlight-ball"));
        const badge = document.getElementById("orderLockBadge");
        if (badge) badge.style.display = "none";
        document.querySelectorAll('.group-mode-btn').forEach(btn=>{
            btn.classList.remove('active');
            if(btn.dataset.mode === currentTransferMode) btn.classList.add('active');
        });
        document.querySelectorAll('.group-tab').forEach(tab=>{
            tab.classList.remove('active');
            if(tab.dataset.display === currentDisplayGroup) tab.classList.add('active');
        });
        document.getElementById("unknownCount").innerText = unknownRecords.length;
        initSidebar();
        renderGrowthPlan();
    }

    function bindActions(){
        document.getElementById("startCaptureBtn")?.addEventListener("click",startCapture);
        document.getElementById("addSpiritFromPresetBtn")?.addEventListener("click",()=>{
            let name=document.getElementById("selectPresetSpirit").value;
            if(!name)return;
            let p=presetSpirits.find(pr=>pr.name===name);
            if(!p)return;
            spirits.push({id:nextSpiritId++, name:p.name, attrs:[...p.attrs], requiredCount:settingBallsPerSpirit || 1500, consumptionLogs: [], prismWarning: false, type: p.type});
            persistAll();
            syncWithPreset();
            fullRender();
        });
        document.getElementById("addBallTypeBtn")?.addEventListener("click",()=>{ let name=prompt("球种名"); if(!name)return; let a1=prompt("属性1","草"); if(!a1)a1="草"; let a2=prompt("属性2(可选)",""); let nid=nextBallId++; ballTypes.push({id:nid,name,attr1:a1,attr2:a2||""}); inventory[nid]=0; persistAll(); fullRender(); });
        document.getElementById("addPresetSpiritBtn")?.addEventListener("click",()=>{
            const modal = document.createElement('div'); modal.className = 'modal';

            // ---- 构建赛季选项 ----
            let seasonOptions = `<option value="">-- 选择赛季 --</option>`;
            let sortedSeasons = [...seasons].sort((a, b) => b.order - a.order);
            let latestSeasonId = sortedSeasons.length > 0 ? sortedSeasons[0].id : null;
            sortedSeasons.forEach(s => {
                let selected = (s.id === latestSeasonId) ? 'selected' : '';
                seasonOptions += `<option value="${s.id}" ${selected}>${escapeHtml(s.name)}</option>`;
            });

            // ---- 分类选项（默认只有通用选项） ----
            let categoryOptions = `<option value="">-- 不选择分类 --</option>`;
            categoryOptions += `<option value="__通用__">📜 通行证精灵（通用）</option>`;

            modal.innerHTML = `<div class="modal-content">
                <h3>新增预设精灵</h3>
                <div><label>精灵名称</label><input id="newPresetName" placeholder="请输入精灵名称" style="width:100%;"></div>
                <div><label>属性1</label><select id="newPresetAttr1">${getAllAttributes().map(a => `<option value="${a}">${a}</option>`).join('')}</select></div>
                <div><label>属性2</label><select id="newPresetAttr2"><option value="">无</option>${getAllAttributes().map(a => `<option value="${a}">${a}</option>`).join('')}</select></div>
                <div><label>类型</label>
                    <select id="newPresetType">
                        <option value="normal">🍃 非奇遇精灵</option>
                        <option value="wonder">✨ 奇遇精灵</option>
                    </select>
                </div>
                <div><label>所属赛季</label>
                    <select id="newPresetSeason" style="width:100%;">${seasonOptions}</select>
                </div>
                <div><label>精灵分类</label>
                    <select id="newPresetCategory" style="width:100%;">${categoryOptions}</select>
                </div>
                <div style="font-size:0.7rem; color:#5a7a4a; margin-top:4px;" id="categoryHint">💡 可选择通行证精灵（通用）或赛季专属分类</div>
                <div style="display:flex; gap:8px; margin-top:16px;">
                    <button id="confirmAddPreset" class="primary">添加</button>
                    <button id="cancelAddPreset">取消</button>
                </div>
            </div>`;
            document.body.appendChild(modal);

            // ---- 当赛季变化时，更新分类下拉 ----
            const seasonSelect = modal.querySelector('#newPresetSeason');
            const categorySelect = modal.querySelector('#newPresetCategory');
            const hintDiv = modal.querySelector('#categoryHint');

            function updateCategories(seasonId) {
                let selectedSeason = seasons.find(s => s.id === seasonId);
                // 保留空选项和通用选项
                let options = `<option value="">-- 不选择分类 --</option>`;
                options += `<option value="__通用__">📜 通行证精灵（通用）</option>`;
                if (selectedSeason && selectedSeason.categories && selectedSeason.categories.length > 0) {
                    selectedSeason.categories.forEach(cat => {
                        options += `<option value="${escapeHtml(cat)}">${escapeHtml(cat)}</option>`;
                    });
                    hintDiv.textContent = `💡 可选择通行证精灵（通用）或 "${selectedSeason.name}" 的专属分类`;
                } else if (selectedSeason) {
                    hintDiv.textContent = `💡 当前赛季暂无专属分类，可在赛季管理中先添加分类`;
                } else {
                    hintDiv.textContent = `💡 可选择通行证精灵（通用）或赛季专属分类`;
                }
                categorySelect.innerHTML = options;
            }

            // 初始化分类（根据默认选中的赛季）
            updateCategories(parseInt(seasonSelect.value) || null);

            seasonSelect.addEventListener('change', function() {
                let seasonId = parseInt(this.value) || null;
                updateCategories(seasonId);
            });

            modal.querySelector('#confirmAddPreset').onclick = function() {
                try {
                    let name = modal.querySelector('#newPresetName').value.trim();
                    if (!name) { alert("请输入精灵名称"); return; }
                    let a1 = modal.querySelector('#newPresetAttr1').value;
                    let a2 = modal.querySelector('#newPresetAttr2').value;
                    let attrs = a2 ? [a1, a2] : [a1];
                    let type = modal.querySelector('#newPresetType').value;
                    let seasonId = parseInt(modal.querySelector('#newPresetSeason').value) || null;
                    let category = modal.querySelector('#newPresetCategory').value;

                    // ---- 如果分类为空，则不存储分类字段 ----
                    let categoryToStore = null;
                    if (category === '__通用__') {
                        categoryToStore = '通行证精灵';
                    } else if (category) {
                        categoryToStore = category;
                    }
                    // 如果 category 为空字符串，则 categoryToStore 保持 null

                    presetSpirits.push({
                        id: nextPresetId++,
                        name,
                        attrs,
                        type,
                        defaultSeasonId: seasonId,
                        category: categoryToStore,  // 可能为 null
                        updatedAt: new Date().toISOString()
                    });
                    persistAll();
                    fullRender();
                    modal.remove();
                    let categoryDisplay = categoryToStore || '未分类';
                    alert(`已添加预设精灵 "${name}"，分类：${categoryDisplay}`);
                } catch(e) {
                    alert('添加失败：' + e.message);
                }
            };
            modal.querySelector('#cancelAddPreset').onclick = function() {
                modal.remove();
            };
        });
        document.getElementById("addCapturedRecordBtn")?.addEventListener("click",showAddCapturedRecordDialog);
        document.getElementById("doBattleGetBtn")?.addEventListener("click",battleGet);
        document.getElementById("synthesisInWarehouseBtn")?.addEventListener("click",openSynthesisDialog);
        document.getElementById("confirmTargetBtn")?.addEventListener("click",setActiveTarget);
        document.getElementById("clearTargetBtn")?.addEventListener("click",clearActiveTarget);
        document.getElementById("presetSearchInput")?.addEventListener("input",()=>renderPresetSpirits());
        document.getElementById("globalSetNeedBtn")?.addEventListener("click",globalSetNeed);
        document.getElementById("toggleDeleteModeBtn")?.addEventListener("click",toggleDeleteMode);
        document.getElementById("confirmDeleteSpiritsBtn")?.addEventListener("click",confirmDeleteSpirits);
        document.getElementById("cancelDeleteModeBtn")?.addEventListener("click",cancelDeleteMode);
        document.getElementById("recordDateFilter")?.addEventListener("change",()=>renderBattlePanel());
        document.getElementById("resetDateFilterBtn")?.addEventListener("click",resetDateFilter);
        document.getElementById("historyRecordBtn")?.addEventListener("click",()=>showHistoryConsumptionDialog());
        document.getElementById("addSeasonBtn")?.addEventListener("click",addSeason);
        document.getElementById("seasonFilterSelect")?.addEventListener("change", onSeasonFilterChange);
        document.querySelectorAll('.group-mode-btn').forEach(btn=>{
            btn.addEventListener('click',()=>{
                onTransferModeChange(btn.dataset.mode);
            });
        });
        document.querySelectorAll('.group-tab').forEach(tab=>{
            tab.addEventListener('click',()=>{
                onDisplayGroupChange(tab.dataset.display);
            });
        });

        document.getElementById("settingRoundBalls")?.addEventListener("change", handleSettingChange);
        document.getElementById("settingPeople")?.addEventListener("change", handleSettingChange);
        document.getElementById("settingBallsPerSpirit")?.addEventListener("change", handleSettingChange);
        document.getElementById("settingCurrentSeason")?.addEventListener("change", handleSettingChange);
        document.querySelectorAll('#settingRoundBalls, #settingPeople, #settingBallsPerSpirit, #settingCurrentSeason').forEach(input => {
            input.addEventListener('blur', function() {
                this.dispatchEvent(new Event('change'));
            });
        });

        // ---- 成长计划事件绑定 ----
        document.getElementById("addGrowthSpiritBtn")?.addEventListener("click", showAddGrowthSpiritDialog);
        document.getElementById("growthSaveSettingsBtn")?.addEventListener("click", saveGrowthSettings);
        document.getElementById("growthSaveMaterialsBtn")?.addEventListener("click", saveCurrentMaterials);

        // 新增：快速增减材料按钮
        document.getElementById("growthMaterialsDec3")?.addEventListener("click", function() {
            let input = document.getElementById("growthCurrentMaterials");
            let val = parseInt(input.value) || 0;
            val = Math.max(0, val - 3);
            input.value = val;
            // 自动保存
            growthData.currentMaterials = val;
            saveGrowthData();
            renderGrowthPlan();
        });
        document.getElementById("growthMaterialsInc3")?.addEventListener("click", function() {
            let input = document.getElementById("growthCurrentMaterials");
            let val = parseInt(input.value) || 0;
            val = val + 3;
            input.value = val;
            // 自动保存
            growthData.currentMaterials = val;
            saveGrowthData();
            renderGrowthPlan();
        });
    }

    function escapeHtml(str){ return String(str).replace(/[&<>]/g,function(m){if(m==='&')return '&amp;';if(m==='<')return '&lt;';if(m==='>')return '&gt;';return m;}); }

    // =========================================================================
    // 软件自动更新
    // =========================================================================
    let lastUpdateManifest = null;

    function loadUpdateConfig() {
        const repo = localStorage.getItem('update_github_repo') || '';
        const url = localStorage.getItem('update_manifest_url') || '';
        const repoInp = document.getElementById('updateGithubRepo');
        const urlInp = document.getElementById('updateManifestUrl');
        // DEFAULT_UPDATE_REPO 可能是 owner/repo（走 Releases）或 version.json 直链（仓库内 exe）；
        // 按形态填入对应输入框，用户已保存的配置优先。
        const def = DEFAULT_UPDATE_REPO || '';
        const defIsUrl = /^https?:\/\//i.test(def);
        if (repoInp) repoInp.value = repo || (defIsUrl ? '' : def);
        if (urlInp) urlInp.value = url || (defIsUrl ? def : '');
        const lbl = document.getElementById('currentVersionLabel');
        if (lbl) lbl.textContent = APP_VERSION;
    }

    function saveUpdateConfig() {
        const repo = (document.getElementById('updateGithubRepo') || {}).value || '';
        const url = (document.getElementById('updateManifestUrl') || {}).value || '';
        localStorage.setItem('update_github_repo', repo);
        localStorage.setItem('update_manifest_url', url);
    }

    // =========================================================================
    // 游戏数据同步（预设精灵库 + 赛季）
    // 数据包放在仓库 data/game_data.json，检查软件更新时顺带拉取，避免每个赛季都要重新打包 exe
    // 流程：拉取 → 差异检测（只读，只看新赛季） → 有新赛季才弹窗询问 → 用户同意后只加新赛季地合入本地
    // 注意：老赛季的数据不参与比对也不写入——发布者老赛季的精灵库可能和用户不一样
    // =========================================================================
    const DATA_VERSION_KEY = 'game_data_version';
    let dataSyncInFlight = false;
    let pendingDataPack = null;      // 已拉取、等待用户确认的数据包
    let skippedDataVersion = '';     // 本次运行中用户选择「以后再说」的数据版本（不写入本地，重启会再提示）
    let dataCheckedThisRound = false; // 本轮「检查更新」是否已检查过数据
    let pendingDataCheckSilent = true;

    function getDataPackUrl() {
        return localStorage.getItem('update_data_url') || DEFAULT_DATA_URL || '';
    }

    function loadDataConfig() {
        const verEl = document.getElementById('dataVersionLabel');
        if (verEl) {
            const v = localStorage.getItem(DATA_VERSION_KEY) || '';
            verEl.textContent = v ? String(v).replace('T', ' ').slice(0, 19) : '未同步';
        }
        const urlEl = document.getElementById('dataPackUrlLabel');
        if (urlEl) urlEl.textContent = getDataPackUrl() || '未配置';
        const inp = document.getElementById('updateDataUrl');
        if (inp && document.activeElement !== inp) inp.value = localStorage.getItem('update_data_url') || '';
    }

    // 把界面上填的数据包直链存起来（留空则回落到默认地址）
    function saveDataPackUrl() {
        const inp = document.getElementById('updateDataUrl');
        if (!inp) return;
        const v = (inp.value || '').trim();
        if (v) localStorage.setItem('update_data_url', v);
        else localStorage.removeItem('update_data_url');
    }

    function bindDataSyncButtons() {
        const sb = document.getElementById('syncDataBtn');
        if (sb) sb.onclick = function () { checkGameDataUpdates(false); };
        const eb = document.getElementById('exportDataPackBtn');
        if (eb) eb.onclick = function () { exportDataPack(); };
        const pb = document.getElementById('publishDataPackBtn');
        if (pb) pb.onclick = function () { publishDataPack(); };
        const tk = document.getElementById('publishToken');
        if (tk) {
            tk.value = localStorage.getItem(PUBLISH_TOKEN_KEY) || '';
            tk.addEventListener('change', function () {
                localStorage.setItem(PUBLISH_TOKEN_KEY, tk.value.trim());
            });
            tk.addEventListener('blur', function () {
                localStorage.setItem(PUBLISH_TOKEN_KEY, tk.value.trim());
            });
        }
        const ib = document.getElementById('importDataPackBtn');
        if (ib) ib.onclick = function () {
            if (!pythonAPI) { alert('程序还没就绪，请稍后再试'); return; }
            const st = document.getElementById('dataSyncStatus');
            if (st) st.textContent = '正在读取本地数据包…';
            pythonAPI.importDataPack();
        };
        const tb = document.getElementById('testDataUrlBtn');
        if (tb) tb.onclick = function () {
            if (!pythonAPI) { alert('程序还没就绪，请稍后再试'); return; }
            saveDataPackUrl();
            const st = document.getElementById('dataSyncStatus');
            if (st) st.textContent = '正在逐个测试地址（每个最多 8 秒）…';
            pythonAPI.testDataPackUrls(getDataPackUrl());
        };
        const du = document.getElementById('updateDataUrl');
        if (du) du.addEventListener('change', function () { saveDataPackUrl(); loadDataConfig(); });
        if (du) du.addEventListener('blur', function () { saveDataPackUrl(); loadDataConfig(); });

        applyPublisherMode(isPublisherMode());
        bindPublisherUnlock(document.getElementById('updateCardTitle'));
        bindPublisherUnlock(document.getElementById('gameDataLabel'));
    }

    // ===== 发布者模式（隐藏功能：在标题上连点 5 次显示） =====
    // 普通用户用不到「导出数据包 / 上传到 GitHub」，藏起来避免误点，也让界面干净。
    const PUBLISHER_KEY = 'publisher_mode';
    const PUBLISH_TOKEN_KEY = 'gh_publish_token';
    let pendingPublishPack = null;
    let lastPendingPublishPack = null;   // 等待远端对比结果、即将弹确认窗的数据包
    let lastPendingNoSeason = 0;

    function isPublisherMode() { return localStorage.getItem(PUBLISHER_KEY) === '1'; }

    function applyPublisherMode(on) {
        localStorage.setItem(PUBLISHER_KEY, on ? '1' : '0');
        const panel = document.getElementById('publisherPanel');
        if (panel) panel.style.display = on ? 'block' : 'none';
        const badge = document.getElementById('publisherBadge');
        if (badge) badge.style.display = on ? 'inline-block' : 'none';
    }

    function bindPublisherUnlock(el) {
        if (!el || el.dataset.pubBound === '1') return;
        el.dataset.pubBound = '1';
        let count = 0, last = 0;
        el.addEventListener('click', function () {
            const now = Date.now();
            if (now - last > 1200) count = 0;   // 间隔超过 1.2 秒重新计数
            last = now;
            count++;
            if (count < 5) return;
            count = 0;
            const on = !isPublisherMode();
            applyPublisherMode(on);
            const st = document.getElementById('publishStatus');
            if (st) st.textContent = on ? '已显示发布者工具' : '';
            if (!on) {
                const s2 = document.getElementById('dataSyncStatus');
                if (s2) s2.textContent = '已隐藏发布者工具';
            }
        });
    }

    // 上传前先做本地检查，再拉远端做覆盖对比，最后弹窗确认——上传是整文件覆盖，
    // 不是追加：远端有、本地没有的内容会被删掉，所以要先让发布者看清楚再确认
    function publishDataPack() {
        if (!pythonAPI) { alert('程序还没就绪，请稍后再试'); return; }
        const tokenEl = document.getElementById('publishToken');
        const token = (tokenEl ? tokenEl.value : (localStorage.getItem(PUBLISH_TOKEN_KEY) || '')).trim();
        const st = document.getElementById('publishStatus');
        if (!token) {
            if (st) st.textContent = '请先填写 GitHub Token';
            if (tokenEl) tokenEl.focus();
            return;
        }
        localStorage.setItem(PUBLISH_TOKEN_KEY, token);

        const pack = buildDataPack();
        if (!pack.seasons.length) {
            if (st) st.textContent = '本地没有赛季，已取消上传';
            alert('你本地还没有任何赛季，用户端收不到内容。\n请先在「赛季管理」新增赛季，并把精灵挂到该赛季下再上传。');
            return;
        }
        const noSeason = pack.spirits.filter(p => !p.season).length;
        // 拉取远端当前数据包，给确认弹窗做「覆盖对比」展示（拉不到也允许继续，只做提示）
        lastPendingPublishPack = pack;
        lastPendingNoSeason = noSeason;
        const repo = ((document.getElementById('updateGithubRepo') || {}).value || '').trim()
                     || 'H-ZHOWEI/iseki-arrest';
        if (st) st.textContent = '正在获取远端当前数据包做对比…';
        try {
            pythonAPI.previewRemotePack(repo, 'data/game_data.json', 'main');
        } catch (e) {
            showPublishConfirm(pack, noSeason, null);
        }
    }

    function showPublishConfirm(pack, noSeason, remotePack) {
        const old = document.getElementById('publishConfirmModal');
        if (old) old.remove();
        // 算出「远端有、本地没有」的内容：上传是覆盖，这些会从远端消失
        let remoteInfo = '', removeInfo = '';
        if (remotePack && Array.isArray(remotePack.seasons) && Array.isArray(remotePack.spirits)) {
            const localSeasons = new Set(pack.seasons.map(s => s.name));
            const localSpirits = new Set(pack.spirits.map(p => p.name));
            const goneSeasons = remotePack.seasons.filter(s => !localSeasons.has(s.name)).map(s => s.name);
            const goneSpirits = remotePack.spirits.filter(p => !localSpirits.has(p.name)).map(p => p.name);
            remoteInfo = '<p style="font-size:0.75rem; color:#5a7a4a; line-height:1.5; margin:6px 0 0;">'
                + '远端当前：<b>' + remotePack.seasons.length + '</b> 个赛季、<b>'
                + remotePack.spirits.length + '</b> 只精灵。</p>';
            if (goneSpirits.length || goneSeasons.length) {
                const names = goneSpirits.slice(0, 8).map(n => '「' + n + '」').join('')
                    + (goneSpirits.length > 8 ? ' 等 ' + goneSpirits.length + ' 只' : '');
                const sn = goneSeasons.slice(0, 4).map(n => '「' + n + '」').join('')
                    + (goneSeasons.length > 4 ? ' 等 ' + goneSeasons.length + ' 个' : '');
                removeInfo = '<p style="font-size:0.75rem; color:#a8322f; background:#fdf0ee;'
                    + ' border:1px solid #f0d2c4; border-radius:10px; padding:8px 10px; line-height:1.5;">'
                    + '警告：以下内容<b>远端有、本地没有</b>，上传后将从远端删除：<br>'
                    + (goneSpirits.length ? '精灵：' + names + '<br>' : '')
                    + (goneSeasons.length ? '赛季：' + sn : '')
                    + '</p>';
            } else {
                removeInfo = '<p style="font-size:0.75rem; color:#5a7a4a; line-height:1.5;">'
                    + '本地已包含远端全部内容，覆盖后不会丢失任何精灵。</p>';
            }
        } else {
            remoteInfo = '<p style="font-size:0.75rem; color:#a8622f; line-height:1.5;">'
                + '未能获取远端当前数据（网络原因），本次将直接覆盖，请先确认本地数据完整。</p>';
        }
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.id = 'publishConfirmModal';
        modal.innerHTML = '<div class="modal-content" style="max-width:480px;">'
            + '<h3 style="margin-top:0;">上传数据包到 GitHub</h3>'
            + '<p style="font-size:0.78rem; color:#5a7a4a; line-height:1.6;">'
            + '本次数据包：<b>' + pack.seasons.length + '</b> 个赛季、<b>' + pack.spirits.length + '</b> 只精灵。<br>'
            + '上传方式：<b>覆盖</b> —— 远端 <b>data/game_data.json</b>（分支 main）会被本地数据完整替换，不是追加。</p>'
            + remoteInfo + removeInfo
            + (noSeason
                ? '<p style="font-size:0.75rem; color:#a8622f; background:#fdf4ea; border:1px solid #f0dcc4;'
                  + ' border-radius:10px; padding:8px 10px; line-height:1.5;">'
                  + '注意：其中 <b>' + noSeason + '</b> 只精灵没有设置所属赛季，'
                  + '这些精灵<b>不会推送给用户</b>。</p>'
                : '')
            + '<p style="font-size:0.75rem; color:#5a7a4a; line-height:1.5;">'
            + '用户端只会收到<b>新赛季</b>及其中的精灵；老赛季的改动不会推送给普通用户。</p>'
            + '<div style="display:flex; gap:8px; margin-top:14px;">'
            + '<button id="confirmPublishBtn" class="primary">确认覆盖上传</button>'
            + '<button id="cancelPublishBtn" style="background:#ffffff; border:1.5px solid #cfe0bf;'
            + ' color:#2b6e2f; border-radius:14px; padding:8px 16px; cursor:pointer; font-weight:600;">取消</button>'
            + '</div></div>';
        document.body.appendChild(modal);
        modal.querySelector('#cancelPublishBtn').onclick = function () { modal.remove(); };
        modal.querySelector('#confirmPublishBtn').onclick = function () {
            modal.remove();
            doPublish(pack);
        };
    }

    // 拉远端数据包的回调：拿到就带对比展示，拿不到也允许继续（弹窗里只做提示）
    function onRemotePackPreview(res) {
        const st = document.getElementById('publishStatus');
        if (st) st.textContent = '';
        showPublishConfirm(lastPendingPublishPack, lastPendingNoSeason,
            (res && res.status === 'ok' && res.pack) ? res.pack : null);
    }

    function doPublish(pack) {
        const st = document.getElementById('publishStatus');
        const token = (localStorage.getItem(PUBLISH_TOKEN_KEY) || '').trim();
        const repo = ((document.getElementById('updateGithubRepo') || {}).value || '').trim()
                     || 'H-ZHOWEI/iseki-arrest';
        pendingPublishPack = pack;
        if (st) st.textContent = '正在上传…';
        try {
            pythonAPI.publishDataPack(JSON.stringify(pack), token, repo, 'data/game_data.json', 'main');
        } catch (e) {
            if (st) st.textContent = '上传失败：' + e;
        }
    }

    function onDataPackPublished(res) {
        const st = document.getElementById('publishStatus');
        const pack = pendingPublishPack;
        pendingPublishPack = null;
        if (!res || res.status === 'error') {
            if (st) st.textContent = '上传失败：' + ((res && res.message) || '未知错误');
            return;
        }
        // 已发布的版本号落到本地，避免本机再次提示「有新赛季」
        if (pack && pack.data_version) localStorage.setItem(DATA_VERSION_KEY, String(pack.data_version));
        loadDataConfig();
        if (st) {
            st.textContent = '已上传（commit ' + (res.commit || '?') + '，'
                + (res.bytes || 0) + ' 字节' + (res.created ? '，新建文件' : '') + '）';
        }
    }

    // 检查数据包是否有新增赛季 / 精灵（只拉取，不改动任何本地数据）
    function checkGameDataUpdates(silent) {
        if (dataSyncInFlight) return;
        saveDataPackUrl();
        const url = getDataPackUrl();
        const st = document.getElementById('dataSyncStatus');
        if (!url) {
            if (st) st.textContent = '未配置数据包地址';
            return;
        }
        if (!pythonAPI) {
            if (st) st.textContent = '正在等待程序就绪…';
            return;
        }
        if (st) st.textContent = '正在检查数据更新…（网络慢时会自动换镜像）';
        dataSyncInFlight = true;
        pythonAPI.syncGameData(url);
    }

    // 兼容旧按钮/旧调用
    function syncGameData(silent) { checkGameDataUpdates(!!silent); }

    // 地址自检结果：逐条列出现在哪些地址能拉到数据包，点「用这个」直接写进「数据包直链」
    function closeDataUrlTestModal() {
        const old = document.getElementById('dataUrlTestModal');
        if (old) old.remove();
    }

    function onDataUrlTested(res) {
        closeDataUrlTestModal();
        const results = (res && res.results) || [];
        const okList = results.filter(function (r) { return r.ok; });
        const st = document.getElementById('dataSyncStatus');
        if (st) {
            st.textContent = okList.length
                ? ('可用 ' + okList.length + ' / ' + results.length + ' 条地址，点「用这个」可切换')
                : '所有地址都不可用，请改用「从文件导入数据包」';
        }

        const rows = results.map(function (r) {
            const m = String(r.url || '').match(/^https?:\/\/([^/]+)/);
            const host = m ? m[1] : String(r.url || '').slice(0, 30);
            const color = r.ok ? '#2b6e2f' : '#c23d2b';
            const stateTxt = r.ok ? ('可用 · ' + r.ms + 'ms') : (r.msg || '失败');
            const btn = r.ok
                ? '<button class="small" data-url="' + escapeHtml(r.url) + '" style="flex:0 0 auto;">用这个</button>'
                : '';
            return '<div style="display:flex; align-items:center; gap:8px; padding:6px 0;'
                + ' border-bottom:1px dashed #e6efda;">'
                + '<div style="flex:1; min-width:0;">'
                + '<div style="font-size:0.76rem; color:#2f4a24; word-break:break-all;">' + escapeHtml(host) + '</div>'
                + '<div style="font-size:0.7rem; color:' + color + ';">' + escapeHtml(stateTxt) + '</div>'
                + '</div>' + btn + '</div>';
        }).join('');

        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.id = 'dataUrlTestModal';
        modal.innerHTML = '<div class="modal-content" style="max-width:520px;">'
            + '<h3 style="margin-top:0;">数据包地址自检</h3>'
            + '<p style="font-size:0.74rem; color:#5a7a4a; margin-top:0;">'
            + '逐个尝试主地址与备用镜像，绿色表示当前网络能拉到。选一条可用的设为「数据包直链」即可。</p>'
            + '<div style="max-height:280px; overflow:auto;">' + (rows || '<p>没有可测试的地址</p>') + '</div>'
            + '<div style="display:flex; justify-content:flex-end; margin-top:12px;">'
            + '<button id="closeTestModalBtn" style="background:#ffffff; border:1.5px solid #cfe0bf;'
            + ' color:#2b6e2f; border-radius:14px; padding:8px 16px; cursor:pointer; font-weight:600;">关闭</button>'
            + '</div></div>';
        document.body.appendChild(modal);
        modal.querySelector('#closeTestModalBtn').onclick = closeDataUrlTestModal;

        modal.querySelectorAll('button[data-url]').forEach(function (b) {
            b.onclick = function () {
                const u = b.getAttribute('data-url');
                const inp = document.getElementById('updateDataUrl');
                if (u === DEFAULT_DATA_URL) localStorage.removeItem('update_data_url');
                else localStorage.setItem('update_data_url', u);
                if (inp) inp.value = (u === DEFAULT_DATA_URL) ? '' : u;
                loadDataConfig();
                closeDataUrlTestModal();
                const s2 = document.getElementById('dataSyncStatus');
                if (s2) s2.textContent = '已切换数据包地址，点「检查数据更新」试试';
            };
        });
    }

    // 差异检测：纯只读。
    // 普通模式：只比对「本地没有的新赛季」以及这些新赛季里的异色精灵；
    //   已有赛季的数据完全不参与比对——发布者老赛季的精灵库可能和用户不一样，
    //   拿老赛季做比对会把差异当成「新增」塞给用户，所以直接不看。
    // 发布者模式（isPublisherMode）：与数据包全量比对，老赛季里本地缺失的精灵
    //   也列为「补回」（restore: true），方便发布者误删后从数据包恢复。
    // 按赛季起止日期判断「当前赛季」：今天落在哪个区间就是哪个；
    // 没有区间覆盖今天时，取「已开始」里开始日期最晚的；都没有日期则按 order 最大的算。
    function getCurrentSeasonInfo() {
        if (!seasons || !seasons.length) return { name: '', season: null };
        const today = new Date(); today.setHours(0, 0, 0, 0);
        function parseDate(s) {
            if (!s) return null;
            const d = new Date(String(s).trim().replace(/-/g, '/'));
            return isNaN(d.getTime()) ? null : d;
        }
        let active = null;
        seasons.forEach(function (s) {
            if (!s || !s.name) return;
            const st = parseDate(s.startDate), ed = parseDate(s.endDate);
            if (st && ed && today >= st && today <= ed) active = s;
        });
        if (active) return { name: String(active.name).trim(), season: active };
        let best = null, bestT = -Infinity;
        seasons.forEach(function (s) {
            if (!s || !s.name) return;
            const st = parseDate(s.startDate);
            if (st && st <= today && st.getTime() >= bestT) { bestT = st.getTime(); best = s; }
        });
        if (best) return { name: String(best.name).trim(), season: best };
        let last = null;
        seasons.forEach(function (s) { if (s && s.name && (!last || (s.order || 0) >= (last.order || 0))) last = s; });
        return last ? { name: String(last.name).trim(), season: last } : { name: '', season: null };
    }

    function getCurrentSeasonName() { return getCurrentSeasonInfo().name; }

    // 赛季是否已经结束（有合法结束日期且早于今天）——已结束的赛季不参与推送
    function isSeasonEnded(endDate) {
        if (!endDate) return false;
        const d = new Date(String(endDate).trim().replace(/-/g, '/'));
        if (isNaN(d.getTime())) return false;
        d.setHours(23, 59, 59, 999);
        return d.getTime() < Date.now();
    }

    function diffGameData(pack) {
        const pub = isPublisherMode();
        const curSeasonName = getCurrentSeasonName();   // 当前赛季（按赛季起止日期判断）
        const knownSeasons = {};
        const knownSpirits = {};
        seasons.forEach(s => { if (s && s.name) knownSeasons[String(s.name).trim()] = true; });
        presetSpirits.forEach(p => { if (p && p.name) knownSpirits[String(p.name).trim()] = true; });

        const res = { seasons: [], spirits: [], skipped: 0, pastSeasons: 0, pastSeasonNames: [] };

        const newSeasonNames = {};
        (pack.seasons || []).forEach(rs => {
            const name = String((rs && rs.name) || '').trim();
            if (!name || knownSeasons[name]) return;
            // 已结束的赛季不再当作「新赛季」：过往赛季的精灵不推给用户
            if (isSeasonEnded(rs.endDate)) {
                res.pastSeasons++;
                res.pastSeasonNames.push(name);
                return;
            }
            knownSeasons[name] = true;      // 远端包内同名只算一次
            newSeasonNames[name] = true;
            res.seasons.push({
                name: name,
                startDate: rs.startDate || '',
                endDate: rs.endDate || '',
                order: rs.order
            });
        });

        (pack.spirits || []).forEach(rp => {
            const name = String((rp && rp.name) || '').trim();
            if (!name) return;
            const sName = rp.season ? String(rp.season).trim() : '';
            if (newSeasonNames[sName]) {
                // 新赛季里的精灵：本地没有 → 新增
                if (knownSpirits[name]) return;     // 本地已有同名精灵，不覆盖、不重复加
                knownSpirits[name] = true;
                res.spirits.push({ name: name, season: sName, type: rp.type || 'normal', restore: false });
                return;
            }
            if (pub) {
                // 发布者模式：只允许补回「当前赛季」里本地缺失的精灵；
                // 过往赛季一律不比、不导入（早前全量比对会把 S3/S4 的老精灵一起列出来，属于误推）
                if (knownSpirits[name]) return;
                if (!curSeasonName || sName !== curSeasonName) { res.skipped++; return; }
                knownSpirits[name] = true;
                res.spirits.push({ name: name, season: sName, type: rp.type || 'normal', restore: true });
                return;
            }
            if (knownSpirits[name]) return;     // 本地已有同名精灵，无需处理
            res.skipped++;      // 普通模式：老赛季 / 未写赛季的精灵一律跳过
        });
        return res;
    }

    function onGameDataFetched(res) {
        dataSyncInFlight = false;
        const st = document.getElementById('dataSyncStatus');
        if (!res || res.status === 'error') {
            let msg = (res && res.message) ? res.message : '未知错误';
            if (msg.indexOf('数据同步失败') !== 0) msg = '数据同步失败：' + msg;
            if (st) {
                st.textContent = msg + '（可点「检查数据更新」重试，或点「从文件导入数据包」）';
                st.title = msg;
            }
            return;
        }
        const pack = res.pack || {};
        const remoteVer = String(pack.data_version || '');
        const localVer = localStorage.getItem(DATA_VERSION_KEY) || '';
        const verShow = remoteVer ? String(remoteVer).replace('T', ' ').slice(0, 10) : '';
        const fromFile = String(res.source || '').indexOf('file:') === 0;
        const viaMirror = !fromFile && !!res.source && res.source !== getDataPackUrl();

        if (remoteVer && remoteVer === skippedDataVersion) {
            if (st) st.textContent = '已跳过本次数据更新（下次启动会再提示）';
            return;
        }

        const diff = diffGameData(pack);
        const totalNew = diff.seasons.length + diff.spirits.length;
        if (!totalNew) {
            if (remoteVer) localStorage.setItem(DATA_VERSION_KEY, remoteVer);
            loadDataConfig();
            if (st) {
                st.textContent = ((remoteVer && remoteVer !== localVer)
                    ? (isPublisherMode()
                        ? '数据已是最新（当前赛季无缺失项，过往赛季不参与比对）'
                        : '数据已是最新（没有新赛季）')
                    : '数据已是最新')
                    + (fromFile ? '（来自本地文件）'
                        : (viaMirror ? '｜本次走镜像地址，若刚发布建议稍后再检查' : ''));
            }
            return;
        }

        // 有新增：只记录待确认，暂不写入本地
        pendingDataPack = pack;
        const restoreCount = diff.spirits.filter(p => p.restore).length;
        if (st) {
            st.textContent = '发现新赛季 ' + diff.seasons.length + ' 个、异色精灵 '
                + (diff.spirits.length - restoreCount) + ' 个'
                + (restoreCount ? '（含可补回的缺失精灵 ' + restoreCount + ' 个）' : '')
                + '，等待你确认…'
                + (fromFile ? '（来自本地文件）' : (viaMirror ? '（经镜像获取）' : ''));
        }
        showDataSyncDialog(diff, verShow);
    }

    function showDataSyncDialog(diff, verShow) {
        closeDataSyncDialog();
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.id = 'dataSyncModal';

        function chip(text, note) {
            return '<span style="display:inline-block; background:#f1f6ea; border:1px solid #d9e6c9;'
                + ' border-radius:12px; padding:4px 9px; margin:3px 4px 3px 0; font-size:0.74rem;'
                + ' color:#2f4a24;">' + escapeHtml(text)
                + (note ? '<em style="display:block; font-style:normal; color:#7d9870; font-size:0.66rem;">'
                    + escapeHtml(note) + '</em>' : '')
                + '</span>';
        }

        const seasonHtml = diff.seasons.length
            ? '<div style="margin-top:10px;">'
              + '<div style="font-size:0.78rem; color:#2b6e2f; font-weight:600; margin-bottom:4px;">新增赛季 '
              + diff.seasons.length + ' 个</div>'
              + diff.seasons.map(s => chip(s.name,
                    (s.startDate || s.endDate) ? ((s.startDate || '?') + ' ~ ' + (s.endDate || '?')) : '')).join('')
              + '</div>'
            : '';
        const hasRestore = diff.spirits.some(p => p.restore);
        const spiritHtml = diff.spirits.length
            ? '<div style="margin-top:10px;">'
              + '<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">'
              + '<div style="font-size:0.78rem; color:#2b6e2f; font-weight:600;">异色精灵 '
              + diff.spirits.length + ' 个<span style="font-weight:400; color:#7d9870;">（勾选才会添加）</span></div>'
              + '<a href="javascript:void(0)" id="toggleAllSpiritsLink" style="font-size:0.7rem; color:#4a7a3a;">全不选</a>'
              + '</div>'
              + diff.spirits.map(p =>
                    '<label style="display:flex; align-items:center; gap:7px; padding:3px 2px;'
                    + ' font-size:0.78rem; color:#2f4a24; cursor:pointer;">'
                    + '<input type="checkbox" checked data-spirit="' + escapeHtml(p.name) + '">'
                    + '<span>' + escapeHtml(p.name)
                    + (p.season ? '<em style="font-style:normal; color:#7d9870; font-size:0.68rem;">　'
                        + escapeHtml(p.season) + '</em>' : '')
                    + (p.restore
                        ? '<span style="display:inline-block; background:#fff4e0; border:1px solid #eccf9e;'
                          + ' color:#a06a12; border-radius:10px; padding:0 7px; font-size:0.66rem; margin-left:6px;">补回</span>'
                        : '')
                    + '</span></label>').join('')
              + '</div>'
            : '';

        const curInfo = getCurrentSeasonInfo();
        const curSeasonLine = curInfo.name
            ? ('当前赛季：<b>' + escapeHtml(curInfo.name) + '</b>'
               + ((curInfo.season && (curInfo.season.startDate || curInfo.season.endDate))
                    ? '（' + escapeHtml(curInfo.season.startDate || '?') + ' ~ '
                      + escapeHtml(curInfo.season.endDate || '?') + '）'
                    : '')
               + '<br>')
            : '';
        modal.innerHTML = '<div class="modal-content" style="max-width:480px;">'
            + '<h3 style="margin-top:0;">发现新赛季数据</h3>'
            + '<p style="font-size:0.76rem; color:#5a7a4a; line-height:1.5;">'
            + (verShow ? '数据版本：' + escapeHtml(verShow) + '<br>' : '')
            + curSeasonLine
            + (hasRestore
                ? '当前处于<b>发布者模式</b>：除新赛季外，还会补回<b>当前赛季</b>里你本地缺失的精灵'
                  + '（带「补回」标记）；<b>过往赛季一律不比对、不导入</b>。'
                : '只会把下面这些<b>新赛季</b>和它们里面的异色精灵加进来；'
                  + '<b>已有赛季不参与比对</b>，你原有的赛季、精灵和抓取记录不会被改动。')
            + '</p>'
            + '<div style="max-height:250px; overflow:auto; background:#f6faef; border:1px solid #e6efda; border-radius:14px; padding:8px 10px;">'
            + seasonHtml + spiritHtml + '</div>'
            + (diff.skipped
                ? '<div style="margin-top:8px; font-size:0.7rem; color:#8a9a80; line-height:1.4;">'
                  + '另有 ' + diff.skipped + ' 个精灵属于已有赛季或已结束赛季，本次<b>不比对、不导入</b>。</div>'
                : '')
            + (diff.pastSeasons
                ? '<div style="margin-top:6px; font-size:0.7rem; color:#8a9a80; line-height:1.4;">'
                  + '数据包里另有 ' + diff.pastSeasons + ' 个赛季<b>已结束</b>（'
                  + escapeHtml(diff.pastSeasonNames.slice(0, 4).join('、'))
                  + (diff.pastSeasonNames.length > 4 ? ' 等' : '')
                  + '），过往赛季不推送。</div>'
                : '')
            + '<div style="display:flex; gap:8px; margin-top:14px;">'
            + '<button id="applyDataBtn" class="primary">更新到本地</button>'
            + '<button id="skipDataBtn" style="background:#ffffff; border:1.5px solid #cfe0bf;'
            + ' color:#2b6e2f; border-radius:14px; padding:8px 16px; cursor:pointer; font-weight:600;">以后再说</button>'
            + '</div></div>';
        document.body.appendChild(modal);

        // 勾选联动：按钮文字实时显示将写入的条目数；全不选/全选切换
        const applyBtn = modal.querySelector('#applyDataBtn');
        const spiritBoxes = modal.querySelectorAll('input[data-spirit]');
        function refreshApplyLabel() {
            let n = diff.seasons.length;
            spiritBoxes.forEach(cb => { if (cb.checked) n++; });
            applyBtn.textContent = n ? ('更新到本地（' + n + ' 项）') : '标记已读，不添加';
        }
        spiritBoxes.forEach(cb => { cb.addEventListener('change', refreshApplyLabel); });
        const toggleLink = modal.querySelector('#toggleAllSpiritsLink');
        if (toggleLink) toggleLink.onclick = function () {
            const allChecked = Array.from(spiritBoxes).every(cb => cb.checked);
            spiritBoxes.forEach(cb => { cb.checked = !allChecked; });
            toggleLink.textContent = allChecked ? '全选' : '全不选';
            refreshApplyLabel();
        };
        refreshApplyLabel();

        modal.querySelector('#applyDataBtn').onclick = function () { applyGameData(); };
        modal.querySelector('#skipDataBtn').onclick = function () {
            const remoteVer = pendingDataPack ? String(pendingDataPack.data_version || '') : '';
            skippedDataVersion = remoteVer;
            pendingDataPack = null;
            closeDataSyncDialog();
            const st = document.getElementById('dataSyncStatus');
            if (st) st.textContent = '已跳过本次数据更新（下次启动会再提示）';
        };
    }

    function closeDataSyncDialog() {
        const old = document.getElementById('dataSyncModal');
        if (old) old.remove();
    }

    // 用户确认后才真正写入本地。弹窗里取消勾选的精灵不会添加；
    // 全部取消时仅标记「已读」，下次检查不会再提示这一批。
    function applyGameData() {
        if (!pendingDataPack) { closeDataSyncDialog(); return; }
        const pack = pendingDataPack;
        const remoteVer = String(pack.data_version || '');
        const modal = document.getElementById('dataSyncModal');
        const selected = modal
            ? Array.from(modal.querySelectorAll('input[data-spirit]:checked'))
                .map(cb => cb.getAttribute('data-spirit'))
            : null;                     // 无弹窗时视为全选
        const added = mergeGameData(pack, selected, isPublisherMode());
        if (remoteVer) localStorage.setItem(DATA_VERSION_KEY, remoteVer);
        pendingDataPack = null;
        persistAll();
        refreshIdSequences();
        populateSeasonDropdown();
        fullRender();
        loadDataConfig();
        closeDataSyncDialog();
        const st = document.getElementById('dataSyncStatus');
        if (st) {
            st.textContent = (added.seasons || added.spirits)
                ? '已更新：新增 ' + added.seasons + ' 个赛季、' + added.spirits
                  + ' 个异色精灵（原有数据未改动）'
                : '未添加任何内容（已标记本批数据为已读，下次检查不会再提示）';
        }
    }

    // 合并规则：只增不删、绝不覆盖已有条目
    // - 赛季：本地没有 → 新增；已存在 → 完全不碰（不补日期、不改顺序，发布者与用户的老赛季数据可能不同）
    // - 精灵：
    //    普通模式（allowRestore=false）：只处理「本次新加进来的赛季」里的精灵
    //    发布者模式（allowRestore=true）：额外可补回「当前赛季」里本地缺失的精灵；过往赛季一律不碰
    //  - selectedNames：弹窗勾选的精灵名单；不在名单里的（被用户取消勾选）一律不添加
    function mergeGameData(pack, selectedNames, allowRestore) {
        const added = { spirits: 0, seasons: 0, filled: 0 };
        const selected = selectedNames ? new Set(selectedNames) : null;
        const seasonByName = {};
        seasons.forEach(s => { if (s && s.name) seasonByName[String(s.name).trim()] = s; });

        const newSeasonNames = {};
        (pack.seasons || []).forEach(rs => {
            const name = String((rs && rs.name) || '').trim();
            if (!name || seasonByName[name]) return;
            if (isSeasonEnded(rs.endDate)) return;   // 已结束的赛季不导入（与 diff 保持一致）
            const ns = {
                id: nextSeasonId++, name: name,
                order: (rs.order === undefined || rs.order === null) ? 0 : rs.order,
                startDate: rs.startDate || '', endDate: rs.endDate || '',
                categories: [], categoryNotes: {}
            };
            seasons.push(ns);
            seasonByName[name] = ns;
            newSeasonNames[name] = true;
            added.seasons++;
        });

        const presetByName = {};
        presetSpirits.forEach(p => { if (p && p.name) presetByName[String(p.name).trim()] = p; });
        const curSeasonName = getCurrentSeasonName();   // 发布者补回只允许当前赛季

        (pack.spirits || []).forEach(rp => {
            const name = String((rp && rp.name) || '').trim();
            if (!name) return;
            if (selected && !selected.has(name)) return;    // 用户取消勾选，不添加
            const sName = rp.season ? String(rp.season).trim() : '';
            const seasonObj = sName ? seasonByName[sName] : null;
            const eligible = allowRestore
                ? (!!newSeasonNames[sName] || (!!sName && sName === curSeasonName))  // 补回：新赛季 or 当前赛季
                : !!newSeasonNames[sName];                  // 普通：仅限本次新加的赛季
            if (!eligible) return;
            if (presetByName[name]) return;         // 本地已有同名精灵，保持原样
            const np = {
                id: nextPresetId++, name: name,
                attrs: Array.isArray(rp.attrs) ? rp.attrs.slice() : [],
                type: rp.type || 'normal',
                defaultSeasonId: seasonObj ? seasonObj.id : null,
                updatedAt: new Date(0).toISOString()
            };
            presetSpirits.push(np);
            presetByName[name] = np;
            added.spirits++;
        });
        return added;
    }

    // 把本地当前的赛季 + 预设精灵库导出成数据包（给发布者用）
    function buildDataPack() {
        const seasonNameById = {};
        seasons.forEach(s => { seasonNameById[s.id] = s.name; });
        return {
            data_version: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            app: '异色逮捕计划',
            schema: 1,
            note: '预设精灵库与赛季数据。由软件「设置 → 软件更新 → 导出数据包」生成，覆盖仓库 data/game_data.json 即可发布。',
            seasons: seasons.map(s => ({
                name: s.name,
                order: s.order || 0,
                startDate: s.startDate || '',
                endDate: s.endDate || ''
            })),
            spirits: presetSpirits.map(p => ({
                name: p.name,
                attrs: p.attrs || [],
                type: p.type || 'normal',
                season: (p.defaultSeasonId !== null && p.defaultSeasonId !== undefined)
                    ? (seasonNameById[p.defaultSeasonId] || null) : null
            }))
        };
    }

    function exportDataPack() {
        const pack = buildDataPack();
        const st = document.getElementById('dataSyncStatus');
        if (st) st.textContent = '已生成数据包：' + pack.spirits.length + ' 个精灵、' + pack.seasons.length + ' 个赛季';
        if (pythonAPI) pythonAPI.exportDataPack(JSON.stringify(pack, null, 2));
    }


    function doCheckUpdate(silent) {
        const repo = (document.getElementById('updateGithubRepo') || {}).value || '';
        const url = (document.getElementById('updateManifestUrl') || {}).value || '';
        saveUpdateConfig();
        // 顺序：先检测软件版本，版本检查结束后再检测赛季 / 精灵是否有新增（见 afterVersionCheck）
        pendingDataCheckSilent = !!silent;
        dataCheckedThisRound = false;
        const status = document.getElementById('updateStatus');
        if (!repo && !url) {
            if (status) status.textContent = '未填写更新地址，仅检查游戏数据…';
            if (!silent) alert('请先在「软件更新」填写 GitHub 仓库（格式 owner/repo）');
            afterVersionCheck();
            return;
        }
        if (status) status.textContent = '正在检查版本…';
        // 发布形态是仓库内 exe + version.json，清单直链优先。
        // 旧版把「GitHub 仓库」框排在第一位，1.3.0/1.3.1 存下的 owner/repo 会一直残留，
        // 导致检查更新改走 Releases（本仓库没有 Release）→ 误报「已是最新版本」。
        const source = url.trim() || repo.trim();
        if (pythonAPI) pythonAPI.checkUpdate(source);
        else afterVersionCheck();
    }

    // 版本检查结束（无论有没有新版本）→ 再检查数据包新增
    function afterVersionCheck() {
        if (dataCheckedThisRound) return;
        dataCheckedThisRound = true;
        checkGameDataUpdates(pendingDataCheckSilent);
    }

    function onUpdateChecked(result) {
        const status = document.getElementById('updateStatus');
        const setStatus = function (txt, color, title) {
            if (!status) return;
            status.textContent = txt;
            status.style.color = color || '#5a7a4a';
            if (title) status.title = title;
        };
        if (result && result.status === 'stale') {
            // 线上版本比本机还旧 → 一定是读错了地址或命中旧缓存，不能淡定地说「已是最新」
            setStatus('⚠️ ' + (result.message || '读到的线上版本比本机旧'), '#a8622f',
                      '线上 V' + (result.latest || '?') + ' · 本机 V' + APP_VERSION);
            afterVersionCheck();
            return;
        }
        if (result && result.status === 'error') {
            setStatus('检查失败：' + (result.message || ''), '#c23d2b');
            afterVersionCheck();
            return;
        }
        if (!result || result.status === 'noupdate') {
            const cur = (result && result.current) || APP_VERSION;
            const online = (result && result.latest) || '';
            const src = (result && result.source) || '';
            let txt = '已是最新版本 V' + cur;
            // 把「线上读到几版、从哪条线路读的」摆出来，避免再出现「明明有 1.3.10 却说已是最新」的糊涂账
            if (online) txt += '（线上 V' + online + (src ? ' · 来源 ' + src : '') + '）';
            if (result && result.message) txt += ' · ' + result.message;
            setStatus(txt, '#5a7a4a', txt);
            afterVersionCheck();
            return;
        }
        if (result.status === 'update') {
            setStatus('发现新版本 V' + result.latest + (result.source ? '（来源 ' + result.source + '）' : ''));
            lastUpdateManifest = result;
            showUpdateDialog(result);
        }
    }

    // 更新任务在同一时刻只能有一个：重复点「立即更新」会并发下载、进度条来回跳、
    // 甚至多个替换脚本同时改 exe。这里前端先锁，Python 端 startUpdate 也有一把锁兜底。
    let updateInFlight = false;
    let lastUpdatePct = 0;

    function setUpdateHint(text, color) {
        const el = document.getElementById('updateHint');
        if (el) { el.textContent = text; el.style.color = color || '#7d9870'; }
    }

    function showUpdateDialog(m) {
        const modal = document.createElement('div'); modal.className = 'modal';
        modal.id = 'updateModal';
        const notes = (m.notes || '').replace(/\n/g, '<br>');
        modal.innerHTML = `<div class="modal-content" style="max-width:440px;">
            <h3>发现新版本 V${escapeHtml(m.latest)}</h3>
            <p style="font-size:0.8rem; color:#5a7a4a;">当前版本：V${escapeHtml(m.current || APP_VERSION)}</p>
            <div style="font-size:0.8rem; max-height:180px; overflow:auto; background:#f3f7ee; border-radius:12px; padding:8px; margin:8px 0;">${notes || '（无更新说明）'}</div>
            ${m.mandatory ? '<p style="color:#c23d2b; font-size:0.78rem;">⚠️ 此为强制更新</p>' : ''}
            <div style="display:flex; gap:8px; margin-top:12px;">
                <button id="doUpdateBtn" class="primary">立即更新</button>
                ${m.mandatory ? '' : '<button id="laterUpdateBtn">稍后</button>'}
            </div>
            <div id="updateProgressWrap" style="display:none; margin-top:12px;">
                <div style="font-size:0.75rem;"><span id="updatePhase">准备中</span>：<span id="updateProgressText">0</span>%</div>
                <div style="height:10px; background:#e3eada; border-radius:6px; overflow:hidden; margin-top:4px;">
                    <div id="updateProgressBar" style="height:100%; width:0%; background:linear-gradient(135deg,#2b6e2f,#4c9e2c); transition:width .2s;"></div>
                </div>
                <div id="updateHint" style="font-size:0.72rem; color:#7d9870; line-height:1.5; margin-top:6px; white-space:pre-line;"></div>
            </div>
        </div>`;
        document.body.appendChild(modal);
        lastUpdatePct = 0;
        const doBtn = modal.querySelector('#doUpdateBtn');
        const later = modal.querySelector('#laterUpdateBtn');
        doBtn.onclick = function() {
            if (updateInFlight) return;                 // 已在更新中，直接忽略重复点击
            if (!pythonAPI) { alert('程序还没就绪，请稍后再试'); return; }
            updateInFlight = true;
            lastUpdatePct = 0;
            doBtn.disabled = true;
            doBtn.textContent = '正在更新…';
            doBtn.style.opacity = '0.65';
            if (later) later.disabled = true;
            document.getElementById('updateProgressWrap').style.display = 'block';
            setUpdateHint('正在下载新版本，请勿关闭软件。支持断点续传，网络波动会自动重试。');
            pythonAPI.startUpdate(JSON.stringify(lastUpdateManifest));
        };
        if (later) later.onclick = () => {
            if (updateInFlight) return;
            modal.remove(); afterVersionCheck();
        };
    }

    function onUpdateProgress(pct, phase) {
        const n = Math.max(0, Math.min(100, Number(pct) || 0));
        if (n < lastUpdatePct) return;               // 进度只增不减，杜绝「鬼畜」
        lastUpdatePct = n;
        const bar = document.getElementById('updateProgressBar');
        const txt = document.getElementById('updateProgressText');
        const ph = document.getElementById('updatePhase');
        if (bar) bar.style.width = n + '%';
        if (txt) txt.textContent = n;
        if (ph && phase) ph.textContent = phase;
    }

    function onUpdateLog(msg) {
        if (updateInFlight) setUpdateHint(String(msg || ''));
    }

    function onUpdateDone() {
        onUpdateProgress(100, '已安装');
        setUpdateHint('新版本已安装，软件即将关闭并自动重新打开；如果没有自动打开，请手动运行程序（本机数据不会丢）。', '#2b6e2f');
    }

    function onUpdateError(obj) {
        updateInFlight = false;
        const msg = (obj && obj.message) ? obj.message : '未知错误';
        const status = document.getElementById('updateStatus');
        if (status) status.textContent = '更新失败：' + msg.replace(/\n/g, ' ');
        // 不再弹英文原始报错：错误直接写在弹窗里，按钮变「重试更新」
        const doBtn = document.getElementById('doUpdateBtn');
        const later = document.getElementById('laterUpdateBtn');
        if (doBtn) {
            doBtn.disabled = false;
            doBtn.style.opacity = '1';
            doBtn.textContent = '重试更新';
        }
        if (later) {
            later.disabled = false;
            later.textContent = '稍后';
        }
        setUpdateHint(msg + '\n（下载失败不会改动现有程序，可以放心重试）', '#a8622f');
    }

    function maybeAutoCheckUpdate() {
        const repo = localStorage.getItem('update_github_repo') || '';
        const url = localStorage.getItem('update_manifest_url') || '';
        if (!pythonAPI) return;
        if (repo || url) {
            // 启动后静默检查一次（内部先查版本，再查赛季 / 精灵新增）
            setTimeout(() => doCheckUpdate(true), 1500);
        } else if (getDataPackUrl()) {
            // 没配版本地址也要检查数据包，否则新赛季永远同步不到
            setTimeout(() => checkGameDataUpdates(true), 1500);
        }
    }

    // 启动后静默同步一次游戏数据由 initPythonAPI 的通道就绪回调触发（时序更可靠）
    function init(){ loadData(); initTabs(); bindActions(); initPythonAPI(); fullRender(); loadUpdateConfig(); loadDataConfig(); bindDataSyncButtons(); maybeAutoCheckUpdate(); }
    init();
</script>
</body>
</html>
"""


# =============================================================================
# 自动更新：语义化版本比对 + 下载 + 自替换
# =============================================================================

def parse_version(v):
    """把 'v1.2.10' / '1.2.3' / '1.10.0' 解析为可比较的元组，避免字符串比较的坑。"""
    if not v:
        return (0,)
    v = str(v).strip().lstrip('vVuU').strip()
    parts = re.split(r'[.\-_+]', v)
    out = []
    for p in parts:
        m = re.match(r'\d+', p)
        out.append(int(m.group()) if m else 0)
    return tuple(out)


def compare_versions(a, b):
    """返回 1(a>b) / -1(a<b) / 0(相等)。"""
    pa, pb = parse_version(a), parse_version(b)
    length = max(len(pa), len(pb))
    pa = pa + (0,) * (length - len(pa))
    pb = pb + (0,) * (length - len(pb))
    return (pa > pb) - (pa < pb)


def _mirror_urls(url):
    """给 GitHub raw 直链生成备用镜像候选（国内 raw 经常 502 / 读超时 / 被重置）。
    1.3.12 起移除 jsDelivr：它把 `@main` 分支解析锁到抓包时的 commit，缓存 12 小时，
    加 `?_t` / purge.jsdelivr.net 都刷不掉；发版后这段时间内会一直返回上一版
    version.json / 数据包，老客户端因此误报「已是最新版本」。
    现在只保留实时回源的线路。非 raw 链接返回空列表。"""
    m = re.match(r'https?://raw\.githubusercontent\.com/([^/]+)/([^/]+)/([^/]+)/(.+)', url or '')
    if not m:
        return []
    owner, repo, branch, path = m.groups()
    raw = "https://raw.githubusercontent.com/%s/%s/%s/%s" % (owner, repo, branch, path)
    return [
        "https://github.com/%s/%s/raw/%s/%s" % (owner, repo, branch, path),
        "https://ghproxy.net/%s" % raw,
        "https://gh-proxy.com/%s" % raw,
        "https://mirror.ghproxy.com/%s" % raw,
    ]


def _host_of(url):
    m = re.match(r'https?://([^/]+)', url or '')
    return m.group(1) if m else (url or '')[:24]


def _err_text(e):
    if isinstance(e, urllib.error.HTTPError):
        return "HTTP %s" % e.code
    if isinstance(e, TimeoutError) or 'timed out' in str(e).lower():
        return "读超时"
    low = str(e).lower()
    if 'getaddrinfo' in low or 'name or service not known' in low:
        return "域名解析失败"
    if '10054' in str(e) or 'forcibly closed' in low or 'connection reset' in low:
        return "连接被重置"
    if '10060' in str(e):
        return "连接超时"
    if '10061' in str(e) or 'refused' in low:
        return "连接被拒绝"
    return str(e)[:40]


def http_get_json(url, timeout=15, retries=0, backoff=1.5):
    """拉取 JSON。retries 为额外重试次数（网络抖动/读超时时有用）。
    4xx 不重试——文件不存在或没权限，重试只会白等。"""
    last = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': 'IsekiArrest-Updater',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
            })
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = resp.read().decode('utf-8')
            return json.loads(data)
        except urllib.error.HTTPError as e:
            last = e
            if 400 <= e.code < 500:
                raise
        except Exception as e:
            last = e
        if attempt < retries:
            time.sleep(backoff * (attempt + 1))
    raise last


def http_get_json_multi(url, timeout=12, max_candidates=None):
    """依次尝试主地址与备用镜像，返回 (json, 实际命中的地址)。
    - 主地址失败后会带 `_t=<时间戳>` 再试一次：GitHub 边缘节点缓存损坏时会固定返回 502，
      换一个 query 参数即可绕开坏缓存（raw 会忽略该参数）。
    - 镜像各试一次；max_candidates 可限制总尝试数，避免版本检查时等太久。
    - 主地址 404 直接短路：仓库里就没有这个文件，镜像也不会有。"""
    candidates = [url] + _mirror_urls(url)
    if max_candidates:
        candidates = candidates[:max_candidates]
    errors = []
    seen = set()
    for idx, u in enumerate(candidates):
        attempts = [u]
        if idx == 0:
            sep = '&' if '?' in u else '?'
            attempts.append(u + sep + '_t=%d' % int(time.time()))
        for au in attempts:
            if au in seen:
                continue
            seen.add(au)
            try:
                data = http_get_json(au, timeout=timeout, retries=0)
                return data, u
            except urllib.error.HTTPError as e:
                errors.append("%s → %s" % (_host_of(u), _err_text(e)))
                if e.code == 404 and idx == 0:
                    raise RuntimeError("；".join(errors))
            except Exception as e:
                errors.append("%s → %s" % (_host_of(u), _err_text(e)))
    # 去重保序，避免同一域名重复刷屏
    uniq = []
    for e in errors:
        if e not in uniq:
            uniq.append(e)
    raise RuntimeError("；".join(uniq) if uniq else "无可用地址")


def fetch_version_manifest(url, timeout=6, max_wait=10):
    """版本清单（version.json）专用：并发请求主地址与全部镜像，取版本号最高的那份。

    为什么不能「第一个成功就返回」：
      jsDelivr / ghproxy 等 CDN 会按固定 URL 缓存 version.json。1.3.10 之前只给主地址
      加 `?_t=` 破缓存，镜像一律用固定 URL；国内 raw 主地址连不上时就会读到旧清单，
      把线上 1.3.10 读成 1.3.6，于是提示「已是最新版本（1.3.6）」。
    现在每条线路都带 `_t`，并发取回后按 version 字段取最新，个别节点缓存旧版也影响不了结果。
    返回 (manifest_dict, 命中地址)；全部失败抛 RuntimeError（中文原因）。
    """
    from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
    candidates = [url] + _mirror_urls(url)
    ts = int(time.time())
    jobs = []
    for u in candidates:
        sep = '&' if '?' in u else '?'
        jobs.append((u + sep + '_t=%d' % ts, u))

    def _vkey(v):
        p = parse_version(v)
        return p + (0,) * max(0, 6 - len(p))

    def _fetch(au, orig):
        try:
            return http_get_json(au, timeout=timeout, retries=0), orig, ''
        except Exception as e:
            return None, orig, "%s → %s" % (_host_of(orig), _err_text(e))

    good, errors = [], []
    pool = ThreadPoolExecutor(max_workers=min(6, len(jobs)))
    try:
        pending = set(pool.submit(_fetch, au, u) for au, u in jobs)
        deadline = time.monotonic() + max_wait
        first_ok_at = None
        grace = 1.5          # 拿到第一份清单后再给其它线路 1.5 秒，取其中版本号最高的
        while pending and time.monotonic() < deadline:
            if first_ok_at is None:
                left = deadline - time.monotonic()
            else:
                left = min(deadline - time.monotonic(),
                           first_ok_at + grace - time.monotonic())
                if left <= 0:
                    break
            done, pending = wait(pending, timeout=max(0.05, left),
                                 return_when=FIRST_COMPLETED)
            for f in done:
                data, orig, err = f.result()
                if isinstance(data, dict) and data.get('version'):
                    good.append((_vkey(str(data['version'])), data, orig))
                    if first_ok_at is None:
                        first_ok_at = time.monotonic()
                elif err:
                    errors.append(err)
            if not done:
                break            # 剩下的线路太慢，用已拿到的结果，不必干等
    finally:
        pool.shutdown(wait=False)
    if good:
        good.sort(key=lambda x: x[0])
        return good[-1][1], good[-1][2]
    uniq = []
    for e in errors:
        if e not in uniq:
            uniq.append(e)
    raise RuntimeError("；".join(uniq[:4]) if uniq else "所有更新地址均不可用")


def github_put_file(repo, path, branch, token, body, message, timeout=60):
    """用 GitHub Contents API 新建/覆盖仓库里的一个文件（发布者上传数据包用）。
    body: bytes；返回 {commit, url, created}；失败抛 RuntimeError（带中文原因）。
    注意：只做「整文件覆盖」，不做增量 diff——数据包本来就是一整份 JSON。"""
    repo = (repo or '').strip().strip('/')
    path = (path or '').strip().lstrip('/')
    branch = (branch or 'main').strip() or 'main'
    token = (token or '').strip()
    if not token:
        raise RuntimeError("没有填写 GitHub Token")
    if not re.match(r'^[\w.\-]+/[\w.\-]+$', repo):
        raise RuntimeError("仓库格式应为 owner/repo，例如 H-ZHOWEI/iseki-arrest")
    if not path:
        raise RuntimeError("仓库内路径为空")

    api_url = "%s/repos/%s/contents/%s" % (GITHUB_API, repo, urllib.parse.quote(path, safe='/'))
    headers = {
        'Authorization': 'token %s' % token,
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'IsekiArrest-Publisher',
        'Content-Type': 'application/json; charset=utf-8',
    }

    # 1) 取现有文件 sha（不存在则新建）
    sha = None
    try:
        req = urllib.request.Request(
            api_url + '?ref=' + urllib.parse.quote(branch, safe=''), headers=headers)
        with urllib.request.urlopen(req, timeout=20) as r:
            sha = json.loads(r.read().decode('utf-8')).get('sha')
    except urllib.error.HTTPError as e:
        if e.code != 404:
            _raise_github_error(e)

    # 2) PUT 提交
    payload = {
        'message': message,
        'content': base64.b64encode(body).decode('ascii'),
        'branch': branch,
    }
    if sha:
        payload['sha'] = sha
    try:
        req = urllib.request.Request(
            api_url, data=json.dumps(payload).encode('utf-8'), headers=headers, method='PUT')
        with urllib.request.urlopen(req, timeout=timeout) as r:
            res = json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        _raise_github_error(e)

    return {
        'commit': ((res.get('commit') or {}).get('sha') or '')[:7],
        'url': (res.get('content') or {}).get('html_url', ''),
        'created': sha is None,
    }


def _raise_github_error(e):
    """把 GitHub API 的 HTTP 错误翻译成能照着做的中文提示。"""
    detail = ''
    try:
        detail = json.loads(e.read().decode('utf-8')).get('message', '')
    except Exception:
        pass
    if e.code == 401:
        hint = "Token 无效或已过期，请重新生成一个"
    elif e.code == 403:
        hint = "权限不足或触发了限制：Token 需要该仓库的 Contents 读写权限"
    elif e.code == 404:
        hint = "仓库 / 分支 / 路径不存在，或 Token 无权访问该仓库"
    elif e.code in (409, 422):
        hint = "文件刚被改动过（sha 冲突），请再点一次上传"
    else:
        hint = "HTTP %s" % e.code
    raise RuntimeError(hint + (('：' + detail) if detail else ''))


def _update_candidate_urls(url):
    """给 exe 直链生成备用线路：主地址 → 带时间戳绕坏缓存 → 两个 ghproxy → github.com/raw。
    1.3.12 起移除 jsDelivr：它对 >20MB 文件会 403，且 @main 快照会滞后 12 小时。"""
    u = (url or "").strip()
    if not u:
        return []
    out = [u]
    m = re.match(r'https?://raw\.githubusercontent\.com/([^/]+)/([^/]+)/([^/]+)/(.+)', u)
    if m:
        clean = u.split('?', 1)[0]
        sep = '&' if '?' in u else '?'
        out.append(u + sep + '_t=%d' % int(time.time()))
        out.append("https://ghproxy.net/" + clean)
        out.append("https://gh-proxy.com/" + clean)
        owner, repo, branch, path = m.groups()
        out.append("https://github.com/%s/%s/raw/%s/%s" % (owner, repo, branch, path))
    seen, res = set(), []
    for x in out:
        if x not in seen:
            seen.add(x)
            res.append(x)
    return res


def _probe_range(url, timeout=10):
    """用 1 字节 Range 请求探测线路：返回 (文件总大小, 是否支持断点/分段)。"""
    req = urllib.request.Request(url, headers={
        'User-Agent': 'IsekiArrest-Updater',
        'Range': 'bytes=0-0',
        'Cache-Control': 'no-cache',
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        total, supports = 0, False
        cr = r.headers.get('Content-Range') or ''
        if cr and '/' in cr:
            supports = True
            try:
                total = int(cr.rsplit('/', 1)[1])
            except (ValueError, IndexError):
                total = 0
        if not total:
            cl = r.headers.get('Content-Length')
            if cl and cl.isdigit():
                total = int(cl)
        try:
            r.read(64)      # 把响应体读掉，连接可复用
        except Exception:
            pass
        return total, supports


def _friendly_download_error(e):
    """把底层英文网络异常翻成用户能照着做的中文，绝不把原始 traceback 甩给玩家。
    注意 _err_text 会先把异常规范化成「读超时 / 域名解析失败」等中文，两种写法都要认。"""
    s = _err_text(e)
    low = (str(e) + ' ' + s).lower()
    if '没有写入权限' in s or '校验不通过' in s or '不是有效的可执行程序' in s or '缺少 download_url' in low:
        return s
    if any(k in low for k in ('timed out', 'timeout', 'read operation', '读超时', '超时', '926')):
        return ("下载超时：网络在传输过程中断开了，已自动重试并切换线路。\n"
                "可以点「重试更新」继续（已下载的部分会自动续传），或换个网络再试。")
    if any(k in low for k in ('connection reset', 'forcibly closed', 'connection aborted',
                              'remote end', '连接被重置', '10054')):
        return ("网络连接被重置（国内访问 GitHub 常见），已自动切换线路重试。\n"
                "仍失败的话请点「重试更新」或稍后再试。")
    if any(k in low for k in ('getaddrinfo', 'name or service not known', '11001',
                              'dns', 'nodename', '域名解析失败')):
        return "连不上下载地址（DNS / 网络异常）。请确认网络正常后点「重试更新」。"
    if ' 404' in ' ' + s or s.strip().startswith('404') or 'not found' in low:
        return "找不到新版本安装包（404），可能是发布者还没上传完整，请稍后再试。"
    if ' 403' in ' ' + s or ' 429' in ' ' + s:
        return "下载地址被限流，已切换线路；仍失败请稍后再试。"
    if s.startswith(('全部线路', '下载', '更新', '当前为', '程序所在', '分段', '文件大小')):
        return s
    return "更新失败：" + s


def _fetch_range(url, start, end, part_path, timeout=25, retries=5, on_bytes=None):
    """把 [start, end] 这段下载到 part_path；中断后按已写字节续传。返回写入字节数。"""
    want = end - start + 1
    last = None
    for attempt in range(retries):
        offset = os.path.getsize(part_path) if os.path.exists(part_path) else 0
        if offset >= want:
            return offset
        headers = {
            'User-Agent': 'IsekiArrest-Updater',
            'Cache-Control': 'no-cache',
            'Range': 'bytes=%d-%d' % (start + offset, end),
        }
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                status = getattr(resp, 'status', None) or resp.getcode()
                # 服务端忽略了 Range（返回整包）→ 清掉本段从头下，避免拼接错位
                if offset and status != 206:
                    offset = 0
                    with open(part_path, 'wb'):
                        pass
                with open(part_path, 'ab') as f:
                    while True:
                        buf = resp.read(64 * 1024)
                        if not buf:
                            break
                        f.write(buf)
                        offset += len(buf)
                        if on_bytes:
                            on_bytes(len(buf))
            if offset >= want:
                return offset
            last = RuntimeError("本段只收到 %d/%d 字节" % (offset, want))
        except Exception as e:
            last = e
        time.sleep(min(1.5 + attempt, 5))
    raise RuntimeError("分段下载失败：%s" % _err_text(last))


class _DownloadProgress(object):
    """多线程进度聚合：只在百分比上升时回传，避免进度条来回跳（鬼畜）。"""
    def __init__(self, total, cb):
        self.total = total or 0
        self.cb = cb
        self.lock = threading.Lock()
        self.done = 0
        self.last = -1

    def add(self, n):
        if not self.cb or not self.total:
            return
        with self.lock:
            self.done += n
            pct = min(99, int(self.done * 100 / self.total))
            if pct > self.last:
                self.last = pct
                try:
                    self.cb(pct)
                except Exception:
                    pass


def http_download_fast(url, dest, expected_size=0, progress_cb=None, log_cb=None,
                       workers=5, timeout=25):
    """多线程分段 + 断点续传 + 多线路回退下载 exe。返回 {url, size, workers}。
    实测 GitHub raw / ghproxy 都支持 Range（206），4~6 路并发比单连接快数倍；
    单段读超时只影响那一段，重试时从已写字节继续，不会从头再来。"""
    urls = _update_candidate_urls(url)
    if not urls:
        raise ValueError("下载地址为空")
    errors = []
    for cand in urls:
        try:
            if log_cb:
                log_cb("正在尝试线路：" + _host_of(cand))
            total, supports = _probe_range(cand, timeout=10)
            if expected_size and total and total != expected_size:
                raise RuntimeError("文件大小与清单不符（%d ≠ %d）" % (total, expected_size))
            if not total:
                total = expected_size          # 探测不到就用清单里的 size
            if not total:
                # 极端情况：服务端不给大小、清单也没写 → 退化为普通单流下载，
                # 进度只报到 50%，最终靠 SHA256 / MZ 头保证文件正确
                req = urllib.request.Request(cand, headers={'User-Agent': 'IsekiArrest-Updater'})
                with urllib.request.urlopen(req, timeout=30) as r, open(dest, 'wb') as f:
                    while True:
                        buf = r.read(64 * 1024)
                        if not buf:
                            break
                        f.write(buf)
                if progress_cb:
                    progress_cb(50)
                return {'url': cand, 'size': os.path.getsize(dest), 'workers': 1}
            prog = _DownloadProgress(total, progress_cb)
            n = 1
            if supports:
                n = max(1, min(6, workers, int(total // (4 * 1024 * 1024)) or 1))
            chunk = (total + n - 1) // n
            bounds = []
            for i in range(n):
                s = i * chunk
                e = min(total - 1, (i + 1) * chunk - 1)
                if s <= e:
                    bounds.append((s, e))
            parts = [dest + '.part%d' % i for i in range(len(bounds))]
            for p in parts:
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except OSError:
                        pass
            failures = []

            def worker(idx, s, e, path):
                try:
                    _fetch_range(cand, s, e, path, timeout=timeout,
                                 retries=5, on_bytes=prog.add)
                except Exception as ex:
                    failures.append((idx, ex))

            threads = [threading.Thread(target=worker, args=(i, s, e, parts[i]), daemon=True)
                       for i, (s, e) in enumerate(bounds)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            if failures:
                raise RuntimeError("第 %s 段下载失败：%s" % (
                    ','.join(str(i + 1) for i, _ in failures), _err_text(failures[0][1])))
            with open(dest, 'wb') as out:
                for p in parts:
                    with open(p, 'rb') as f:
                        while True:
                            buf = f.read(1024 * 1024)
                            if not buf:
                                break
                            out.write(buf)
            for p in parts:
                try:
                    os.remove(p)
                except OSError:
                    pass
            got = os.path.getsize(dest)
            if got != total:
                raise RuntimeError("下载不完整（%d/%d 字节）" % (got, total))
            return {'url': cand, 'size': total, 'workers': len(bounds)}
        except Exception as e:
            errors.append("%s → %s" % (_host_of(cand), _err_text(e)))
            if log_cb:
                log_cb("线路不通，换下一条")
            try:
                if os.path.exists(dest):
                    os.remove(dest)
            except OSError:
                pass
            continue
    raise RuntimeError("全部线路均失败：" + "；".join(errors[:3]))


def sha256_of_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def fetch_github_release(repo):
    """从 GitHub Releases 获取最新版本的下载信息。
    repo 形如 'owner/repo' 或完整 releases/latest API 地址。
    返回 {'version': '1.3.1', 'download_url': '...', 'notes': '...'} 或 None。
    （注：本软件默认改用仓库根目录 version.json 清单，其 download_url 指向仓库内
    dist/异色逮捕计划.exe —— 模仿「喵想奇记」把 exe 直接提交进仓库的做法。）"""
    if repo.startswith('http'):
        api_url = repo
    else:
        api_url = "https://api.github.com/repos/%s/releases/latest" % repo.strip('/')
    try:
        rel = http_get_json(api_url, timeout=15)
    except urllib.error.HTTPError as e:
        # 404 = 该仓库还没有任何 Release（或仓库不存在），属正常状态，
        # 返回 None 交由上层提示“暂无发布版本/已是最新”，而不是当成错误。
        if e.code == 404:
            return None
        raise
    if not rel or rel.get("message") in ("Not Found",) or "tag_name" not in rel:
        return None
    tag = str(rel.get("tag_name", "")).lstrip('vV')
    version = tag or str(rel.get("tag_name", ""))
    assets = rel.get("assets", []) or []
    download_url = ""
    exe_name = "异色逮捕计划.exe"
    for a in assets:
        if a.get("name", "").lower() == exe_name.lower():
            download_url = a.get("browser_download_url", "")
            break
    if not download_url:
        for a in assets:
            if a.get("name", "").lower().endswith(".exe"):
                download_url = a.get("browser_download_url", "")
                break
    notes = rel.get("body", "") or ""
    size = 0
    for a in assets:
        if a.get("browser_download_url") == download_url:
            size = int(a.get("size") or 0)
            break
    return {"version": version, "download_url": download_url, "notes": notes, "size": size}


def apply_self_update(old_path, new_path):
    """在当前进程内把新 exe 换到原路径，返回新版本路径；失败抛 RuntimeError。

    1.3.10 / 1.3.11 用「启动独立 PowerShell 脚本、等进程退出后替换」，但
    DETACHED_PROCESS 会让 powershell.exe 在没有控制台时直接退出、脚本一行都不执行
    （实测：换成默认 creationflags 才正常写日志），于是「进度走完、软件关了、重开还是旧版」。
    Windows 允许重命名正在运行的 exe：改名后原路径空出来，直接写入新文件即可，
    不需要外部进程、不需要等父子 PID，也不受杀软拦截 .ps1 / Job Object 影响。
    """
    import shutil
    old_path = os.path.abspath(old_path)
    backup = old_path + '.bak'
    if os.path.exists(backup):
        try:
            os.remove(backup)          # 上次更新留下的备份，可能仍被占用
        except OSError:
            backup = old_path + '.%d.bak' % int(time.time())
    try:
        os.rename(old_path, backup)
    except Exception as ex:
        raise RuntimeError("无法重命名旧程序（%s）。可能是目录没有写入权限，"
                           "或程序被安全软件锁定；请把软件移到普通文件夹后重试。" % _err_text(ex))
    try:
        shutil.copyfile(new_path, old_path)
        with open(old_path, 'rb') as f:
            if f.read(2) != b'MZ':
                raise RuntimeError("替换后的文件不是有效 exe")
        if os.path.getsize(old_path) != os.path.getsize(new_path):
            raise RuntimeError("替换后的文件大小与安装包不符")
    except Exception as ex:
        # 尽力还原，绝不在原路径留下损坏的程序
        try:
            if os.path.exists(old_path):
                os.remove(old_path)
            os.rename(backup, old_path)
        except Exception:
            pass
        raise RuntimeError("无法替换程序文件（%s）。新版本已下载完成，"
                           "可以手动复制到软件目录覆盖原文件。" % _err_text(ex))
    try:
        os.remove(new_path)
    except OSError:
        pass
    return old_path




# ----------------------------- Python 后端（数据桥接与文件对话框）--------------------------------
class PythonAPI(QObject):
    """供 JavaScript 调用的 Python 对象，实现文件导入导出及粘贴导入"""

    # 跨线程安全执行 JS：子线程 emit，主线程（本对象线程亲和性）接收后调用 runJavaScript。
    # QWebEnginePage 非线程安全，绝不能在工作线程直接调用 runJavaScript，否则会段错误闪退。
    sigRunJs = pyqtSignal(str)

    def __init__(self, view):
        super().__init__()
        self.view = view
        self.sigRunJs.connect(self._runJs)

    def _runJs(self, js):
        """在主线程执行 JS（由 sigRunJs 排队调用）。"""
        try:
            self.view.page().runJavaScript(js)
        except Exception:
            pass
    
    @pyqtSlot(str)
    def exportWarehouse(self, dataStr):
        self._saveToFile(dataStr, "warehouse_backup.json")
    
    @pyqtSlot()
    def importWarehouse(self):
        self._loadFromFile(lambda content: self._injectModule("warehouse", content))
    
    @pyqtSlot(str)
    def exportPreset(self, dataStr):
        self._saveToFile(dataStr, "preset_backup.json")
    
    @pyqtSlot()
    def importPreset(self):
        self._loadFromFile(lambda content: self._injectModule("presetSpirits", content))
    
    @pyqtSlot(str)
    def exportSeasons(self, dataStr):
        self._saveToFile(dataStr, "seasons_backup.json")
    
    @pyqtSlot()
    def importSeasons(self):
        self._loadFromFile(lambda content: self._injectModule("seasons", content))
    
    @pyqtSlot(str)
    def exportCaptured(self, dataStr):
        self._saveToFile(dataStr, "captured_backup.json")
    
    @pyqtSlot()
    def importCaptured(self):
        self._loadFromFile(lambda content: self._injectModule("capturedSpirits", content))
    
    @pyqtSlot(str)
    def exportUnknown(self, dataStr):
        self._saveToFile(dataStr, "unknown_backup.json")
    
    @pyqtSlot()
    def importUnknown(self):
        self._loadFromFile(lambda content: self._injectModule("unknownRecords", content))
    
    @pyqtSlot(str, str)
    def importFromText(self, module, jsonText):
        try:
            data = json.loads(jsonText)
            if module == "captured":
                if not isinstance(data, list):
                    raise ValueError("已捕捉数据应为数组")
                self._injectModule("capturedSpirits", jsonText)
            elif module == "warehouse":
                if "ballTypes" not in data or "inventory" not in data:
                    raise ValueError("仓库数据需包含 ballTypes 和 inventory 字段")
                self._injectModule("warehouse", jsonText)
            elif module == "preset":
                if not isinstance(data, list):
                    raise ValueError("预设库数据应为数组")
                self._injectModule("presetSpirits", jsonText)
            elif module == "seasons":
                if not isinstance(data, list):
                    raise ValueError("赛季数据应为数组")
                self._injectModule("seasons", jsonText)
            elif module == "unknown":
                if not isinstance(data, list):
                    raise ValueError("未知记录数据应为数组")
                self._injectModule("unknownRecords", jsonText)
            else:
                raise ValueError("未知模块")
        except Exception as e:
            QtWidgets.QMessageBox.critical(None, "导入失败", f"解析错误：{e}")
    
    @pyqtSlot(str)
    def exportAllData(self, dataStr):
        self._saveToFile(dataStr, "all_data_backup.json")
    
    @pyqtSlot()
    def importAllData(self):
        self._loadFromFile(lambda content: self._injectAllData(content))

    # ----------------------------- 自动更新相关 -----------------------------
    @pyqtSlot(str)
    def checkUpdate(self, source_url):
        """检查更新（后台线程，结果经 onUpdateChecked 回调）。
        source 支持两种形式：
          - GitHub 仓库 'owner/repo'（或 releases API 地址）→ 走 Releases API，
            仓库没有 Release 时自动回退到内置的 version.json 清单；
          - version.json 直链 → 并发走主地址 + 镜像，取版本号最高的那份。
        结果一律带 current / latest / source，方便前端把「为什么已是最新」讲清楚。"""
        def _manifest_result(manifest, used):
            latest = str(manifest.get("version", ""))
            cmp = compare_versions(latest, APP_VERSION)
            base = {"current": APP_VERSION, "latest": latest,
                    "source": _host_of(used) if used else ""}
            if cmp < 0:
                d = dict(base)
                d["status"] = "stale"
                d["message"] = ("读到的线上版本 V%s 比本机 V%s 还旧，多半是更新地址填错或命中旧缓存。"
                                "请点「恢复默认更新地址」后重试，或直接从仓库下载最新版覆盖安装。"
                                % (latest, APP_VERSION))
                return d
            if cmp == 0:
                d = dict(base)
                d["status"] = "noupdate"
                return d
            d = dict(base)
            d["status"] = "update"
            d.update({
                "notes": manifest.get("notes", ""),
                "download_url": manifest.get("download_url", ""),
                "mandatory": bool(manifest.get("mandatory", False)),
                "sha256": manifest.get("sha256", ""),
                "size": int(manifest.get("size") or 0),
                "manifest_url": used,
            })
            return d

        def _run():
            result = {"status": "noupdate", "message": ""}
            try:
                source = (source_url or "").strip()
                low = source.lower()
                # 只有 owner/repo 或明确的 releases 地址才走 Releases；
                # github.com/.../raw/main/version.json 这类直链必须当清单处理。
                is_repo = bool(re.match(r'^[\w.\-]+/[\w.\-]+$', source))
                is_release = ('/releases' in low or 'api.github.com' in low)
                if not source:
                    result = {"status": "error", "message": "未配置更新来源，请点「恢复默认更新地址」"}
                elif is_repo or is_release:
                    info = fetch_github_release(source)
                    if not info:
                        # 仓库没有 Release 不能说「已是最新版本」：发布形态是仓库内 exe + version.json
                        if re.match(r'^https?://', DEFAULT_UPDATE_REPO or ''):
                            manifest, used = fetch_version_manifest(DEFAULT_UPDATE_REPO)
                            result = _manifest_result(manifest, used)
                            result["message"] = "该仓库暂无 Release，已自动改用仓库内更新清单检查"
                        else:
                            result = {"status": "noupdate", "current": APP_VERSION, "latest": "",
                                      "source": "GitHub Releases",
                                      "message": "该仓库暂无 Release，且未配置更新清单直链"}
                    else:
                        latest = info.get("version", "")
                        cmp = compare_versions(latest, APP_VERSION)
                        if cmp <= 0:
                            result = {"status": "noupdate", "current": APP_VERSION,
                                      "latest": latest, "source": "GitHub Releases"}
                        else:
                            result = {
                                "status": "update",
                                "current": APP_VERSION,
                                "latest": latest,
                                "source": "GitHub Releases",
                                "notes": info.get("notes", ""),
                                "download_url": info.get("download_url", ""),
                                "mandatory": False,
                                "sha256": "",
                                "size": int(info.get("size") or 0),
                                "manifest_url": "github:" + source,
                            }
                else:
                    manifest, used_manifest = fetch_version_manifest(source)
                    result = _manifest_result(manifest, used_manifest)
            except urllib.error.HTTPError as e:
                result = {"status": "error", "message": "HTTP 错误 %s：%s" % (e.code, e.reason)}
            except Exception as e:
                result = {"status": "error", "message": "检查更新失败：%s" % e}
            try:
                self.sigRunJs.emit("onUpdateChecked(%s)" % json.dumps(result, ensure_ascii=False))
            except Exception:
                pass
        threading.Thread(target=_run, daemon=True).start()

    @pyqtSlot(str)
    def syncGameData(self, url):
        """拉取游戏数据包（预设精灵库 + 赛季）并回传给前端做差异检测。
        数据包更新不需要重新打包 exe，用户点「检查更新」即可拿到新赛季数据。
        主地址（GitHub raw）读超时时自动换 github.com 直链 / ghproxy 系列镜像，
        避免国内网络下整条同步失败；V1.3.12 起不再使用会缓存旧内容的 jsDelivr。"""
        def _run():
            try:
                target = (url or "").strip()
                if not target:
                    raise ValueError("未配置数据包地址")
                # 数据包是「整文件覆盖」上传的，固定 URL 容易被 CDN 缓存住上传前的旧内容；
                # 带一个时间戳让主地址和镜像都回源，保证拿到的是刚上传的那份。
                sep = '&' if '?' in target else '?'
                fresh = target + sep + '_t=%d' % int(time.time())
                pack, used = http_get_json_multi(fresh, timeout=15)
                if not isinstance(pack, dict):
                    raise ValueError("数据包格式错误（应为 JSON 对象）")
                result = {"status": "ok", "pack": pack, "source": used}
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    result = {"status": "error",
                              "message": "仓库里还没有 data/game_data.json（发布者需先导出一份上传）"}
                else:
                    result = {"status": "error", "message": "HTTP 错误 %s：%s" % (e.code, e.reason)}
            except Exception as e:
                msg = str(e)
                if 'timed out' in msg.lower() or '读超时' in msg:
                    msg = "网络读取超时（已尝试镜像地址）：%s" % msg
                result = {"status": "error", "message": "数据同步失败：%s" % msg}
            try:
                self.sigRunJs.emit("onGameDataFetched(%s)" % json.dumps(result, ensure_ascii=False))
            except Exception:
                pass
        threading.Thread(target=_run, daemon=True).start()

    @pyqtSlot(str)
    def exportDataPack(self, jsonStr):
        """导出数据包，供发布者覆盖仓库 data/game_data.json。"""
        self._saveToFile(jsonStr, "game_data.json")

    @pyqtSlot()
    def importDataPack(self):
        """从本地 game_data.json 导入数据包（网络全挂时的兜底）。
        走与在线同步完全相同的差异检测 + 用户确认流程，不会直接覆盖本地数据。"""
        try:
            filePath, _ = QtWidgets.QFileDialog.getOpenFileName(
                None, "选择数据包文件", "game_data.json", "JSON文件 (*.json)")
            if not filePath:
                return
            with open(filePath, 'r', encoding='utf-8-sig') as f:
                pack = json.load(f)
            if not isinstance(pack, dict):
                raise ValueError("文件内容不是 JSON 对象")
            if not isinstance(pack.get('spirits'), list) and not isinstance(pack.get('seasons'), list):
                raise ValueError("文件里没有 spirits / seasons 字段，可能选错了文件")
            result = {"status": "ok", "pack": pack,
                      "source": "file:" + os.path.basename(filePath)}
        except Exception as e:
            result = {"status": "error", "message": "读取数据包失败：%s" % e}
        try:
            self.sigRunJs.emit("onGameDataFetched(%s)" % json.dumps(result, ensure_ascii=False))
        except Exception:
            pass

    @pyqtSlot(str)
    def testDataPackUrls(self, url):
        """逐个测试数据包候选地址（主地址 + 镜像），把每条的结果回传前端。
        用户网络差异很大，让他点一下就知道该把哪条填进「数据包直链」。"""
        def _run():
            target = (url or "").strip()
            results = []
            try:
                candidates = ([target] if target else []) + _mirror_urls(target)
                if not candidates:
                    results.append({"url": target or "", "ok": False, "ms": 0, "msg": "地址为空"})
                for u in candidates:
                    t0 = time.time()
                    try:
                        http_get_json(u, timeout=8, retries=0)
                        results.append({"url": u, "ok": True, "ms": int((time.time() - t0) * 1000),
                                        "msg": "可用"})
                    except Exception as e:
                        results.append({"url": u, "ok": False, "ms": int((time.time() - t0) * 1000),
                                        "msg": _err_text(e)})
            except Exception as e:
                results.append({"url": target, "ok": False, "ms": 0, "msg": str(e)})
            try:
                self.sigRunJs.emit("onDataUrlTested(%s)" % json.dumps(
                    {"status": "ok", "results": results}, ensure_ascii=False))
            except Exception:
                pass
        threading.Thread(target=_run, daemon=True).start()

    @pyqtSlot(str)
    def startUpdate(self, manifestJson):
        """下载并自更新。同一时刻只允许一个更新任务（防止重复点击导致进度条鬼畜 / 多次替换）。"""
        if not hasattr(self, '_update_lock'):
            self._update_lock = threading.Lock()
        with self._update_lock:
            if getattr(self, '_update_running', False):
                return                      # 静默忽略重复点击，前端按钮也已禁用
            self._update_running = True

        def emit_progress(pct, phase):
            try:
                self.sigRunJs.emit("onUpdateProgress(%d, %s)" % (
                    int(pct), json.dumps(phase, ensure_ascii=False)))
            except Exception:
                pass

        def emit_log(msg):
            try:
                self.sigRunJs.emit("onUpdateLog(%s)" % json.dumps(msg, ensure_ascii=False))
            except Exception:
                pass

        def _run():
            new_path = None
            failed = False
            verified = False
            try:
                if not getattr(sys, 'frozen', False):
                    raise RuntimeError("当前为开发模式（未打包成 exe），无法执行自更新，请打包后再更新。")
                manifest = json.loads(manifestJson)
                download_url = (manifest.get("download_url") or "").strip()
                expected_sha = (manifest.get("sha256") or "").strip()
                try:
                    expected_size = int(manifest.get("size") or 0)
                except (TypeError, ValueError):
                    expected_size = 0
                if not download_url:
                    raise ValueError("更新清单缺少 download_url")

                old_path = os.path.abspath(sys.executable)
                # 先确认目标目录可写：不能写就直接提示，绝不把用户软件白白关掉
                probe = os.path.join(os.path.dirname(old_path), '.iseki_write_test')
                try:
                    with open(probe, 'w') as f:
                        f.write('ok')
                    os.remove(probe)
                except Exception:
                    raise RuntimeError(
                        "程序所在目录没有写入权限，无法自动覆盖。\n"
                        "请把软件移到普通文件夹（不要放 C:\\Program Files），"
                        "或右键「以管理员身份运行」后再点更新。")

                emit_progress(2, "准备下载")
                fd, new_path = tempfile.mkstemp(suffix='.exe', prefix='iseki_new_')
                os.close(fd)
                info = http_download_fast(
                    download_url, new_path, expected_size=expected_size,
                    progress_cb=lambda p: emit_progress(p, "下载中"),
                    log_cb=emit_log, workers=5, timeout=25)
                emit_log("下载完成（%d 路并发），正在校验安装包" % info['workers'])
                emit_progress(99, "校验安装包")

                with open(new_path, 'rb') as f:
                    magic = f.read(2)
                if magic != b'MZ':
                    raise ValueError("下载到的文件不是有效的可执行程序，可能线路返回了错误页面，请点「重试更新」")
                got = os.path.getsize(new_path)
                if expected_size and got != expected_size:
                    raise ValueError("安装包大小不符（%d ≠ %d 字节），请点「重试更新」" % (got, expected_size))
                if expected_sha:
                    actual = sha256_of_file(new_path)
                    if actual.lower() != expected_sha.lower():
                        raise ValueError("SHA256 校验不通过，文件可能下载不完整或被篡改，请点「重试更新」")

                verified = True
                emit_progress(100, "校验通过，正在安装")
                # 进程内直接替换：失败会抛异常，此时绝不退出程序
                apply_self_update(old_path, new_path)
                self.sigRunJs.emit("onUpdateDone()")
                # 尝试拉起新实例；即使失败，文件已经换好，用户手动打开即可
                try:
                    subprocess.Popen([old_path], close_fds=True)
                except Exception:
                    pass
                time.sleep(0.8)
                os._exit(0)
            except Exception as e:
                failed = True
                msg = _friendly_download_error(e)
                # 只有「下载并通过全部校验、但替换失败」才把新 exe 放到软件目录旁边，
                # 用户直接双击即可用上新版，不至于白下一遍 87MB
                if verified and new_path and os.path.exists(new_path):
                    try:
                        import shutil as _shutil
                        side = os.path.join(os.path.dirname(os.path.abspath(sys.executable)),
                                            '异色逮捕计划_新版.exe')
                        _shutil.copyfile(new_path, side)
                        msg += "\n\n新版本已放在软件目录：" + side + \
                               "\n直接双击它就能使用新版（本机数据不会丢）。"
                    except Exception:
                        msg += "\n\n新版本安装包：" + new_path
                try:
                    self.sigRunJs.emit("onUpdateError(%s)" % json.dumps(
                        {"message": msg, "detail": _err_text(e)}, ensure_ascii=False))
                except Exception:
                    pass
            finally:
                if failed and new_path and os.path.exists(new_path):
                    try:
                        os.remove(new_path)
                    except OSError:
                        pass
                with self._update_lock:
                    self._update_running = False
        threading.Thread(target=_run, daemon=True).start()

    @pyqtSlot(str, str, str)
    def previewRemotePack(self, repo, path, branch):
        """上传前拉取远端当前的数据包（主地址失败自动走镜像），供前端做「覆盖对比」展示。
        拉取失败也回包（status=error），前端降级为「直接覆盖 + 提示确认」。"""
        def _emit(obj):
            try:
                self.sigRunJs.emit("onRemotePackPreview(%s)" % json.dumps(obj, ensure_ascii=False))
            except Exception:
                pass

        def _run():
            raw = "https://raw.githubusercontent.com/%s/%s/%s" % (
                (repo or '').strip().strip('/'), (branch or 'main').strip() or 'main',
                (path or 'data/game_data.json').strip().lstrip('/'))
            try:
                pack, _hit = http_get_json_multi(raw, timeout=8)
                if not isinstance(pack, dict):
                    raise ValueError("远端数据包格式异常")
                _emit({"status": "ok", "pack": pack})
            except Exception as e:
                _emit({"status": "error", "message": str(e)})
        threading.Thread(target=_run, daemon=True).start()

    @pyqtSlot(str, str, str, str, str)
    def publishDataPack(self, packJson, token, repo, path, branch):
        """把数据包直接提交到 GitHub 仓库（发布者专用，走 Contents API）。
        packJson: 数据包 JSON；token: GitHub PAT（需 contents 写入权限）；
        repo: owner/repo；path: 仓库内路径（如 data/game_data.json）；branch: 分支。"""
        def _emit(obj):
            try:
                self.sigRunJs.emit("onDataPackPublished(%s)" % json.dumps(obj, ensure_ascii=False))
            except Exception:
                pass

        def _run():
            try:
                try:
                    pack = json.loads(packJson)
                except Exception as e:
                    raise RuntimeError("数据包 JSON 解析失败：%s" % e)
                if not isinstance(pack, dict) or not isinstance(pack.get('seasons'), list):
                    raise RuntimeError("数据包格式错误（缺少 seasons 数组）")
                seasons = pack.get('seasons') or []
                spirits = pack.get('spirits') or []
                if not seasons:
                    raise RuntimeError("数据包里没有任何赛季，用户端收不到内容，已取消上传")
                body = json.dumps(pack, ensure_ascii=False, indent=2).encode('utf-8')
                msg = "data: 更新数据包（%d 赛季 / %d 精灵）" % (len(seasons), len(spirits))
                info = github_put_file(repo, path or 'data/game_data.json', branch or 'main',
                                       token, body, msg)
                _emit({
                    'status': 'ok',
                    'commit': info.get('commit', ''),
                    'url': info.get('url', ''),
                    'created': info.get('created', False),
                    'bytes': len(body),
                    'seasons': len(seasons),
                    'spirits': len(spirits),
                })
            except Exception as e:
                _emit({'status': 'error', 'message': str(e)})
        threading.Thread(target=_run, daemon=True).start()

    def _injectAllData(self, content):
        try:
            data = json.loads(content)
            js = f"""
            localStorage.setItem('ball_final', JSON.stringify({json.dumps(data.get('ballTypes', []))}));
            localStorage.setItem('inv_final', JSON.stringify({json.dumps(data.get('inventory', {}))}));
            localStorage.setItem('preset_final', JSON.stringify({json.dumps(data.get('presetSpirits', []))}));
            localStorage.setItem('target_final', JSON.stringify({json.dumps(data.get('spirits', []))}));
            localStorage.setItem('captured_final', JSON.stringify({json.dumps(data.get('capturedSpirits', []))}));
            localStorage.setItem('seasons_final', JSON.stringify({json.dumps(data.get('seasons', []))}));
            localStorage.setItem('unknown_final', JSON.stringify({json.dumps(data.get('unknownRecords', []))}));
            localStorage.setItem('battle_rec_final', JSON.stringify({json.dumps(data.get('battleRecords', []))}));
            localStorage.setItem('growth_plan_data', JSON.stringify({json.dumps(data.get('growthData', {}))}));
            location.reload();
            """
            self.view.page().runJavaScript(js)
        except Exception as e:
            QtWidgets.QMessageBox.critical(None, "导入失败", f"全部数据导入错误：{e}")
    
    def _saveToFile(self, dataStr, defaultName):
        filePath, _ = QtWidgets.QFileDialog.getSaveFileName(None, "保存文件", defaultName, "JSON文件 (*.json)")
        if filePath:
            try:
                with open(filePath, 'w', encoding='utf-8') as f:
                    f.write(dataStr)
                QtWidgets.QMessageBox.information(None, "导出成功", f"数据已保存至：{filePath}")
            except Exception as e:
                QtWidgets.QMessageBox.critical(None, "导出失败", str(e))
    
    def _loadFromFile(self, callback):
        filePath, _ = QtWidgets.QFileDialog.getOpenFileName(None, "导入文件", "", "JSON文件 (*.json)")
        if filePath:
            try:
                with open(filePath, 'r', encoding='utf-8') as f:
                    content = f.read()
                callback(content)
            except Exception as e:
                QtWidgets.QMessageBox.critical(None, "导入失败", str(e))
    
    def _injectModule(self, module, content):
        try:
            data = json.loads(content)
            storageMap = {
                "capturedSpirits": "captured_final",
                "presetSpirits":   "preset_final",
                "seasons":         "seasons_final",
                "unknownRecords":  "unknown_final",
                "warehouse":       None
            }
            if module == "warehouse":
                js = f"""
                localStorage.setItem('ball_final', JSON.stringify({json.dumps(data['ballTypes'])}));
                localStorage.setItem('inv_final', JSON.stringify({json.dumps(data['inventory'])}));
                location.reload();
                """
                self.view.page().runJavaScript(js)
            else:
                key = storageMap.get(module)
                if not key:
                    raise ValueError("未知模块")
                
                if module == "presetSpirits":
                    # 预设精灵库：合并模式
                    self.view.page().runJavaScript(
                        f"localStorage.getItem('{key}') || '[]'",
                        lambda result: self._mergePresetData(result, data)
                    )
                else:
                    # 其他模块：替换模式
                    js = f"""
                    localStorage.setItem('{key}', JSON.stringify({json.dumps(data)}));
                    location.reload();
                    """
                    self.view.page().runJavaScript(js)
        except Exception as e:
            QtWidgets.QMessageBox.critical(None, "导入失败", f"模块导入错误：{e}")
    
    def _mergePresetData(self, result, new_data):
        """合并预设精灵数据"""
        try:
            current_data = json.loads(result) if result else []
            if not isinstance(current_data, list):
                current_data = []
            
            # 以 name 为唯一标识进行合并
            existing_names = {item['name'] for item in current_data}
            for new_item in new_data:
                if new_item['name'] not in existing_names:
                    current_data.append(new_item)
            
            # 保存并刷新
            js = f"""
            localStorage.setItem('preset_final', JSON.stringify({json.dumps(current_data)}));
            location.reload();
            """
            self.view.page().runJavaScript(js)
        except Exception as e:
            QtWidgets.QMessageBox.critical(None, "合并导入失败", f"错误：{e}")


class ExternalLinkPage(QtWebEngineWidgets.QWebEnginePage):
    
    def acceptNavigationRequest(self, url, nav_type, is_main_frame):
        """
        拦截外部链接，交给系统浏览器打开
        """
        
        if url.scheme() in ["http", "https"]:
            QDesktopServices.openUrl(url)
            return False
        
        return super().acceptNavigationRequest(
            url,
            nav_type,
            is_main_frame
        )
    
    def createWindow(self, window_type):
        """
        处理 target="_blank"
        """
        
        new_page = ExternalLinkPage(self.profile())
        
        new_page.urlChanged.connect(
            lambda url: QDesktopServices.openUrl(url)
        )
        
        return new_page


def getDefaultSeasons():
    now = datetime.now()
    end = now + timedelta(days=56)
    return [
        {"id":      4000, "name": "S1", "order": 1, "startDate": now.strftime("%Y-%m-%d"),
         "endDate": end.strftime("%Y-%m-%d")},
        {"id":      4001, "name": "S2", "order": 2, "startDate": now.strftime("%Y-%m-%d"),
         "endDate": end.strftime("%Y-%m-%d")}
    ]


# ----------------------------- 资源路径 ---------------------------------
def resource_path(name):
    """获取随程序分发的资源文件绝对路径。

    兼容两种运行方式：
      1. PyInstaller 打包后（onefile）：资源被解包到 sys._MEIPASS 临时目录；
      2. 源码直接运行：资源与本文件同目录。
    另外再兜底到「exe 所在目录」，方便用户把 ico 放在 exe 旁边使用。
    """
    candidates = []
    base = getattr(sys, "_MEIPASS", None)
    if base:
        candidates.append(os.path.join(base, name))
    if getattr(sys, "frozen", False):
        candidates.append(os.path.join(os.path.dirname(os.path.abspath(sys.executable)), name))
    else:
        candidates.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), name))
    candidates.append(os.path.join(os.getcwd(), name))
    for p in candidates:
        if os.path.exists(p):
            return p
    return candidates[-1]


# ----------------------------- 主程序 ---------------------------------
def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)
    
    view = QtWebEngineWidgets.QWebEngineView()
    # 设置自定义网页页签处理
    page = ExternalLinkPage(view)
    view.setPage(page)
    view.setWindowTitle("洛克王国 异色逮捕大师 - " + APP_VERSION)
    view.setMinimumSize(1000, 700)
    view.resize(1100, 800)
    
    icon_path = resource_path("application-note.ico")
    app_icon = QIcon(icon_path)
    if not app_icon.isNull():
        # 同时设置应用级图标，任务栏 / Alt+Tab / 窗口标题栏才不会显示默认图标
        app.setWindowIcon(app_icon)
        view.setWindowIcon(app_icon)
    
    tmp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8')
    html = HTML_CONTENT.replace("__APP_VERSION__", APP_VERSION)
    html = html.replace("__DEFAULT_REPO__", DEFAULT_UPDATE_REPO)
    html = html.replace("__DATA_URL__", DEFAULT_DATA_URL)
    tmp_file.write(html)
    tmp_file.close()
    
    channel = QWebChannel()
    python_api = PythonAPI(view)
    channel.registerObject("pythonAPI", python_api)
    view.page().setWebChannel(channel)
    
    file_url = QUrl.fromLocalFile(tmp_file.name)
    view.load(file_url)
    view.show()
    
    def cleanup():
        try:
            os.unlink(tmp_file.name)
        except Exception:
            pass
    
    app.aboutToQuit.connect(cleanup)
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()