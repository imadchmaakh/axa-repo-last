APP_QSS = """
* { font-family: 'Segoe UI', 'Arial'; font-size: 12pt; }
QWidget { background: #f8fafc; color: #0f172a; }
QTabWidget::pane { border: 1px solid #e2e8f0; }
QTabBar::tab { padding: 8px 16px; background: #e2e8f0; margin: 2px; border-radius: 10px; }
QTabBar::tab:selected { background: #60a5fa; color: white; }

QGroupBox { border: 1px solid #cbd5e1; border-radius: 12px; margin-top: 12px; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 6px; }

QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox {
    background: white; border: 1px solid #cbd5e1; border-radius: 10px; padding: 6px;
}
QPushButton {
    background: #22c55e; color: white; border: none; border-radius: 12px; padding: 8px 16px;
}
QPushButton:hover { background: #16a34a; }
QPushButton#danger { background: #ef4444; }
QPushButton#danger:hover { background: #dc2626; }
QPushButton#secondary { background: #3b82f6; }
QPushButton#secondary:hover { background: #2563eb; }

QTableWidget { background: white; gridline-color: #e2e8f0; }
QHeaderView::section { background: #e2e8f0; padding: 6px; border: none; }
QLabel#HeaderTitle { font-size: 18pt; font-weight: 700; }
QLabel#OutOfStock { color: #ef4444; font-weight: 600; }
"""
