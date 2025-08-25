import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from database import setup_database
from controllers import Controller
from qss import APP_QSS

def setup_application():
    """Setup application with enhanced configuration"""
    app = QApplication(sys.argv)
    
    # Application metadata
    app.setApplicationName("Store Manager (Arabic)")
    app.setApplicationDisplayName("نظام إدارة المتجر")
    app.setApplicationVersion("2.0")
    app.setOrganizationName("Store Management Solutions")
    
    # Enable high DPI scaling for better display on modern screens
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    # Set default font for better Arabic text rendering
    font = QFont("Segoe UI", 11)
    font.setStyleHint(QFont.System)
    app.setFont(font)
    
    # Apply dark theme stylesheet
    app.setStyleSheet(APP_QSS)
    
    return app

def create_required_directories():
    """Create necessary directories for the application"""
    directories = [
        "assets",
        "assets/logo", 
        "assets/photos"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

def main():
    """Main application entry point"""
    # Setup database
    setup_database()
    
    # Create required directories
    create_required_directories()
    
    # Setup and configure application
    app = setup_application()
    
    # Create and show main window
    window = Controller()
    window.show()
    
    # Center window on screen
    screen = app.primaryScreen().geometry()
    window_size = window.geometry()
    x = (screen.width() - window_size.width()) // 2
    y = (screen.height() - window_size.height()) // 2
    window.move(x, y)
    
    # Start application event loop
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()