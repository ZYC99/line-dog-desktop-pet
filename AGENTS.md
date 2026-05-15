# LineDogPet 代码编写规范

## 项目概览

这是一个 PySide6 桌面宠物应用。核心模块：

- `main.py`：应用入口、单实例检测。
- `pet_window.py`：主窗口、动画调度、鼠标交互、托盘和工作模式。
- `pet_stats.py`：属性、冷却时间、坐标和用户偏好的 JSON 持久化。
- `pet_animation.py`：GIF 素材扫描、分类和方向选择。
- `pet_menu.py`：右键菜单、属性条、尺寸控件。
- `config.py`：资源路径、数据路径和全局常量。
- `test_regressions.py`：回归测试。

文档约定：
- `docs/CODE_MAP.md` 是代码导航地图，新增文件或重大功能变更时必须同步更新。
- 小修小改（改一行、修 typo）不需要更新 CODE_MAP，行号偏几行不影响导航。

## 常用命令

```powershell
$env:QT_QPA_PLATFORM='offscreen'; python -m unittest test_regressions.py
python -m py_compile main.py config.py pet_stats.py pet_animation.py pet_menu.py pet_window.py test_regressions.py
git diff --check
```

## 打包和发布

- 普通用户不需要安装 Python、PySide6 或 PyInstaller；用户应从 GitHub Releases 下载 `LineDogPet.exe`。
- `build.bat` 仅供维护者本地验证打包，必须只使用已有 `.venv\Scripts\python.exe`，不得自动安装依赖。
- Release 构建由 `.github/workflows/release.yml` 负责，在 GitHub Actions runner 中安装 `requirements.txt`、运行测试、执行 PyInstaller 并上传 exe。
- 不要在本地打包脚本中引用不存在的资源，例如 `assets/icon.ico`；如果要加图标，先提交真实图标文件并同步更新 CI。

## 编码原则

- 优先做小而明确的改动，不做无关重构。
- 修改行为前先加回归测试；测试要先在旧实现上失败，再实现修复。
- 保持模块边界清晰：窗口交互放 `pet_window.py`，状态持久化放 `pet_stats.py`，菜单 UI 放 `pet_menu.py`。
- 不吞掉会影响行为的异常；如果需要降级，保留默认值并确保后续运算类型正确。
- 避免直接读写真实用户数据路径做测试；需要测试持久化时给 `PetStats` 注入临时 `data_file/data_dir`。

## PySide6 约定

- 测试 GUI 逻辑时使用 `QT_QPA_PLATFORM=offscreen`。
- 不要依赖不存在或只读的 Qt 属性赋值，例如 `QMovie.loopCount = 1` 不会控制播放次数。
- 对 `QMovie` 的信号连接要先断开旧连接，避免复用 movie 时触发旧回调。
- 托盘图标、窗口动画等不同用途不要复用同一个 `QMovie` 实例。
- 改变窗口尺寸时同步当前 `movie.setScaledSize(label.size())`。
- 动画素材使用 `QMovie.CacheNone`，避免动态缩放后继续显示旧尺寸缓存帧。
- 用户缩放窗口后要 clamp 到当前屏幕可用区域内。

## 状态和持久化

- `PetStats` 保存的是用户偏好和普通模式状态，不应保存临时运行态。
- 工作模式可以保持置顶和小尺寸，但不能强制鼠标穿透；用户必须能右键呼出菜单退出。
- 只有普通模式下才把当前窗口坐标同步到 `stats.x/stats.y`。
- 加载 JSON 时必须做类型转换和范围限制，坏数据应回退默认值。
- 首次使用时三项属性都应是满值：饱食度 100、清洁度 100、好感度 100。
- 打包资源路径和用户数据路径必须分开：资源可以来自 `sys._MEIPASS`，用户数据放 APPDATA。
- PyInstaller onefile 打包后，持久化仍写入 `%APPDATA%\LineDogPet\pet_data.json`，不会写入 exe 目录或临时解包目录；卸载或升级 exe 不会自动删除该文件。

## 交互规范

- 鼠标穿透必须有托盘恢复入口，避免用户无法再次操作宠物。
- 工作模式必须有托盘退出入口。
- 工作模式下小狗本体也必须能接收右键菜单。
- 右键菜单里的尺寸预设按钮和滑块必须保持同步。
- Ctrl + 滚轮缩放、菜单滑块缩放和预设按钮缩放应走同一个尺寸入口。
- 默认尺寸是 180px；尺寸预设为小 120px、中 180px、大 270px。
- 首次无存档启动时，默认位置在桌面右下角，右侧 margin 为屏幕宽度的 10%；后续启动必须使用用户上次保存的位置和尺寸。
- 喂食、洗澡、打招呼、玩耍等互动动画保底展示 5 秒。
- 互动动画进行中不能被 idle、walk、hover greet 或其他互动打断。
- 每次应用启动后直接播放一次 `greet` 分类动画；不要先播放 idle 再切换 greet。
- 好感度大于 90 时，每 1 分钟从 `idle` 和 `happy` 中随机选择一个模式播放，选中 `happy` 时播放 1 分钟。
- 好感度大于 80 且不超过 90 时，主要播放 idle，每 20 秒按 50% 概率播放 `happy` 5 秒。
- 好感度大于 50 且不超过 80 时，只播放 idle。
- 好感度低于 50 时，主要播放 idle，每 20 秒按 50% 概率播放 `angry` 5 秒。
- `happy`/`angry` 心情动画不要在 100ms tick 中直接随机触发，必须走心情定时器。
- 随机移动只在普通模式触发：无互动、非工作模式、属性状态不触发高优先级动画、空闲时间在 30 到 120 秒之间，并且本次 100ms tick 的随机值小于 0.003。

## 验收要求

完成任何功能或 bugfix 后至少运行：

```powershell
$env:QT_QPA_PLATFORM='offscreen'; python -m unittest test_regressions.py
python -m py_compile main.py config.py pet_stats.py pet_animation.py pet_menu.py pet_window.py test_regressions.py
git diff --check
```

涉及可视交互时，还需要手动运行：

```powershell
python main.py
```

检查右键菜单、尺寸调节、工作模式、托盘入口、退出保存和二次启动单实例行为。
