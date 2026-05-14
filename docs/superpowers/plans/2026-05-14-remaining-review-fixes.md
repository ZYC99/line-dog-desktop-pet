# Remaining Review Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the remaining review findings so work mode, tray icon setup, persisted state loading, and single-instance startup behave reliably.

**Architecture:** Keep `PetStats` as the persisted user preference and normal-position source of truth. Keep work-mode runtime effects inside `PetWindow`, use small helper methods for save-position syncing and effective window flags, and expose unit-testable helper functions in `main.py` for single-instance startup.

**Tech Stack:** Python 3.11, PySide6, `unittest`, existing `test_regressions.py`.

---

## File Structure

- Modify `pet_window.py`: work-mode preference isolation, normal-position save helper, independent tray icon movie.
- Modify `pet_stats.py`: optional data-file injection for tests and typed/clamped JSON loading.
- Modify `main.py`: testable single-instance helper functions with stale server-name cleanup.
- Modify `test_regressions.py`: add regression tests for all remaining findings.
- Modify `docs/REVIEW_FINDINGS.md`: move fixed findings into the repaired section after implementation.

---

### Task 1: Preserve Normal Position And User Preferences In Work Mode

**Files:**
- Modify: `pet_window.py:100-113`, `pet_window.py:421-453`, `pet_window.py:531-543`
- Test: `test_regressions.py`

- [ ] **Step 1: Write failing tests**

Append these tests to `PetWindowBehaviorTests` in `test_regressions.py`:

```python
def test_work_mode_restores_user_topmost_and_click_preferences(self):
    from PySide6.QtCore import Qt
    from pet_window import PetWindow

    window = PetWindow()
    self.addCleanup(window.close)
    window.stats.topmost = False
    window.stats.click_through = False
    window._apply_topmost()
    window._apply_click_through()

    window._toggle_work()

    self.assertTrue(window.stats.work_mode)
    self.assertFalse(window.stats.topmost)
    self.assertFalse(window.stats.click_through)
    self.assertTrue(window.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents))

    window._toggle_work()

    self.assertFalse(window.stats.work_mode)
    self.assertFalse(window.stats.topmost)
    self.assertFalse(window.stats.click_through)
    self.assertFalse(window.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents))

def test_work_mode_does_not_overwrite_normal_saved_position(self):
    from pet_window import PetWindow

    window = PetWindow()
    self.addCleanup(window.close)
    window.move(123, 234)

    window._toggle_work()
    window.move(300, 300)
    window._sync_position_for_save()

    self.assertEqual(window.stats.x, 123)
    self.assertEqual(window.stats.y, 234)
```

- [ ] **Step 2: Verify tests fail**

Run:

```powershell
$env:QT_QPA_PLATFORM='offscreen'; python -m unittest test_regressions.PetWindowBehaviorTests.test_work_mode_restores_user_topmost_and_click_preferences test_regressions.PetWindowBehaviorTests.test_work_mode_does_not_overwrite_normal_saved_position
```

Expected: both fail because work mode currently mutates `stats.topmost`, mutates `stats.click_through`, and `_sync_position_for_save` does not exist.

- [ ] **Step 3: Implement effective window flags**

In `pet_window.py`, change `_apply_topmost` and `_apply_click_through` to use effective runtime state:

```python
def _effective_topmost(self):
    return self.stats.topmost or self.stats.work_mode

def _effective_click_through(self):
    return self.stats.click_through or self.stats.work_mode

def _apply_topmost(self):
    flags = self.windowFlags()
    if self._effective_topmost():
        flags |= Qt.WindowType.WindowStaysOnTopHint
    else:
        flags &= ~Qt.WindowType.WindowStaysOnTopHint
    self.setWindowFlags(flags)
    self.show()

def _apply_click_through(self):
    self.setAttribute(
        Qt.WidgetAttribute.WA_TransparentForMouseEvents,
        self._effective_click_through(),
    )
```

- [ ] **Step 4: Implement normal-position syncing**

Add this helper near lifecycle methods in `pet_window.py`:

```python
def _sync_position_for_save(self):
    if not self.stats.work_mode:
        self.stats.x = self.x()
        self.stats.y = self.y()
```

Update `_show_menu`, `closeEvent`, and `_quit` to call `_sync_position_for_save()` instead of assigning `stats.x/y` directly.

- [ ] **Step 5: Stop mutating user preferences in work mode**

Change `_enter_work`:

```python
def _enter_work(self):
    self._sync_position_for_save()
    self._work_prev_size = self.stats.pet_size
    self._set_size(WORK_MODE_SIZE)
    self.stats.pet_size = self._work_prev_size
    screen = QApplication.primaryScreen().availableGeometry()
    self.move(
        screen.width() - WORK_MODE_SIZE - WORK_MARGIN_RIGHT,
        screen.height() - WORK_MODE_SIZE - WORK_MARGIN_BOTTOM,
    )
    self._apply_click_through()
    self._apply_topmost()
    self._setup_tray_menu()
    if self.anim.has_category("work"):
        self._play("work")
```

Change `_exit_work`:

```python
def _exit_work(self):
    self._set_size(self.stats.pet_size)
    self._apply_click_through()
    self._apply_topmost()
    self._setup_tray_menu()
    self.move(self.stats.x, self.stats.y)
    self._clamp_window_position()
    self._play("idle")
```

- [ ] **Step 6: Verify Task 1**

Run:

```powershell
$env:QT_QPA_PLATFORM='offscreen'; python -m unittest test_regressions.PetWindowBehaviorTests.test_work_mode_restores_user_topmost_and_click_preferences test_regressions.PetWindowBehaviorTests.test_work_mode_does_not_overwrite_normal_saved_position
```

Expected: both tests pass.

---

### Task 2: Use An Independent QMovie For The Tray Icon

**Files:**
- Modify: `pet_window.py:465-487`
- Test: `test_regressions.py`

- [ ] **Step 1: Write failing test**

Append this test to `PetWindowBehaviorTests`:

```python
def test_tray_icon_setup_does_not_stop_current_idle_movie(self):
    from PySide6.QtGui import QMovie
    from pet_window import PetWindow

    window = PetWindow()
    self.addCleanup(window.close)
    idle_movie = window.anim._movies["idle"][0]
    window.label.setMovie(idle_movie)
    idle_movie.start()

    window._setup_tray()
    window._set_tray_icon(window._tray_icon_movie)

    self.assertIsNot(window._tray_icon_movie, idle_movie)
    self.assertEqual(idle_movie.state(), QMovie.MovieState.Running)
```

- [ ] **Step 2: Verify test fails**

Run:

```powershell
$env:QT_QPA_PLATFORM='offscreen'; python -m unittest test_regressions.PetWindowBehaviorTests.test_tray_icon_setup_does_not_stop_current_idle_movie
```

Expected: fail because `_tray_icon_movie` does not exist and current code reuses the shared idle movie.

- [ ] **Step 3: Implement independent tray movie**

Change `_setup_tray`:

```python
def _setup_tray(self):
    self.tray = QSystemTrayIcon(self)
    idle_gifs = self.anim._movies.get("idle", [])
    if idle_gifs:
        self._tray_icon_movie = QMovie(idle_gifs[0].fileName())
        self._tray_icon_movie.setCacheMode(QMovie.CacheMode.CacheAll)
        self._tray_icon_movie.start()
        self._tray_icon_movie.jumpToFrame(0)
        QTimer.singleShot(100, lambda: self._set_tray_icon(self._tray_icon_movie))
    else:
        self.tray.setIcon(self.style().standardIcon(
            self.style().StandardPixmap.SP_ComputerIcon))
    self.tray.setToolTip("线条小狗")
    self._setup_tray_menu()
    self.tray.show()
```

Keep `_set_tray_icon` as the only place that stops the tray-only movie.

- [ ] **Step 4: Verify Task 2**

Run:

```powershell
$env:QT_QPA_PLATFORM='offscreen'; python -m unittest test_regressions.PetWindowBehaviorTests.test_tray_icon_setup_does_not_stop_current_idle_movie
```

Expected: pass.

---

### Task 3: Validate Persisted JSON Types And Ranges

**Files:**
- Modify: `pet_stats.py:7-131`
- Test: `test_regressions.py`

- [ ] **Step 1: Write failing tests**

Add a new test class to `test_regressions.py`:

```python
class PetStatsLoadTests(unittest.TestCase):
    def test_load_clamps_and_coerces_persisted_values(self):
        import json
        from config import SIZE_MAX, SIZE_MIN
        from pet_stats import PetStats

        with tempfile.TemporaryDirectory() as data_dir:
            data_file = os.path.join(data_dir, "pet_data.json")
            with open(data_file, "w", encoding="utf-8") as f:
                json.dump({
                    "hunger": "150",
                    "cleanliness": "-5",
                    "affection": "bad",
                    "x": "12",
                    "y": None,
                    "topmost": "false",
                    "click_through": "yes",
                    "work_mode": 1,
                    "pet_size": SIZE_MAX + 500,
                    "last_feed": "bad",
                    "last_bath": 123.5,
                }, f)

            stats = PetStats(data_file=data_file, data_dir=data_dir)

        self.assertEqual(stats.hunger, 100)
        self.assertEqual(stats.cleanliness, 0)
        self.assertEqual(stats.affection, 50)
        self.assertEqual(stats.x, 12)
        self.assertEqual(stats.y, 500)
        self.assertFalse(stats.topmost)
        self.assertTrue(stats.click_through)
        self.assertTrue(stats.work_mode)
        self.assertEqual(stats.pet_size, SIZE_MAX)
        self.assertIsNone(stats._last_action["feed"])
        self.assertEqual(stats._last_action["bath"], 123.5)

    def test_corrupt_json_loads_defaults_without_crashing(self):
        from pet_stats import PetStats

        with tempfile.TemporaryDirectory() as data_dir:
            data_file = os.path.join(data_dir, "pet_data.json")
            with open(data_file, "w", encoding="utf-8") as f:
                f.write("{not valid json")

            stats = PetStats(data_file=data_file, data_dir=data_dir)

        self.assertEqual(stats.hunger, 100)
        self.assertEqual(stats.cleanliness, 100)
        self.assertEqual(stats.affection, 50)
```

- [ ] **Step 2: Verify tests fail**

Run:

```powershell
$env:QT_QPA_PLATFORM='offscreen'; python -m unittest test_regressions.PetStatsLoadTests
```

Expected: fail because `PetStats.__init__` does not accept `data_file` and data is not coerced.

- [ ] **Step 3: Add injectable data paths**

Change the `PetStats` constructor:

```python
def __init__(self, data_file=DATA_FILE, data_dir=DATA_DIR):
    self.data_file = data_file
    self.data_dir = data_dir
    ...
```

Update `save` and `_load` to use `self.data_dir` and `self.data_file`.

- [ ] **Step 4: Add value coercion helpers**

Add helpers inside `PetStats`:

```python
def _coerce_number(self, value, default, minimum, maximum):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, value))

def _coerce_int(self, value, default, minimum, maximum):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, value))

def _coerce_bool(self, value, default):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in ("true", "1", "yes", "on"):
            return True
        if normalized in ("false", "0", "no", "off"):
            return False
    return default

def _coerce_timestamp(self, value):
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if value >= 0 else None
```

- [ ] **Step 5: Use helpers in `_load`**

Replace raw `data.get(...)` assignments:

```python
self.hunger = self._coerce_number(data.get("hunger"), 100, 0, 100)
self.cleanliness = self._coerce_number(data.get("cleanliness"), 100, 0, 100)
self.affection = self._coerce_number(data.get("affection"), 50, 0, 100)
self.x = self._coerce_int(data.get("x"), 800, 0, 100000)
self.y = self._coerce_int(data.get("y"), 500, 0, 100000)
self.topmost = self._coerce_bool(data.get("topmost"), True)
self.click_through = self._coerce_bool(data.get("click_through"), False)
self.work_mode = self._coerce_bool(data.get("work_mode"), False)
self.pet_size = self._coerce_int(data.get("pet_size"), WINDOW_SIZE, SIZE_MIN, SIZE_MAX)
self._last_action["feed"] = self._coerce_timestamp(data.get("last_feed"))
self._last_action["bath"] = self._coerce_timestamp(data.get("last_bath"))
self._last_action["greet"] = self._coerce_timestamp(data.get("last_greet"))
self._last_action["play"] = self._coerce_timestamp(data.get("last_play"))
```

Import `SIZE_MIN` and `SIZE_MAX` from `config`.

- [ ] **Step 6: Verify Task 3**

Run:

```powershell
$env:QT_QPA_PLATFORM='offscreen'; python -m unittest test_regressions.PetStatsLoadTests
```

Expected: pass.

---

### Task 4: Make Single-Instance Startup Robust

**Files:**
- Modify: `main.py:1-22`
- Test: `test_regressions.py`

- [ ] **Step 1: Write failing tests**

Add this test class to `test_regressions.py`:

```python
class SingleInstanceTests(unittest.TestCase):
    def test_start_local_server_removes_stale_name_and_retries(self):
        import main

        calls = []

        class FakeServer:
            attempts = 0

            def listen(self, name):
                calls.append(("listen", name))
                FakeServer.attempts += 1
                return FakeServer.attempts == 2

        def remove_server(name):
            calls.append(("remove", name))
            return True

        server = main.start_local_server(
            name="LineDogPetTest",
            server_factory=FakeServer,
            remove_server=remove_server,
        )

        self.assertIsInstance(server, FakeServer)
        self.assertEqual(calls, [
            ("listen", "LineDogPetTest"),
            ("remove", "LineDogPetTest"),
            ("listen", "LineDogPetTest"),
        ])

    def test_start_local_server_raises_if_retry_fails(self):
        import main

        class FakeServer:
            def listen(self, name):
                return False

        with self.assertRaises(RuntimeError):
            main.start_local_server(
                name="LineDogPetTest",
                server_factory=FakeServer,
                remove_server=lambda name: True,
            )
```

- [ ] **Step 2: Verify tests fail**

Run:

```powershell
python -m unittest test_regressions.SingleInstanceTests
```

Expected: fail because `start_local_server` does not exist.

- [ ] **Step 3: Refactor `main.py`**

Use this structure:

```python
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from pet_window import PetWindow

SERVER_NAME = "LineDogPet"

def is_instance_running(name=SERVER_NAME, socket_factory=QLocalSocket):
    socket = socket_factory()
    socket.connectToServer(name)
    return socket.waitForConnected(500)

def start_local_server(name=SERVER_NAME, server_factory=QLocalServer, remove_server=QLocalServer.removeServer):
    server = server_factory()
    if server.listen(name):
        return server
    remove_server(name)
    server = server_factory()
    if server.listen(name):
        return server
    raise RuntimeError(f"无法启动本地单实例服务: {name}")

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    if is_instance_running():
        print("LineDogPet 已在运行")
        sys.exit(0)

    server = start_local_server()
    window = PetWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
```

Keep the `server` local variable in `main()` so the `QLocalServer` object stays alive for the app lifetime.

- [ ] **Step 4: Verify Task 4**

Run:

```powershell
python -m unittest test_regressions.SingleInstanceTests
```

Expected: pass.

---

### Task 5: Update Review Record And Run Full Verification

**Files:**
- Modify: `docs/REVIEW_FINDINGS.md`

- [ ] **Step 1: Update findings record**

Move these entries from “其余发现” into “已修复”:

```markdown
- 打工模式会覆盖用户偏好和普通坐标
- 托盘图标复用 idle `QMovie` 可能影响当前动画
- JSON 持久化加载缺少类型和值校验
- 单实例服务监听失败未处理
```

For each entry, add one sentence describing the implemented fix.

- [ ] **Step 2: Run all regression tests**

Run:

```powershell
$env:QT_QPA_PLATFORM='offscreen'; python -m unittest test_regressions.py
```

Expected: all tests pass.

- [ ] **Step 3: Compile all Python files**

Run:

```powershell
python -m py_compile main.py config.py pet_stats.py pet_animation.py pet_menu.py pet_window.py test_regressions.py
```

Expected: exit code 0.

- [ ] **Step 4: Check diff formatting**

Run:

```powershell
git diff --check
```

Expected: exit code 0. Existing LF/CRLF warnings are acceptable if there are no whitespace errors.

- [ ] **Step 5: Manual smoke test**

Run:

```powershell
$env:QT_QPA_PLATFORM='offscreen'; python main.py
```

Expected in offscreen mode: no import or startup exception before the event loop starts. Stop the process manually after startup.

Manual desktop verification outside offscreen:

```powershell
python main.py
```

Check:
- Right-click menu opens.
- Size presets and slider remain synchronized.
- Ctrl + mouse wheel resizes the pet and keeps it onscreen.
- Enter work mode, exit from tray, and original normal position returns.
- User topmost/click-through preferences survive a work-mode round trip.
- A second app launch exits with “LineDogPet 已在运行”.

---

## Self-Review

- Spec coverage: covers all remaining review findings recorded in `docs/REVIEW_FINDINGS.md`.
- Placeholder scan: no placeholder tasks remain; each task has exact files, test code, implementation code, and commands.
- Type consistency: helper names used by tests match implementation steps: `_sync_position_for_save`, `start_local_server`, `data_file`, and `data_dir`.
