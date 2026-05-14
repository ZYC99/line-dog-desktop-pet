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

    # 单实例检测
    if is_instance_running():
        print("LineDogPet 已在运行")
        sys.exit(0)

    server = start_local_server()

    window = PetWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
