当前目标：
- 维护 LineDogPet：一个 PySide6 桌面宠物应用，重点保证桌面小狗动画、右键菜单、工作模式、托盘恢复入口、尺寸调整、状态持久化和 Release 打包流程稳定。
- 新 Codex 会话应先读本文件，再读 `AGENTS.md` / `CLAUDE.md` 和相关代码，不要依赖旧聊天历史。

当前已完成：
- 应用入口在 `main.py`，包含 `QLocalServer` / `QLocalSocket` 单实例检测。
- 主窗口在 `pet_window.py`，已实现透明无边框窗口、启动 greet、idle/walk/sleep/status/mood 动画调度、鼠标拖拽、右键菜单、Ctrl+滚轮缩放、托盘菜单、工作模式、bye 退出动画和定时保存。
- 状态持久化在 `pet_stats.py`，保存饱食度、清洁度、好感度、位置、置顶、鼠标穿透、工作模式、宠物尺寸和互动 CD；坏 JSON 或坏类型会回退/转换/限制范围。
- GIF 加载和分类在 `pet_animation.py`，扫描 `assets/gif/*/*.gif`，walk 按文件名数字奇偶选择左右方向，`QMovie` 使用 `CacheNone`。
- 右键菜单在 `pet_menu.py`，包含属性条、喂食/洗澡/打招呼/玩耍、工作模式、置顶、鼠标穿透、尺寸预设和滑块、退出。
- 开机自启在 `pet_startup.py`，通过当前用户 Windows Run 注册表项启用/关闭，并从右键菜单勾选切换。
- 回归测试集中在 `test_regressions.py`，覆盖打包配置、单实例、工作模式、托盘恢复、尺寸同步、启动 greet、互动 5 秒保底、心情定时器、随机移动、持久化加载等。
- Release 构建由 `.github/workflows/release.yml` 负责；本地 `build.bat` 只使用已有 `.venv\Scripts\python.exe`，不安装依赖。

关键接口：
- `PetWindow._play(category)`：播放普通循环动画；工作模式或互动中会阻止不合适的切换。
- `PetWindow._play_once(category)`：播放互动/一次性动画，使用 interaction id 防止旧回调打断新动画，保底/超时 5 秒。
- `PetWindow._set_pet_size(size)`：统一尺寸入口；菜单滑块、预设按钮、Ctrl+滚轮都应走这里。
- `PetWindow._toggle_work()` / `_enter_work()` / `_exit_work()`：工作模式入口；工作模式保持可右键/托盘退出，不强制鼠标穿透。
- `PetWindow._setup_tray_menu()`：托盘菜单入口；鼠标穿透和工作模式必须有恢复/退出项。
- `PetWindow._sync_position_for_save()`：只在普通模式同步窗口坐标到 `stats.x/y`。
- `PetWindow._run_mood_cycle()` / `_play_timed_mood()`：心情动画必须走 mood timer，不要放到 100ms tick 随机触发。
- `PetStats.save()` / `PetStats._load()`：用户偏好和普通模式状态 JSON 持久化，测试时注入临时 `data_file/data_dir`。
- `PetAnimation.get_random(category)` / `get_walk(direction)`：按分类取 GIF，walk direction 为 `1` 右、`-1` 左、`0` jump。
- `PetMenu(callbacks)`：菜单通过 callbacks 调回 `PetWindow`，常用 key 有 `feed`、`bath`、`greet`、`play`、`toggle_work`、`toggle_topmost`、`toggle_click_through`、`set_size`、`quit`。
- `pet_startup.build_startup_command()`：打包后返回 exe 命令，开发模式返回 Python + `main.py` 命令。
- `pet_startup.is_startup_enabled()` / `set_startup_enabled(enabled)`：读取或写入 `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` 下的 `LineDogPet` 启动项。

关键资产文件：
- `assets/icon.ico`：应用和 Release exe 图标，`build.bat` 与 GitHub Actions 都引用它。
- `assets/gif/idle/*.gif`：默认待机动画和托盘图标第一帧来源。
- `assets/gif/greet/*.gif`：启动 greet、右键打招呼和 hover greet。
- `assets/gif/walk/*.gif`：左右移动动画，文件名数字奇偶影响方向选择。
- `assets/gif/jump/*.gif`：向上移动时使用。
- `assets/gif/work/*.gif`：工作模式动画。
- `assets/gif/bye/*.gif`：退出前告别动画。
- `assets/gif/eat/*.gif`、`bath/*.gif`、`play/*.gif`、`full/*.gif`：互动动画。
- `assets/gif/happy/*.gif`、`angry/*.gif`、`hungry/*.gif`、`dirty/*.gif`、`sleep/*.gif`、`astonishing/*.gif`：心情、状态和鼠标久离惊讶动画。
- `assets/gif/README.md`：GIF 资源说明。
- `assets/png/keyboard_reference.png`：键盘参考图片。

当前问题：
- 多个中文源码注释、菜单文本、README 和 `docs/CODE_MAP.md` 在当前终端输出中显示为乱码；需要确认文件真实编码/内容是否已经损坏，修复前不要盲改业务逻辑。
- `git status --short` 显示 `LineDogPet.spec` 是未跟踪文件；不要误删或覆盖，先确认它是否是用户需要保留的打包产物。
- `docs/CODE_MAP.md` 也显示乱码，后续如果新增代码文件或重大功能变更，需要先处理/确认文档编码再同步导航。
- 新增开机自启后需要继续关注真实 Windows 注册表行为；自动化测试使用 fake registry，不会写真实用户注册表。

下一步：
- 新会话先读 `CURRENT_STATUS.md`，再读 `AGENTS.md` / `CLAUDE.md`，然后根据任务读取相关模块。
- 做功能或 bugfix 时先加/改 `test_regressions.py` 回归测试，再改实现。
- 完成任何功能或 bugfix 后至少运行：`$env:QT_QPA_PLATFORM='offscreen'; python -m unittest test_regressions.py`、`python -m py_compile main.py config.py pet_stats.py pet_animation.py pet_menu.py pet_window.py pet_startup.py test_regressions.py`、`git diff --check`。
- 涉及可视交互时手动运行 `python main.py`，检查右键菜单、尺寸调节、工作模式、托盘入口、退出保存和二次启动单实例行为。
- 若任务涉及发布/打包，优先检查 `.github/workflows/release.yml`、`build.bat`、`assets/icon.ico`、`LineDogPet.spec` 的关系。

禁止改动：
- 不要把用户数据写到 exe 目录、源码目录或 PyInstaller 临时解包目录；持久化必须继续写 `%APPDATA%\LineDogPet\pet_data.json`。
- 不要让 `build.bat` 自动安装依赖；它只能使用已有 `.venv\Scripts\python.exe`。
- 不要引用不存在的打包资源；新增图标或资源必须真实提交并同步 CI。
- 不要让工作模式强制鼠标穿透；用户必须能右键或从托盘退出工作模式。
- 不要复用同一个 `QMovie` 同时做托盘图标和窗口动画。
- 不要用 `QMovie.loopCount = 1` 这类无效属性控制播放次数。
- 不要在互动动画进行中让 idle、walk、hover greet、心情动画或其他互动打断它。
- 不要在 100ms tick 中直接随机触发 happy/angry 心情动画；必须走 mood timer。
- 不要在工作模式下把工作模式窗口坐标保存成普通模式坐标。
- 不要随意删除或覆盖未跟踪的 `LineDogPet.spec`。
- 不要把开机自启写到 HKLM 或需要管理员权限的位置；必须使用当前用户 Run 项。
