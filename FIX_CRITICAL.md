# 关键修复：4 项

> 项目: D:/软件安装/line-dog-desktop-pet
> 只修 🔴 级别，按文件顺序

---

## 修复 1：`main.py` — 单实例检测

**当前：** 只有 QLocalSocket 连接，没有 QLocalServer 监听。
**修复：** 第一个实例创建 QLocalServer.listen("LineDogPet")。

完整重写 main.py：
```python
import sys, os
from PySide6.QtWidgets import QApplication
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from pet_window import PetWindow

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # 单实例检测
    socket = QLocalSocket()
    socket.connectToServer("LineDogPet")
    if socket.waitForConnected(500):
        print("LineDogPet 已在运行")
        sys.exit(0)

    server = QLocalServer()
    server.listen("LineDogPet")

    window = PetWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
```

---

## 修复 2：`pet_window.py` — 首次鼠标进入不触发震惊

**位置：** `__init__` 中 `self._last_mouse_leave = 0`
**改为：**
```python
self._last_mouse_leave = time.time()
```

---

## 修复 3：`pet_window.py` — finished 信号累积

**位置：** `_play_once` 方法，`movie.finished.connect` 前加 disconnect：
```python
    self._state = category
    self._interaction_in_progress = True
    try:
        movie.finished.disconnect()
    except RuntimeError:
        pass
    movie.finished.connect(lambda: self._end_interaction())
```

---

## 修复 4：`pet_window.py` — 打工模式重启恢复

**位置：** `__init__` 末尾（`_setup_tray()` 之后），加：
```python
        # 恢复打工模式
        if self.stats.work_mode:
            self.stats.work_mode = False
            self._toggle_work()
```

---

## 执行后

1. 语法检查
2. 启动测试
