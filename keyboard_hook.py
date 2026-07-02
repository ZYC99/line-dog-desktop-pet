import sys
import threading

from PySide6.QtCore import QObject, Signal


class KeyboardHook(QObject):
    key_event = Signal(int, int, bool, bool)

    def __init__(self, backend=None, parent=None):
        super().__init__(parent)
        self._backend = backend if backend is not None else WindowsLowLevelKeyboardBackend()
        self._running = False

    @property
    def running(self):
        return self._running

    def start(self):
        if self._running:
            return True
        if not self._backend.start(self._emit_key_event):
            self._running = False
            return False
        self._running = True
        return True

    def stop(self):
        if not self._running:
            return
        stopped = self._backend.stop()
        if stopped is not False:
            self._running = False

    def _emit_key_event(self, vk_code, scan_code, extended, pressed):
        self.key_event.emit(int(vk_code), int(scan_code), bool(extended), bool(pressed))


class WindowsLowLevelKeyboardBackend:
    WH_KEYBOARD_LL = 13
    WM_KEYDOWN = 0x0100
    WM_KEYUP = 0x0101
    WM_SYSKEYDOWN = 0x0104
    WM_SYSKEYUP = 0x0105
    WM_QUIT = 0x0012
    WM_USER = 0x0400
    LLKHF_EXTENDED = 0x01
    PM_NOREMOVE = 0x0000

    def __init__(self):
        self._callback = None
        self._hook_proc = None
        self._hook_handle = None
        self._thread = None
        self._thread_id = None
        self._ready = threading.Event()
        self._started = False
        self._lock = threading.Lock()

    def start(self, callback):
        if sys.platform != "win32":
            return False

        with self._lock:
            if self._started:
                return True
            self._callback = callback
            self._ready.clear()
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

        if not self._ready.wait(timeout=2.0):
            self.stop()
            return False

        with self._lock:
            self._started = self._hook_handle is not None
            if not self._started:
                self._callback = None
                self._hook_proc = None
            return self._started

    def stop(self):
        thread = None
        thread_id = None
        posted_quit = True
        if sys.platform == "win32":
            with self._lock:
                thread = self._thread
                thread_id = self._thread_id
            if thread_id:
                posted_quit = self._post_quit_message(thread_id)
        with self._lock:
            thread = thread or self._thread
        thread_alive = False
        if thread and thread.is_alive():
            thread.join(timeout=1.0)
            thread_alive = thread.is_alive()
        stopped = posted_quit and not thread_alive
        with self._lock:
            if stopped:
                self._started = False
                self._thread = None
                self._thread_id = None
                self._hook_handle = None
                self._hook_proc = None
                self._callback = None
                self._ready.clear()
            else:
                self._started = True
        return stopped

    def _post_quit_message(self, thread_id):
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        user32.PostThreadMessageW.argtypes = [
            wintypes.DWORD,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        ]
        user32.PostThreadMessageW.restype = wintypes.BOOL
        return bool(user32.PostThreadMessageW(thread_id, self.WM_QUIT, 0, 0))

    def _run(self):
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        lresult = ctypes.c_ssize_t
        hhook = ctypes.c_void_p
        hinstance = ctypes.c_void_p
        ulong_ptr = ctypes.c_size_t

        class KBDLLHOOKSTRUCT(ctypes.Structure):
            _fields_ = [
                ("vkCode", wintypes.DWORD),
                ("scanCode", wintypes.DWORD),
                ("flags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", ulong_ptr),
            ]

        low_level_keyboard_proc = ctypes.WINFUNCTYPE(
            lresult,
            ctypes.c_int,
            wintypes.WPARAM,
            wintypes.LPARAM,
        )

        user32.SetWindowsHookExW.argtypes = [
            ctypes.c_int,
            low_level_keyboard_proc,
            hinstance,
            wintypes.DWORD,
        ]
        user32.SetWindowsHookExW.restype = hhook
        user32.CallNextHookEx.argtypes = [
            hhook,
            ctypes.c_int,
            wintypes.WPARAM,
            wintypes.LPARAM,
        ]
        user32.CallNextHookEx.restype = lresult
        user32.UnhookWindowsHookEx.argtypes = [hhook]
        user32.UnhookWindowsHookEx.restype = wintypes.BOOL
        user32.GetMessageW.argtypes = [
            ctypes.POINTER(wintypes.MSG),
            wintypes.HWND,
            wintypes.UINT,
            wintypes.UINT,
        ]
        user32.GetMessageW.restype = wintypes.BOOL
        user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
        user32.TranslateMessage.restype = wintypes.BOOL
        user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
        user32.DispatchMessageW.restype = lresult
        user32.PeekMessageW.argtypes = [
            ctypes.POINTER(wintypes.MSG),
            wintypes.HWND,
            wintypes.UINT,
            wintypes.UINT,
            wintypes.UINT,
        ]
        user32.PeekMessageW.restype = wintypes.BOOL
        kernel32.GetCurrentThreadId.argtypes = []
        kernel32.GetCurrentThreadId.restype = wintypes.DWORD
        kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
        kernel32.GetModuleHandleW.restype = hinstance

        def hook_proc(n_code, w_param, l_param):
            try:
                if n_code >= 0 and w_param in (
                    self.WM_KEYDOWN,
                    self.WM_SYSKEYDOWN,
                    self.WM_KEYUP,
                    self.WM_SYSKEYUP,
                ):
                    event = ctypes.cast(l_param, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                    pressed = w_param in (self.WM_KEYDOWN, self.WM_SYSKEYDOWN)
                    extended = bool(event.flags & self.LLKHF_EXTENDED)
                    callback = self._callback
                    if callback is not None:
                        callback(event.vkCode, event.scanCode, extended, pressed)
            finally:
                return user32.CallNextHookEx(self._hook_handle, n_code, w_param, l_param)

        msg = wintypes.MSG()
        thread_id = kernel32.GetCurrentThreadId()
        user32.PeekMessageW(ctypes.byref(msg), None, self.WM_USER, self.WM_USER, self.PM_NOREMOVE)
        hook_proc_ref = low_level_keyboard_proc(hook_proc)
        module_handle = kernel32.GetModuleHandleW(None)
        hook_handle = user32.SetWindowsHookExW(
            self.WH_KEYBOARD_LL,
            hook_proc_ref,
            module_handle,
            0,
        )

        with self._lock:
            self._thread_id = thread_id
            self._hook_proc = hook_proc_ref
            self._hook_handle = hook_handle
        self._ready.set()

        if not hook_handle:
            return

        try:
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            user32.UnhookWindowsHookEx(hook_handle)
