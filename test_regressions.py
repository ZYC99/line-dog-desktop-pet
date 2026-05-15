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


class BuildConfigTests(unittest.TestCase):
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
        self.assertIn("softprops/action-gh-release", content)


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
