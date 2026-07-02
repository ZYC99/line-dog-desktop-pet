import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


ROOT = Path(__file__).resolve().parent


class ConfigPathTests(unittest.TestCase):
    def test_frozen_assets_use_pyinstaller_meipass(self):
        config_path = ROOT / "config.py"
        with tempfile.TemporaryDirectory() as bundle_dir:
            original_frozen = getattr(sys, "frozen", None)
            original_meipass = getattr(sys, "_MEIPASS", None)
            sys.frozen = True
            sys._MEIPASS = bundle_dir
            try:
                spec = importlib.util.spec_from_file_location("config_under_test", config_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            finally:
                if original_frozen is None:
                    delattr(sys, "frozen")
                else:
                    sys.frozen = original_frozen
                if original_meipass is None:
                    delattr(sys, "_MEIPASS")
                else:
                    sys._MEIPASS = original_meipass

        self.assertEqual(
            module.ASSETS_DIR,
            os.path.join(bundle_dir, "assets", "gif"),
        )

    def test_default_size_is_180px(self):
        import config

        self.assertEqual(config.WINDOW_SIZE, 180)
        self.assertEqual(config.SIZE_PRESETS["中"], 180)

    def test_work_mode_size_is_135px(self):
        import config

        self.assertEqual(config.WORK_MODE_SIZE, 135)

    def test_keyboard_assets_path_uses_pyinstaller_meipass(self):
        config_path = ROOT / "config.py"
        with tempfile.TemporaryDirectory() as bundle_dir:
            original_frozen = getattr(sys, "frozen", None)
            original_meipass = getattr(sys, "_MEIPASS", None)
            sys.frozen = True
            sys._MEIPASS = bundle_dir
            try:
                spec = importlib.util.spec_from_file_location("config_keyboard_under_test", config_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            finally:
                if original_frozen is None:
                    delattr(sys, "frozen")
                else:
                    sys.frozen = original_frozen
                if original_meipass is None:
                    delattr(sys, "_MEIPASS")
                else:
                    sys._MEIPASS = original_meipass

        self.assertEqual(
            module.KEYBOARD_ASSETS_DIR,
            os.path.join(bundle_dir, "assets", "png", "keyboard"),
        )

    def test_typing_dog_path_uses_pyinstaller_meipass(self):
        config_path = ROOT / "config.py"
        with tempfile.TemporaryDirectory() as bundle_dir:
            original_frozen = getattr(sys, "frozen", None)
            original_meipass = getattr(sys, "_MEIPASS", None)
            sys.frozen = True
            sys._MEIPASS = bundle_dir
            try:
                spec = importlib.util.spec_from_file_location("config_typing_dog_under_test", config_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
            finally:
                if original_frozen is None:
                    delattr(sys, "frozen")
                else:
                    sys.frozen = original_frozen
                if original_meipass is None:
                    delattr(sys, "_MEIPASS")
                else:
                    sys._MEIPASS = original_meipass

        self.assertEqual(
            module.TYPING_DOG_IMAGE,
            os.path.join(bundle_dir, "assets", "generated", "typing_dog_halfbody_left45.png"),
        )


class ReleaseWorkflowTests(unittest.TestCase):
    def test_local_build_script_does_not_install_dependencies(self):
        content = (ROOT / "build.bat").read_text(encoding="utf-8")

        self.assertNotIn("pip install", content.lower())
        self.assertIn(".venv\\Scripts\\python.exe", content)
        self.assertIn("-m PyInstaller", content)

    def test_local_build_script_uses_project_icon(self):
        content = (ROOT / "build.bat").read_text(encoding="utf-8")
        icon = ROOT / "assets" / "icon.ico"

        self.assertTrue(icon.is_file())
        self.assertEqual(icon.read_bytes()[:4], b"\x00\x00\x01\x00")
        self.assertIn('--icon "assets\\icon.ico"', content)

    def test_release_workflow_installs_requirements_and_builds_release(self):
        content = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

        self.assertIn("pip install -r requirements.txt", content)
        self.assertIn("python -m PyInstaller", content)
        self.assertIn('--icon "assets\\icon.ico"', content)
        self.assertIn("pet_keyboard_overlay.py", content)
        self.assertIn("keyboard_hook.py", content)
        self.assertIn('--add-data "assets;assets"', content)
        self.assertIn("softprops/action-gh-release", content)


class StartupConfigTests(unittest.TestCase):
    def test_builds_startup_command_for_frozen_and_dev_modes(self):
        from pet_startup import build_startup_command

        self.assertEqual(
            build_startup_command(
                executable=r"C:\Apps\LineDogPet.exe",
                script_path=r"D:\repo\main.py",
                frozen=True,
            ),
            r'"C:\Apps\LineDogPet.exe"',
        )
        self.assertEqual(
            build_startup_command(
                executable=r"C:\Python311\python.exe",
                script_path=r"D:\repo\main.py",
                frozen=False,
            ),
            r'"C:\Python311\python.exe" "D:\repo\main.py"',
        )

    def test_startup_registry_toggle_uses_current_user_run_key(self):
        from config import STARTUP_KEY, STARTUP_NAME
        from pet_startup import is_startup_enabled, set_startup_enabled

        class FakeWinreg:
            HKEY_CURRENT_USER = "HKCU"
            KEY_READ = 1
            KEY_SET_VALUE = 2
            REG_SZ = 1

            def __init__(self):
                self.values = {}
                self.opened = []

            def OpenKey(self, root, path, reserved=0, access=0):
                self.opened.append((root, path, access))
                return self

            def CreateKey(self, root, path):
                self.opened.append((root, path, "create"))
                return self

            def QueryValueEx(self, key, name):
                if name not in self.values:
                    raise FileNotFoundError(name)
                return self.values[name], self.REG_SZ

            def SetValueEx(self, key, name, reserved, value_type, value):
                self.values[name] = value

            def DeleteValue(self, key, name):
                if name not in self.values:
                    raise FileNotFoundError(name)
                del self.values[name]

            def CloseKey(self, key):
                pass

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        registry = FakeWinreg()

        self.assertFalse(is_startup_enabled(registry=registry))

        set_startup_enabled(True, registry=registry, command="LineDogPet.exe")

        self.assertTrue(is_startup_enabled(registry=registry))
        self.assertEqual(registry.values[STARTUP_NAME], "LineDogPet.exe")
        self.assertIn((registry.HKEY_CURRENT_USER, STARTUP_KEY, registry.KEY_SET_VALUE), registry.opened)

        set_startup_enabled(False, registry=registry)

        self.assertFalse(is_startup_enabled(registry=registry))


class KeyboardOverlayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])

    def test_keyboard_overlay_scales_to_model_aspect_ratio(self):
        from PySide6.QtCore import QSize
        from pet_keyboard_overlay import PetKeyboardOverlay

        overlay = PetKeyboardOverlay()
        self.addCleanup(overlay.close)

        overlay.set_keyboard_width(204)

        self.assertEqual(overlay.size(), QSize(204, 118))

    def test_keyboard_overlay_tracks_and_renders_multiple_pressed_keys(self):
        from PySide6.QtCore import QSize
        from pet_keyboard_overlay import PetKeyboardOverlay

        overlay = PetKeyboardOverlay()
        self.addCleanup(overlay.close)
        overlay.set_keyboard_width(204)

        overlay.set_key_pressed(0x41, 0, False, True)
        pixmap = overlay._background_label.pixmap()
        self.assertIsNotNone(pixmap)
        self.assertFalse(pixmap.isNull())

        overlay.set_key_pressed(0x10, 0x2A, False, True)
        self.assertEqual(
            overlay.pressed_assets,
            {("left-keys", "KeyA.png"), ("left-keys", "ShiftLeft.png")},
        )
        pixmap = overlay._background_label.pixmap()
        self.assertIsNotNone(pixmap)
        self.assertFalse(pixmap.isNull())

        overlay.set_key_pressed(0x41, 0, False, True)
        self.assertEqual(len(overlay.pressed_assets), 2)

        overlay.set_key_pressed(0x41, 0, False, False)
        self.assertEqual(overlay.pressed_assets, {("left-keys", "ShiftLeft.png")})
        pixmap = overlay._background_label.pixmap()
        self.assertIsNotNone(pixmap)
        self.assertFalse(pixmap.isNull())

        overlay.clear_pressed_keys()
        self.assertEqual(overlay.pressed_assets, set())
        pixmap = overlay._background_label.pixmap()
        self.assertIsNotNone(pixmap)
        self.assertFalse(pixmap.isNull())
        self.assertEqual(overlay.size(), QSize(204, 118))


class KeyboardMappingTests(unittest.TestCase):
    def test_maps_letters_and_main_keyboard_digits(self):
        from pet_keyboard_overlay import key_asset_for_event

        self.assertEqual(key_asset_for_event(0x41, 0, False), ("left-keys", "KeyA.png"))
        self.assertEqual(key_asset_for_event(0x5A, 0, False), ("left-keys", "KeyZ.png"))
        self.assertEqual(key_asset_for_event(0x30, 0, False), ("left-keys", "Num0.png"))
        self.assertEqual(key_asset_for_event(0x39, 0, False), ("left-keys", "Num9.png"))

    def test_maps_arrow_keys(self):
        from pet_keyboard_overlay import key_asset_for_event

        expected = {
            0x25: ("right-keys", "LeftArrow.png"),
            0x26: ("right-keys", "UpArrow.png"),
            0x27: ("right-keys", "RightArrow.png"),
            0x28: ("right-keys", "DownArrow.png"),
        }
        for vk_code, asset in expected.items():
            with self.subTest(vk_code=vk_code):
                self.assertEqual(key_asset_for_event(vk_code, 0, True), asset)

    def test_distinguishes_left_and_right_shift(self):
        from pet_keyboard_overlay import key_asset_for_event

        self.assertEqual(key_asset_for_event(0x10, 0x2A, False), ("left-keys", "ShiftLeft.png"))
        self.assertEqual(key_asset_for_event(0x10, 0x36, False), ("left-keys", "ShiftRight.png"))
        self.assertEqual(key_asset_for_event(0x10, 0, False), ("left-keys", "Shift.png"))
        self.assertEqual(key_asset_for_event(0xA0, 0x36, False), ("left-keys", "ShiftLeft.png"))
        self.assertEqual(key_asset_for_event(0xA1, 0x2A, False), ("left-keys", "ShiftRight.png"))

    def test_distinguishes_left_and_right_control(self):
        from pet_keyboard_overlay import key_asset_for_event

        self.assertEqual(key_asset_for_event(0x11, 0, False), ("left-keys", "ControlLeft.png"))
        self.assertEqual(key_asset_for_event(0x11, 0, True), ("left-keys", "ControlRight.png"))
        self.assertEqual(key_asset_for_event(0xA2, 0, True), ("left-keys", "ControlLeft.png"))
        self.assertEqual(key_asset_for_event(0xA3, 0, False), ("left-keys", "ControlRight.png"))

    def test_distinguishes_left_and_right_alt(self):
        from pet_keyboard_overlay import key_asset_for_event

        self.assertEqual(key_asset_for_event(0x12, 0, False), ("left-keys", "Alt.png"))
        self.assertEqual(key_asset_for_event(0x12, 0, True), ("left-keys", "AltGr.png"))
        self.assertEqual(key_asset_for_event(0xA4, 0, True), ("left-keys", "Alt.png"))
        self.assertEqual(key_asset_for_event(0xA5, 0, False), ("left-keys", "AltGr.png"))

    def test_maps_supported_special_keys(self):
        from pet_keyboard_overlay import key_asset_for_event

        expected = {
            0x08: "Backspace.png",
            0x09: "Tab.png",
            0x0D: "Return.png",
            0x14: "CapsLock.png",
            0x1B: "Escape.png",
            0x20: "Space.png",
            0x2E: "Delete.png",
            0x5B: "Meta.png",
            0x5C: "Meta.png",
            0xBF: "Slash.png",
            0xC0: "BackQuote.png",
        }
        for vk_code, filename in expected.items():
            with self.subTest(vk_code=vk_code):
                self.assertEqual(
                    key_asset_for_event(vk_code, 0, False),
                    ("left-keys", filename),
                )

    def test_does_not_map_function_or_unknown_keys(self):
        from pet_keyboard_overlay import key_asset_for_event

        self.assertIsNone(key_asset_for_event(0x70, 0, False))
        self.assertIsNone(key_asset_for_event(0x7B, 0, False))
        self.assertIsNone(key_asset_for_event(0xFF, 0, False))

    def test_every_supported_mapping_uses_an_existing_asset(self):
        from config import KEYBOARD_ASSETS_DIR
        from pet_keyboard_overlay import key_asset_for_event

        events = [(vk_code, 0, False) for vk_code in range(0x41, 0x5B)]
        events += [(vk_code, 0, False) for vk_code in range(0x30, 0x3A)]
        events += [(vk_code, 0, True) for vk_code in range(0x25, 0x29)]
        events += [
            (vk_code, 0, False)
            for vk_code in (0x08, 0x09, 0x0D, 0x14, 0x1B, 0x20, 0x2E, 0x5B, 0x5C, 0xBF, 0xC0)
        ]
        events += [
            (0x10, 0x2A, False),
            (0x10, 0x36, False),
            (0x10, 0, False),
            (0xA0, 0x36, False),
            (0xA1, 0x2A, False),
            (0x11, 0, False),
            (0x11, 0, True),
            (0xA2, 0, True),
            (0xA3, 0, False),
            (0x12, 0, False),
            (0x12, 0, True),
            (0xA4, 0, True),
            (0xA5, 0, False),
        ]

        for event in events:
            with self.subTest(event=event):
                asset = key_asset_for_event(*event)
                self.assertIsNotNone(asset)
                subdirectory, filename = asset
                self.assertTrue(
                    os.path.isfile(os.path.join(KEYBOARD_ASSETS_DIR, subdirectory, filename)),
                    asset,
                )


class KeyboardHookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])

    def test_emits_backend_key_events_and_start_stop_are_idempotent(self):
        from keyboard_hook import KeyboardHook

        class FakeBackend:
            def __init__(self):
                self.started = 0
                self.stopped = 0
                self.callback = None

            def start(self, callback):
                self.started += 1
                self.callback = callback
                return True

            def stop(self):
                self.stopped += 1

        backend = FakeBackend()
        hook = KeyboardHook(backend=backend)
        events = []
        hook.key_event.connect(lambda *args: events.append(args))

        self.assertFalse(hook.running)
        self.assertTrue(hook.start())
        self.assertTrue(hook.running)
        self.assertTrue(hook.start())
        self.assertEqual(backend.started, 1)

        backend.callback(0x41, 0x1E, False, True)
        self.app.processEvents()

        self.assertEqual(events, [(0x41, 0x1E, False, True)])

        hook.stop()
        self.assertFalse(hook.running)
        hook.stop()
        self.assertEqual(backend.stopped, 1)

    def test_start_failure_leaves_hook_not_running(self):
        from keyboard_hook import KeyboardHook

        class FailingBackend:
            def __init__(self):
                self.started = 0
                self.stopped = 0

            def start(self, callback):
                self.started += 1
                return False

            def stop(self):
                self.stopped += 1

        backend = FailingBackend()
        hook = KeyboardHook(backend=backend)

        self.assertFalse(hook.start())
        self.assertFalse(hook.running)
        self.assertEqual(backend.started, 1)
        hook.stop()
        self.assertEqual(backend.stopped, 0)

    def test_stop_failure_keeps_hook_running_and_prevents_duplicate_start(self):
        from keyboard_hook import KeyboardHook

        class StopFailingBackend:
            def __init__(self):
                self.started = 0
                self.stopped = 0

            def start(self, callback):
                self.started += 1
                return True

            def stop(self):
                self.stopped += 1
                return False

        backend = StopFailingBackend()
        hook = KeyboardHook(backend=backend)

        self.assertTrue(hook.start())
        hook.stop()

        self.assertTrue(hook.running)
        self.assertEqual(backend.stopped, 1)
        self.assertTrue(hook.start())
        self.assertEqual(backend.started, 1)

    def test_native_backend_stop_failure_keeps_backend_started(self):
        from keyboard_hook import WindowsLowLevelKeyboardBackend

        class StillAliveThread:
            joined = False

            def is_alive(self):
                return True

            def join(self, timeout=None):
                self.joined = True

        backend = WindowsLowLevelKeyboardBackend()
        thread = StillAliveThread()
        backend._thread = thread
        backend._started = True

        self.assertFalse(backend.stop())
        self.assertTrue(thread.joined)
        self.assertTrue(backend._started)
        self.assertIs(backend._thread, thread)


class PetWindowBehaviorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])

    def test_stale_interaction_end_does_not_clear_current_interaction(self):
        from pet_window import PetWindow

        window = PetWindow()
        self.addCleanup(window.close)
        window._interaction_in_progress = True
        window._interaction_id = 2

        window._end_interaction(1)

        self.assertTrue(window._interaction_in_progress)

    def test_tray_menu_can_disable_click_through_and_work_mode(self):
        from pet_window import PetWindow

        window = PetWindow()
        self.addCleanup(window.close)
        window.stats.click_through = True
        window.stats.work_mode = True
        window._setup_tray_menu()

        actions = {
            action.text(): action
            for action in window.tray.contextMenu().actions()
            if action.text()
        }

        self.assertIn("关闭鼠标穿透", actions)
        self.assertIn("退出打工模式", actions)

    def test_enabling_click_through_refreshes_tray_recovery_action(self):
        from pet_window import PetWindow

        window = PetWindow()
        self.addCleanup(window.close)
        window.stats.click_through = False
        window._setup_tray_menu()

        window._toggle_click_through()

        actions = {
            action.text(): action
            for action in window.tray.contextMenu().actions()
            if action.text()
        }

        self.assertIn("关闭鼠标穿透", actions)

    def test_size_preset_button_updates_slider(self):
        from PySide6.QtWidgets import QPushButton, QSlider
        from pet_menu import PetMenu

        class Stats:
            hunger = 100
            cleanliness = 100
            affection = 50
            work_mode = False
            topmost = True
            click_through = False
            pet_size = 180

            def can_do(self, action):
                return True

        sizes = []
        menu = PetMenu(Stats(), {"set_size": sizes.append})
        self.addCleanup(menu.close)
        slider = menu.findChild(QSlider)
        large_button = next(
            button for button in menu.findChildren(QPushButton)
            if button.text().startswith("大")
        )

        large_button.click()

        self.assertEqual(slider.value(), 270)
        self.assertEqual(sizes[-1], 270)

    def test_menu_shows_startup_toggle_state(self):
        from pet_menu import PetMenu

        class Stats:
            hunger = 100
            cleanliness = 100
            affection = 50
            work_mode = False
            topmost = True
            click_through = False
            pet_size = 180

            def can_do(self, action):
                return True

        menu = PetMenu(Stats(), {}, startup_enabled=True)
        self.addCleanup(menu.close)

        startup_actions = [
            action for action in menu.actions()
            if "开机自启" in action.text()
        ]

        self.assertEqual(len(startup_actions), 1)
        self.assertTrue(startup_actions[0].isCheckable())
        self.assertTrue(startup_actions[0].isChecked())

    def test_menu_shows_keyboard_toggle_state(self):
        from pet_menu import PetMenu

        class Stats:
            hunger = 100
            cleanliness = 100
            affection = 50
            work_mode = True
            topmost = True
            click_through = False
            keyboard_visible = True
            pet_size = 180

            def can_do(self, action):
                return True

        menu = PetMenu(Stats(), {})
        self.addCleanup(menu.close)

        keyboard_actions = [
            action for action in menu.actions()
            if "显示键盘" in action.text()
        ]

        self.assertEqual(len(keyboard_actions), 1)
        self.assertTrue(keyboard_actions[0].isCheckable())
        self.assertTrue(keyboard_actions[0].isChecked())

    def test_window_toggles_startup_setting(self):
        import pet_window
        from pet_window import PetWindow

        class FakeStartup:
            enabled = False

            def is_startup_enabled(self):
                return self.enabled

            def set_startup_enabled(self, enabled):
                self.enabled = enabled
                return True

        fake_startup = FakeStartup()
        original_startup = pet_window.pet_startup
        pet_window.pet_startup = fake_startup
        self.addCleanup(lambda: setattr(pet_window, "pet_startup", original_startup))

        window = PetWindow()
        self.addCleanup(window.close)

        window._toggle_startup()

        self.assertTrue(fake_startup.enabled)

    def test_work_mode_keyboard_overlay_extends_window_height(self):
        from config import KEYBOARD_WORK_MODE_PET_SIZE, KEYBOARD_WORK_MODE_WIDTH
        from pet_keyboard_overlay import keyboard_height_for_width
        from pet_window import PetWindow

        window = PetWindow()
        self.addCleanup(window.close)
        window.stats.work_mode = False
        window.stats.keyboard_visible = True

        window._toggle_work()

        self.assertTrue(window.keyboard_overlay.isVisible())
        self.assertEqual(window.width(), KEYBOARD_WORK_MODE_WIDTH)
        self.assertEqual(
            window.height(),
            KEYBOARD_WORK_MODE_PET_SIZE + keyboard_height_for_width(KEYBOARD_WORK_MODE_WIDTH),
        )
        self.assertEqual(window.label.width(), KEYBOARD_WORK_MODE_PET_SIZE)
        self.assertEqual(window.label.x(), (KEYBOARD_WORK_MODE_WIDTH - KEYBOARD_WORK_MODE_PET_SIZE) // 2)

    def test_keyboard_toggle_persists_preference(self):
        from pet_window import PetWindow

        window = PetWindow()
        self.addCleanup(window.close)
        window.stats.keyboard_visible = False

        window._toggle_keyboard()

        self.assertTrue(window.stats.keyboard_visible)

    def test_keyboard_visibility_switches_between_typing_dog_and_work_movie(self):
        from pet_window import PetWindow

        window = PetWindow()
        self.addCleanup(window.close)
        window.stats.work_mode = False
        window.stats.keyboard_visible = True

        window._toggle_work()

        self.assertIsNone(window.label.movie())
        self.assertFalse(window.label.pixmap().isNull())

        window._toggle_keyboard()

        self.assertIsNotNone(window.label.movie())
        self.assertEqual(window._state, "work")

    def test_missing_typing_dog_keeps_work_movie(self):
        import pet_window
        from pet_window import PetWindow

        original_image = pet_window.TYPING_DOG_IMAGE
        pet_window.TYPING_DOG_IMAGE = str(ROOT / "assets" / "generated" / "missing.png")
        self.addCleanup(lambda: setattr(pet_window, "TYPING_DOG_IMAGE", original_image))

        window = PetWindow()
        self.addCleanup(window.close)
        window.stats.work_mode = False
        window.stats.keyboard_visible = True

        window._toggle_work()

        self.assertIsNotNone(window.label.movie())
        self.assertEqual(window._state, "work")

    def test_keyboard_hook_lifecycle_follows_work_keyboard_visibility(self):
        import pet_window
        from PySide6.QtCore import QObject, Signal
        from pet_window import PetWindow

        class FakeKeyboardHook(QObject):
            key_event = Signal(int, int, bool, bool)

            def __init__(self):
                super().__init__()
                self.start_count = 0
                self.stop_count = 0
                self.running = False

            def start(self):
                if not self.running:
                    self.start_count += 1
                    self.running = True
                return True

            def stop(self):
                if self.running:
                    self.stop_count += 1
                    self.running = False

        fake = FakeKeyboardHook()
        window = PetWindow(keyboard_hook=fake)
        self.addCleanup(window.close)
        window.stats.work_mode = False
        window.stats.keyboard_visible = True

        window._toggle_work()

        self.assertEqual(fake.start_count, 1)
        self.assertTrue(fake.running)

        fake.key_event.emit(0x41, 0x1E, False, True)
        self.app.processEvents()

        self.assertIn(("left-keys", "KeyA.png"), window.keyboard_overlay.pressed_assets)

        window._toggle_keyboard()

        self.assertEqual(fake.stop_count, 1)
        self.assertFalse(fake.running)
        self.assertEqual(window.keyboard_overlay.pressed_assets, set())
        self.assertIsNotNone(window.label.movie())
        self.assertEqual(window._state, "work")

        window._toggle_keyboard()

        self.assertEqual(fake.start_count, 2)
        self.assertTrue(fake.running)

        fake.key_event.emit(0x41, 0x1E, False, True)
        self.app.processEvents()

        window._toggle_work()

        self.assertEqual(fake.stop_count, 2)
        self.assertFalse(fake.running)
        self.assertEqual(window.keyboard_overlay.pressed_assets, set())

        window._toggle_work()
        self.assertEqual(fake.start_count, 3)

        window.close()

        self.assertEqual(fake.stop_count, 3)
        window.close()
        self.assertEqual(fake.stop_count, 3)

        finish_fake = FakeKeyboardHook()
        finish_window = PetWindow(keyboard_hook=finish_fake)
        self.addCleanup(finish_window.close)
        finish_window.stats.work_mode = False
        finish_window.stats.keyboard_visible = True
        finish_window._toggle_work()
        original_quit = pet_window.QApplication.quit
        pet_window.QApplication.quit = lambda: None
        self.addCleanup(lambda: setattr(pet_window.QApplication, "quit", original_quit))

        finish_window._finish_quit()
        finish_window._finish_quit()

        self.assertEqual(finish_fake.stop_count, 1)
        self.assertFalse(finish_fake.running)
        self.assertEqual(finish_window.keyboard_overlay.pressed_assets, set())

    def test_resizing_updates_current_movie_scaled_size(self):
        from PySide6.QtCore import QSize
        from pet_window import PetWindow

        window = PetWindow()
        self.addCleanup(window.close)
        movie = window.label.movie()
        self.assertIsNotNone(movie)

        window._set_pet_size(260)

        self.assertEqual(window.size(), QSize(260, 260))
        self.assertEqual(movie.scaledSize(), QSize(260, 260))

    def test_resizing_keeps_window_inside_screen(self):
        from PySide6.QtWidgets import QApplication
        from pet_window import PetWindow

        screen = QApplication.primaryScreen().availableGeometry()
        window = PetWindow()
        self.addCleanup(window.close)
        window.move(screen.width() - 10, screen.height() - 10)

        window._set_pet_size(400)

        self.assertGreaterEqual(window.x(), 0)
        self.assertGreaterEqual(window.y(), 0)
        self.assertLessEqual(window.x() + window.width(), screen.width())
        self.assertLessEqual(window.y() + window.height(), screen.height())

    def test_work_mode_restores_user_topmost_and_click_preferences(self):
        from PySide6.QtCore import Qt
        from pet_window import PetWindow

        window = PetWindow()
        self.addCleanup(window.close)
        window.stats.work_mode = False
        window.stats.topmost = False
        window.stats.click_through = False
        window._apply_topmost()
        window._apply_click_through()

        window._toggle_work()

        self.assertTrue(window.stats.work_mode)
        self.assertFalse(window.stats.topmost)
        self.assertFalse(window.stats.click_through)
        self.assertFalse(window.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents))

        window._toggle_work()

        self.assertFalse(window.stats.work_mode)
        self.assertFalse(window.stats.topmost)
        self.assertFalse(window.stats.click_through)
        self.assertFalse(window.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents))

    def test_work_mode_does_not_overwrite_normal_saved_position(self):
        from pet_window import PetWindow

        window = PetWindow()
        self.addCleanup(window.close)
        window.stats.work_mode = False
        window.move(123, 234)

        window._toggle_work()
        window.move(300, 300)
        window._sync_position_for_save()

        self.assertEqual(window.stats.x, 123)
        self.assertEqual(window.stats.y, 234)

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

    def test_work_mode_tray_action_exits_work_mode(self):
        from PySide6.QtCore import Qt
        from pet_window import PetWindow

        window = PetWindow()
        self.addCleanup(window.close)
        window.stats.work_mode = False
        window._toggle_work()
        window._setup_tray_menu()

        actions = {
            action.text(): action
            for action in window.tray.contextMenu().actions()
            if action.text()
        }
        actions["退出打工模式"].trigger()

        self.assertFalse(window.stats.work_mode)
        self.assertFalse(window.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents))

    def test_entering_work_mode_cancels_pending_interaction_animation(self):
        from pet_window import PetWindow

        window = PetWindow()
        self.addCleanup(window.close)
        stale_interaction_id = 10
        window.stats.work_mode = False
        window._interaction_in_progress = True
        window._interaction_id = stale_interaction_id
        window._state = "greet"

        window._toggle_work()

        self.assertTrue(window.stats.work_mode)
        self.assertFalse(window._interaction_in_progress)
        self.assertEqual(window._state, "work")

        window._end_interaction(stale_interaction_id)
        window._force_end_interaction(stale_interaction_id)

        self.assertEqual(window._state, "work")

    def test_work_mode_ignores_hover_greet_animation(self):
        from pet_window import PetWindow

        window = PetWindow()
        self.addCleanup(window.close)
        window.stats.work_mode = False
        window._toggle_work()
        window._interaction_in_progress = False
        window._state = "work"

        window._do_hover_greet()

        self.assertEqual(window._state, "work")

    def test_quit_plays_bye_animation_before_saving_and_exiting(self):
        import pet_window
        from pet_window import PetWindow

        saved = []
        quit_calls = []
        scheduled = []
        window = PetWindow()
        self.addCleanup(window.close)
        original_save = window.stats.save
        original_single_shot = window._schedule_single_shot
        original_quit = pet_window.QApplication.quit
        window.stats.save = lambda: saved.append("save")
        window._schedule_single_shot = lambda ms, callback: scheduled.append((ms, callback))
        pet_window.QApplication.quit = lambda: quit_calls.append("quit")
        self.addCleanup(lambda: setattr(window.stats, "save", original_save))
        self.addCleanup(lambda: setattr(window, "_schedule_single_shot", original_single_shot))
        self.addCleanup(lambda: setattr(pet_window.QApplication, "quit", original_quit))

        window._quit()

        self.assertEqual(window._state, "bye")
        self.assertEqual(saved, [])
        self.assertEqual(quit_calls, [])
        self.assertIn(5_000, [ms for ms, _callback in scheduled])

        scheduled[-1][1]()

        self.assertEqual(saved, ["save"])
        self.assertEqual(quit_calls, ["quit"])

    def test_tray_show_reapplies_enabled_topmost_mode(self):
        from PySide6.QtCore import Qt
        from pet_window import PetWindow

        window = PetWindow()
        self.addCleanup(window.close)
        window.stats.topmost = True
        window.hide()
        flags = window.windowFlags()
        window.setWindowFlags(flags & ~Qt.WindowType.WindowStaysOnTopHint)

        window._toggle_visible()

        self.assertTrue(window.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)

    def test_interaction_uses_5_second_timeout(self):
        from pet_window import PetWindow

        scheduled = []
        window = PetWindow()
        self.addCleanup(window.close)
        window.stats.work_mode = False
        window._interaction_in_progress = False
        original_single_shot = window._schedule_single_shot
        window._schedule_single_shot = lambda ms, callback: scheduled.append(ms)
        self.addCleanup(lambda: setattr(window, "_schedule_single_shot", original_single_shot))

        window._play_once("greet")

        self.assertIn(5_000, scheduled)

    def test_interaction_last_frame_before_5s_does_not_end_interaction(self):
        from pet_window import PetWindow

        class FakeMovie:
            stopped = False

            def frameCount(self):
                return 1

            def stop(self):
                self.stopped = True

        window = PetWindow()
        self.addCleanup(window.close)
        window._interaction_in_progress = True
        window._interaction_id = 10
        window._interaction_started_at = window._interaction_started_at or 0
        window._interaction_started_at = __import__("time").time()

        movie = FakeMovie()
        window._end_once_movie(movie, 0, 10)

        self.assertTrue(window._interaction_in_progress)
        self.assertFalse(movie.stopped)

    def test_interaction_blocks_idle_and_walk_until_finished(self):
        from pet_window import PetWindow

        window = PetWindow()
        self.addCleanup(window.close)
        window._interaction_in_progress = True
        window._state = "greet"

        window._play("idle")
        window._play_walk(1, 0)

        self.assertEqual(window._state, "greet")

    def test_interaction_blocks_hover_and_direct_once_animation(self):
        from pet_window import PetWindow

        window = PetWindow()
        self.addCleanup(window.close)
        window._interaction_in_progress = True
        window._state = "eat"

        window._do_hover_greet()
        window._play_once("greet")

        self.assertEqual(window._state, "eat")

    def test_hungry_status_animation_does_not_block_feed(self):
        from pet_window import PetWindow

        window = PetWindow()
        self.addCleanup(window.close)
        window.stats.hunger = 20
        window.stats.cleanliness = 100
        window.stats.affection = 50
        window.stats.work_mode = False
        window.stats._last_action["feed"] = None
        window._state = "idle"
        window._interaction_in_progress = False

        window._tick()

        self.assertEqual(window._state, "hungry")
        self.assertFalse(window._interaction_in_progress)

        window._do_feed()

        self.assertGreater(window.stats.hunger, 20)
        self.assertIsNotNone(window.stats._last_action["feed"])

    def test_startup_greet_plays_greet_category(self):
        from pet_window import PetWindow

        played = []
        window = PetWindow()
        self.addCleanup(window.close)
        original_play_once = window._play_once
        window._play_once = lambda category: played.append(category)
        self.addCleanup(lambda: setattr(window, "_play_once", original_play_once))

        window._play_startup_greet()

        self.assertEqual(played, ["greet"])

    def test_mood_timer_uses_one_minute_cycle_above_90_affection(self):
        from config import MOOD_LONG_CHECK_MS
        from pet_window import PetWindow

        window = PetWindow()
        self.addCleanup(window.close)
        window.stats.affection = 95
        window._run_mood_cycle()

        self.assertEqual(MOOD_LONG_CHECK_MS, 60_000)
        self.assertEqual(window._mood_timer.interval(), MOOD_LONG_CHECK_MS)

    def test_above_90_randomly_picks_happy_for_one_minute(self):
        import pet_window
        from pet_window import PetWindow

        played = []
        scheduled = []
        window = PetWindow()
        self.addCleanup(window.close)
        window.stats.affection = 95
        window._interaction_in_progress = False
        window.stats.work_mode = False
        original_play_once = window._play_once
        original_play = window._play
        original_choice = pet_window.random.choice
        original_single_shot = window._schedule_single_shot
        window._play = lambda category: played.append(category)
        pet_window.random.choice = lambda options: "happy"
        window._schedule_single_shot = lambda ms, callback: scheduled.append(ms)
        self.addCleanup(lambda: setattr(window, "_play_once", original_play_once))
        self.addCleanup(lambda: setattr(window, "_play", original_play))
        self.addCleanup(lambda: setattr(pet_window.random, "choice", original_choice))
        self.addCleanup(lambda: setattr(window, "_schedule_single_shot", original_single_shot))

        window._run_mood_cycle()

        self.assertEqual(played, ["happy"])
        self.assertIn(60_000, scheduled)

    def test_affection_80_to_90_has_50_percent_happy_for_5s(self):
        import pet_window
        from pet_window import PetWindow

        played = []
        scheduled = []
        window = PetWindow()
        self.addCleanup(window.close)
        window.stats.affection = 85
        window._interaction_in_progress = False
        window.stats.work_mode = False
        original_play = window._play
        original_random = pet_window.random.random
        original_single_shot = window._schedule_single_shot
        window._play = lambda category: played.append(category)
        pet_window.random.random = lambda: 0.49
        window._schedule_single_shot = lambda ms, callback: scheduled.append(ms)
        self.addCleanup(lambda: setattr(window, "_play", original_play))
        self.addCleanup(lambda: setattr(pet_window.random, "random", original_random))
        self.addCleanup(lambda: setattr(window, "_schedule_single_shot", original_single_shot))

        window._run_mood_cycle()

        self.assertEqual(played, ["happy"])
        self.assertIn(5_000, scheduled)

    def test_affection_50_to_80_only_idle(self):
        from pet_window import PetWindow

        played = []
        window = PetWindow()
        self.addCleanup(window.close)
        window.stats.affection = 70
        window._interaction_in_progress = False
        window.stats.work_mode = False
        original_play = window._play
        window._play = lambda category: played.append(category)
        self.addCleanup(lambda: setattr(window, "_play", original_play))

        window._run_mood_cycle()

        self.assertEqual(played, ["idle"])

    def test_affection_below_50_has_50_percent_angry_for_5s(self):
        import pet_window
        from pet_window import PetWindow

        played = []
        scheduled = []
        window = PetWindow()
        self.addCleanup(window.close)
        window.stats.affection = 40
        window._interaction_in_progress = False
        window.stats.work_mode = False
        original_play = window._play
        original_random = pet_window.random.random
        original_single_shot = window._schedule_single_shot
        window._play = lambda category: played.append(category)
        pet_window.random.random = lambda: 0.49
        window._schedule_single_shot = lambda ms, callback: scheduled.append(ms)
        self.addCleanup(lambda: setattr(window, "_play", original_play))
        self.addCleanup(lambda: setattr(pet_window.random, "random", original_random))
        self.addCleanup(lambda: setattr(window, "_schedule_single_shot", original_single_shot))

        window._run_mood_cycle()

        self.assertEqual(played, ["angry"])
        self.assertIn(5_000, scheduled)

    def test_tick_does_not_trigger_high_affection_happy_directly(self):
        import pet_window
        from pet_window import PetWindow

        played = []
        window = PetWindow()
        self.addCleanup(window.close)
        window.stats.hunger = 80
        window.stats.cleanliness = 80
        window.stats.affection = 90
        window._interaction_in_progress = False
        window._last_state_change = pet_window.time.time() - 20
        original_random = pet_window.random.random
        original_play_once = window._play_once
        pet_window.random.random = lambda: 0
        window._play_once = lambda category: played.append(category)
        self.addCleanup(lambda: setattr(pet_window.random, "random", original_random))
        self.addCleanup(lambda: setattr(window, "_play_once", original_play_once))

        window._tick()

        self.assertNotIn("happy", played)

    def test_random_walk_triggers_only_in_idle_walk_window(self):
        import pet_window
        from pet_window import PetWindow

        calls = []
        window = PetWindow()
        self.addCleanup(window.close)
        window.stats.hunger = 80
        window.stats.cleanliness = 80
        window.stats.affection = 50
        window.stats.work_mode = False
        window._interaction_in_progress = False
        window._last_state_change = pet_window.time.time() - 31
        original_random = pet_window.random.random
        original_random_walk = window._random_walk
        pet_window.random.random = lambda: 0
        window._random_walk = lambda: calls.append("walk")
        self.addCleanup(lambda: setattr(pet_window.random, "random", original_random))
        self.addCleanup(lambda: setattr(window, "_random_walk", original_random_walk))

        window._tick()

        self.assertEqual(calls, ["walk"])

    def test_random_walk_does_not_trigger_before_idle_walk_min(self):
        import pet_window
        from pet_window import PetWindow

        calls = []
        window = PetWindow()
        self.addCleanup(window.close)
        window.stats.hunger = 80
        window.stats.cleanliness = 80
        window.stats.affection = 50
        window._interaction_in_progress = False
        window._last_state_change = pet_window.time.time() - 29
        original_random = pet_window.random.random
        original_random_walk = window._random_walk
        pet_window.random.random = lambda: 0
        window._random_walk = lambda: calls.append("walk")
        self.addCleanup(lambda: setattr(pet_window.random, "random", original_random))
        self.addCleanup(lambda: setattr(window, "_random_walk", original_random_walk))

        window._tick()

        self.assertEqual(calls, [])

    def test_random_walk_does_not_trigger_in_work_mode(self):
        import pet_window
        from pet_window import PetWindow

        calls = []
        window = PetWindow()
        self.addCleanup(window.close)
        window.stats.work_mode = True
        window.stats.hunger = 80
        window.stats.cleanliness = 80
        window.stats.affection = 50
        window._interaction_in_progress = False
        window._last_state_change = pet_window.time.time() - 31
        original_random = pet_window.random.random
        original_random_walk = window._random_walk
        pet_window.random.random = lambda: 0
        window._random_walk = lambda: calls.append("walk")
        self.addCleanup(lambda: setattr(pet_window.random, "random", original_random))
        self.addCleanup(lambda: setattr(window, "_random_walk", original_random_walk))

        window._tick()

        self.assertEqual(calls, [])


class PetStatsLoadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])

    def test_load_clamps_and_coerces_persisted_values(self):
        import json
        from PySide6.QtWidgets import QApplication
        from config import SIZE_MAX
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
                    "keyboard_visible": "yes",
                    "work_mode": 1,
                    "pet_size": SIZE_MAX + 500,
                    "last_feed": "bad",
                    "last_bath": 123.5,
                }, f)

            stats = PetStats(data_file=data_file, data_dir=data_dir)

        screen = QApplication.primaryScreen().availableGeometry()
        expected_y = min(500, screen.height() - SIZE_MAX)
        self.assertEqual(stats.hunger, 100)
        self.assertEqual(stats.cleanliness, 0)
        self.assertEqual(stats.affection, 100)
        self.assertEqual(stats.x, 12)
        self.assertEqual(stats.y, expected_y)
        self.assertFalse(stats.topmost)
        self.assertTrue(stats.click_through)
        self.assertTrue(stats.keyboard_visible)
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
        self.assertEqual(stats.affection, 100)

    def test_first_use_starts_with_full_stats(self):
        from PySide6.QtWidgets import QApplication
        from pet_stats import PetStats

        with tempfile.TemporaryDirectory() as data_dir:
            data_file = os.path.join(data_dir, "pet_data.json")
            stats = PetStats(data_file=data_file, data_dir=data_dir)

        screen = QApplication.primaryScreen().availableGeometry()
        expected_x = screen.width() - 180 - int(screen.width() * 0.10)
        expected_y = screen.height() - 180 - 80
        self.assertEqual(stats.hunger, 100)
        self.assertEqual(stats.cleanliness, 100)
        self.assertEqual(stats.affection, 100)
        self.assertEqual(stats.pet_size, 180)
        self.assertEqual(stats.x, expected_x)
        self.assertEqual(stats.y, expected_y)

    def test_persisted_size_and_position_override_first_use_defaults(self):
        import json
        from pet_stats import PetStats

        with tempfile.TemporaryDirectory() as data_dir:
            data_file = os.path.join(data_dir, "pet_data.json")
            with open(data_file, "w", encoding="utf-8") as f:
                json.dump({"pet_size": 220, "x": 33, "y": 44}, f)

            stats = PetStats(data_file=data_file, data_dir=data_dir)

        self.assertEqual(stats.pet_size, 220)
        self.assertEqual(stats.x, 33)
        self.assertEqual(stats.y, 44)


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


if __name__ == "__main__":
    unittest.main()
