import sys
from PyQt6.QtWidgets import QApplication

from .demo_advanced import LuminaPyQtMainWindow

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = LuminaPyQtMainWindow()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
