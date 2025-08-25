import sys
from PyQt5.QtWidgets import QApplication
from database import setup_database
from controllers import Controller
from qss import APP_QSS

if __name__ == "__main__":
    setup_database()
    app = QApplication(sys.argv)
    app.setApplicationName("Store Manager (Arabic)")
    app.setStyleSheet(APP_QSS)
    win = Controller()
    win.show()
    sys.exit(app.exec_())
