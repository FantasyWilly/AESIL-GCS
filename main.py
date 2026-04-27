import sys


from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow

def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow(rosbridge_url="ws://127.0.0.1:9090")
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
