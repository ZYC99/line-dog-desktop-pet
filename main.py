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
