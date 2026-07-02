import os
import sys

from config import BASE_DIR, STARTUP_KEY, STARTUP_NAME

try:
    import winreg
except ImportError:  # pragma: no cover - Windows-only feature.
    winreg = None


def build_startup_command(executable=None, script_path=None, frozen=None):
    executable = executable or sys.executable
    if frozen is None:
        frozen = getattr(sys, "frozen", False)
    if frozen:
        return f'"{executable}"'
    script_path = script_path or os.path.join(BASE_DIR, "main.py")
    return f'"{executable}" "{script_path}"'


def is_startup_enabled(registry=None):
    registry = _get_registry(registry)
    if registry is None:
        return False
    try:
        with registry.OpenKey(
            registry.HKEY_CURRENT_USER,
            STARTUP_KEY,
            0,
            registry.KEY_READ,
        ) as key:
            registry.QueryValueEx(key, STARTUP_NAME)
        return True
    except (FileNotFoundError, OSError):
        return False


def set_startup_enabled(enabled, registry=None, command=None):
    registry = _get_registry(registry)
    if registry is None:
        return False
    if enabled:
        command = command or build_startup_command()
        with registry.OpenKey(
            registry.HKEY_CURRENT_USER,
            STARTUP_KEY,
            0,
            registry.KEY_SET_VALUE,
        ) as key:
            registry.SetValueEx(key, STARTUP_NAME, 0, registry.REG_SZ, command)
        return True
    try:
        with registry.OpenKey(
            registry.HKEY_CURRENT_USER,
            STARTUP_KEY,
            0,
            registry.KEY_SET_VALUE,
        ) as key:
            registry.DeleteValue(key, STARTUP_NAME)
    except FileNotFoundError:
        pass
    return True


def _get_registry(registry):
    return registry if registry is not None else winreg
