# 异色逮捕计划（洛克王国 异色逮捕大师）

洛克王国**异色精灵捕捉辅助记录工具**：把你要蹲的异色精灵、当前赛季、咕噜球库存、每只的消耗与成长计划都记清楚、算明白，告别纸笔和脑子记。

基于 **Python + PyQt5 + HTML/JS（QWebEngine）** 开发，用 PyInstaller 打包为单文件 `异色逮捕计划.exe`，**免安装、双击即用**。

> 📘 **新手请先看 [操作指引](操作指引.md)** —— 含界面总览、赛季/预设库/待捕捉目标/已捕捉确认/成长计划/数据备份/软件更新的逐步说明与常见问题。
> （仓库已附带 `操作指引.md`，下载后直接打开即可。）

---

## 主要功能

- **待捕捉异色精灵管理**：维护「预设精灵库」，一键把预设加入「当前捕捉目标」；支持「全部 / ✨奇遇 / 🍃非奇遇」筛选。
- **当前捕捉目标**：跟踪你正在蹲的那只精灵，球种库存可即时修改（捕捉中修改会同步快照影响后续消耗计算），支持删除模式批量移除。
- **已捕捉记录 & 未知记录确认**：记录获取方式（朋友赠送 / 赛季特色 / 自己捕捉），「自己捕捉」才计入平均消耗；不确定抓到什么时先存「未知」，确认后自动转为对应精灵并清理同名待捕捉。
- **赛季管理**：设置开始/结束时间，软件**自动算剩余天数并自动切换当前赛季**，用于给精灵分类。
- **周本精灵成长计划**：按 0→5 星（2 / 4 / 8 / 16 / 30，合计 60 材料）计算培养需求，记录已有材料、升星时自动扣除。
- **咕噜球仓库 & 统计**：记录库存、战斗/购买获得、合成属性球（1:1）；捕捉统计支持「每日需抓轮数」与「统一球数 / 每只所需球数」双向同步。
- **数据备份灵活**：各模块**独立导入导出** + 一键**全部数据备份** + **快速粘贴导入**（复制 JSON 直接导入，无需存文件）。
- **软件自动更新**：基于仓库内 `version.json` 清单（其 `download_url` 指向仓库 `dist/` 下的 exe，模仿「喵想奇记」把 exe 直接提交进仓库的做法），可手动「检查更新」，版本号按**语义化比对**（如 `1.10.0` 不会误判小于 `1.9.0`），发现新版一键更新。
- **本机存储、数据私有**：所有数据保存在本机（内置网页本地存储），不调用任何外部服务、不上传任何数据（仅可选的更新检查会访问 GitHub）。

---

## 目录说明

```
automation_app.py       主程序（PyQt5 + 内嵌 HTML/JS 单文件应用）
异色逮捕计划.spec       PyInstaller 打包配置（图标 / 单文件 / 体积裁剪规则都在这）
package.bat             一键打包脚本（自动探测 Python + 临时移走 PyQt5 自带 VC++ 库避免启动崩溃 + 按 spec 打包 + 体积校验）
application-note.ico    程序图标
version.json           自动更新清单（version + download_url 指向仓库内 dist/ 下的 exe）
version.json.example    自动更新配置示例（version.json 模板）
data/game_data.json     游戏数据包：预设精灵库 + 赛季（改了数据只需更新这个文件，不必重打包）
操作指引.md             使用手册（操作指引）
dist/异色逮捕计划.exe   已打包好的可执行文件（Windows，直接提交进仓库 dist/ 目录，供用户下载与自更新）
```

> 本仓库只包含程序源码、公共游戏数据与文档，**不含任何个人数据**。个人捕捉记录在 exe 本机存储里，请自行通过「全部数据备份」保管、迁移。

---

## 游戏数据同步（预设精灵库 / 赛季）

预设精灵库和赛季这类**会随赛季更新的数据**不再写死在 exe 里，而是放在仓库的 `data/game_data.json`：

- 软件点「检查更新」时会**顺带自动拉取**这个数据包（启动后也会静默同步一次），也可以单独点「同步数据」。
- **只增不删**：新增你本地没有的赛季 / 精灵；已存在的精灵仅当你**没手动改过**时才更新属性，你改过的精灵和自己新增的条目不会被覆盖；赛季起止日期以数据包为准，你给赛季加的分类与备注会保留。
- 数据包结构：

```json
{
  "data_version": "2026-11-20T00:00:00.000Z",
  "updated_at": "2026-11-20T00:00:00.000Z",
  "schema": 1,
  "seasons": [
    { "name": "S3", "order": 3, "startDate": "2026-11-20", "endDate": "2027-01-15" }
  ],
  "spirits": [
    { "name": "新精灵", "attrs": ["草", "火"], "type": "normal", "season": "S3" }
  ]
}
```

`data_version` 只做「是否变化」判断：与本地记录不同就合并一次，合并本身是幂等的（重复同步不会重复新增）。

**发布新赛季数据（不用重打包 exe）**：

1. 在本机软件里把赛季、预设精灵维护好。
2. 设置 → 软件更新 → **导出数据包（发布用）**，保存为 `game_data.json`。
3. 覆盖仓库 `data/game_data.json`，提交推送。
4. 用户下次点「检查更新」即可自动拿到新数据（数据版本会显示在设置页）。

---

## 直接使用

1. 在 GitHub 仓库的 **`dist/` 目录**下载 `异色逮捕计划.exe`，双击运行（免安装）。
2. 数据保存在本机；换电脑或重装前，请用「设置 → 全部数据备份」导出，到新机器再导入恢复。

---

## 从源码运行

需要 **Python 3.12+（Windows）**，依赖：

```bash
pip install pyinstaller PyQt5 PyQtWebEngine
python automation_app.py
```

---

## 自行打包

最简单的方式：双击 **`package.bat`**。它会依次完成：

1. **自动探测**第一个同时具备 PyQt5 与 PyInstaller 的 Python（本机多 Python 时不会指错环境）。
2. **临时移走 PyQt5 自带的 VC++ 运行库**（`msvcp140 / vcruntime140` 等），避免与系统运行库冲突导致打出的 exe 一启动就 `0xc0000005` 崩溃；打包结束（无论成败）再还原，不影响你的 Python 环境。
3. 按 `异色逮捕计划.spec` 打包：exe 图标、单文件、无控制台，以及**体积裁剪**都在 spec 里。
4. 打包，产物在 `dist/异色逮捕计划.exe`（约 **83 MB**）。

**关于体积裁剪**：PyQt5 的打包钩子会把整个 Qt5 目录（约 96 MB）都塞进去，不处理的话 exe 会到 107 MB，**超过 GitHub 单文件 100 MB 限制，push 会被拒绝**（`remote: error: File ... exceeds GitHub's file size limit of 100.00 MB`）。spec 里的 `DROP_NAMES / DROP_PREFIXES` 剔除了这些用不到的重型文件：

- `opengl32sw.dll`（软件 OpenGL 回退；WebEngine 在 Windows 上走 ANGLE）
- `qtwebengine_devtools_resources.pak`（开发者工具资源）
- 53 个 Chromium 语言包中除 `zh-CN / zh-TW / en-US` 外的全部
- 整套 `qml/`（QtQuick / Controls / Quick3D，本项目是纯 Widgets + HTML）
- `Qt5XmlPatterns / Qt5Quick3D* / Qt5Bluetooth / Qt5Sql / Qt5Test` 等未使用的模块

裁剪后 107 MB → **83 MB**，图标、WebEngine 渲染、自动更新均实测正常。若以后新增功能用到被剔除的模块，从 spec 里删掉对应条目即可。

也可以手动打包：

```bash
pip install pyinstaller PyQt5 PyQtWebEngine
pyinstaller 异色逮捕计划.spec --noconfirm
```

> 注意：`application-note.ico` 必须与打包脚本同目录，缺失会直接报错退出；打包请始终**按 spec 打包**，不要用 `pyinstaller automation_app.py`，否则会重新生成 spec 把裁剪规则冲掉，exe 又会涨回 107 MB。

---

## 发布更新（让软件能自更新）

更新机制模仿「喵想奇记」：**exe 直接提交进仓库的 `dist/` 目录**，再由仓库根目录的 `version.json` 清单告知软件最新版本与下载地址。默认更新源就是这个 `version.json`（位于 `https://raw.githubusercontent.com/H-ZHOWEI/iseki-arrest/main/version.json`）。

1. 改动代码后，把 `automation_app.py` 里的 `APP_VERSION` 改成新版本号（如 `1.3.1`，语义化版本）。
2. 双击 `package.bat` 重新打包，得到新的 `dist/异色逮捕计划.exe`。
3. 把新 exe 放进 **`dist/` 目录**并提交到仓库（`.gitignore` 已为它放行）。
   > **exe 必须小于 100 MB**，否则 GitHub 会拒绝推送。按 spec 打包出来的约 83 MB，正常没问题；若哪天体积又涨过 100 MB，说明裁剪规则被冲掉了，回看上一节「关于体积裁剪」。
4. 更新仓库根目录的 **`version.json`**：把 `version` 改成新版本号，`size` 填字节数，并用以下命令重算 `sha256` 后填进去：
   ```bash
   certutil -hashfile dist/异色逮捕计划.exe SHA256
   ```
5. 提交推送后，旧版用户点「检查更新」即可检测到新版本并一键更新（下载地址指向仓库内 `dist/` 的 exe，带 SHA256 校验）。

> 也可改用 GitHub Releases：在仓库 Releases 上传名为 `异色逮捕计划.exe` 的附件，再把「软件更新」里的更新来源填成 `H-ZHOWEI/iseki-arrest` 即可（两种来源软件都支持）。

`version.json.example` 是 `version.json` 的模板。

---

## 说明

本工具仅用于本机洛克王国异色精灵捕捉的**辅助记录与计算**，不读取游戏内存、不模拟点击、不连接任何外挂服务，不上传任何个人数据。
