当前目标：
- 完成键盘跟随功能的打包、文档同步和最终自动化验收，确保 Release CI 会编译新模块，后续维护者能从文档快速定位入口。

当前已完成：
- 键盘跟随已实现：仅在打工模式且显示键盘时启动全局键盘 hook。
- 打工模式显示键盘时，小狗切换为 `assets/generated/typing_dog_halfbody_left45.png` 静态 typing dog PNG；隐藏键盘或退出打工模式后恢复原有动画逻辑。
- BongoCat 键盘支持虚拟键映射、按下/松开状态、多键同时高亮和释放后恢复。
- hook 生命周期已接入 `pet_window.py`：进入打工模式并显示键盘时启动，隐藏键盘、退出打工模式、关闭窗口和退出应用时停止并清空高亮。
- Release workflow 继续使用 `--add-data "assets;assets"` 打包全部资源，并在 `py_compile` 清单中包含键盘跟随相关模块。

关键接口：
- `KeyboardHook.start()` / `KeyboardHook.stop()`：可重复调用的键盘监听启停入口，事件通过 `key_event` Signal 回到 Qt 主线程。
- `WindowsLowLevelKeyboardBackend`：Windows `WH_KEYBOARD_LL` 后端，回调后始终继续传递输入，不吞按键。
- `key_asset_for_event(vk_code, scan_code, extended)`：把原生键盘事件映射到 BongoCat 按键素材。
- `PetKeyboardOverlay.set_key_pressed(...)` / `clear_pressed_keys()`：维护当前按下按键集合并刷新叠层。
- `PetWindow._refresh_keyboard_follow()`：统一判断 `work_mode and keyboard_visible`，负责静态小狗、键盘叠层和 hook 生命周期。
- `PetWindow._toggle_keyboard()` / `_enter_work()` / `_exit_work()`：键盘显示、打工模式进入和退出的用户入口。

关键资产文件：
- `assets/generated/typing_dog_halfbody_left45.png`：打工模式显示键盘时的小狗静态图。
- `assets/png/keyboard/background.png`：BongoCat 键盘底图。
- `assets/png/keyboard/left-keys/*.png`：主键盘、数字、修饰键等左侧键位高亮素材。
- `assets/png/keyboard/right-keys/*.png`：方向键等右侧键位高亮素材。
- `assets/png/keyboard/README.md`：BongoCat 键盘素材来源与 MIT 许可说明。

当前问题：
- 自动化测试使用假 hook 后端，不会安装真实系统级键盘 hook；全局按键高亮仍需要在 Windows 桌面环境手动验收。
- 工作树中存在未跟踪的 `LineDogPet.spec`、`run_*.log` 和额外 generated 图片，本任务不处理这些文件。

下一步：
- 运行完整回归测试、编译检查和 `git diff --check`。
- 在真实 Windows 桌面手动运行 `C:\Users\ZYKJ\miniforge3\python.exe main.py`，检查打工模式、显示键盘、按键高亮、隐藏键盘、退出打工模式、托盘退出和单实例行为。
- 如需发布，继续确认 GitHub Actions Release 产物包含 `assets/generated/typing_dog_halfbody_left45.png` 和 `assets/png/keyboard/`。

禁止改动：
- 不要写入真实用户数据路径做测试；持久化仍应写入 `%APPDATA%\LineDogPet\pet_data.json`。
- 不要让 hook 拦截、吞掉、改写或重新映射系统键盘输入。
- 不要在非“打工模式 + 显示键盘”状态启动键盘 hook。
- 不要把当前按下按键集合、hook 运行状态等临时运行态写入 JSON。
- 不要删除或覆盖未跟踪的 `LineDogPet.spec`、`run_*.log` 或额外 generated 图片。
