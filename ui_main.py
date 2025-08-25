# ui_main.py
from PyQt5.QtWidgets import (
    QWidget, QTabWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QDoubleSpinBox, QFileDialog, QTableWidget, QTableWidgetItem,
    QGroupBox, QMessageBox, QHeaderView, QAbstractItemView, QFrame, QTextEdit
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap, QFont, QIcon

class MainUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("نظام إدارة المتجر")
        self.resize(1280, 820)
        self.setLayoutDirection(Qt.RightToLeft)

        # Custom app/taskbar icon (no default Python icon)
        self.setWindowIcon(QIcon("assets/logo/app_icon.png"))

        main = QVBoxLayout(self)
        main.setContentsMargins(10,10,10,10)
        main.setSpacing(8)

        # Custom header (title right, window buttons left)
        header = QHBoxLayout()
        self.lbl_title = QLabel("نظام إدارة المتجر")
        self.lbl_title.setObjectName("HeaderTitle")
        header.addWidget(self.lbl_title)
        header.addStretch(1)
        self.btn_min = QPushButton("—")
        self.btn_max = QPushButton("⬜")
        self.btn_close = QPushButton("✕")
        self.btn_close.setObjectName("danger")
        for b in (self.btn_min, self.btn_max, self.btn_close):
            b.setMinimumHeight(34)
        row_btns = QHBoxLayout()
        row_btns.addWidget(self.btn_min)
        row_btns.addWidget(self.btn_max)
        row_btns.addWidget(self.btn_close)
        header.addLayout(row_btns)
        main.addLayout(header)

        line = QFrame(); line.setFrameShape(QFrame.HLine); line.setFrameShadow(QFrame.Sunken)
        main.addWidget(line)

        self.tabs = QTabWidget()
        self.tabs.setLayoutDirection(Qt.RightToLeft)
        main.addWidget(self.tabs)

        # Build tabs
        self._build_bill_tab()
        self._build_stock_tab()
        self._build_sales_tab()
        self._build_settings_tab()

        # Tab icons (Arabic titles preserved)
        self.tabs.setTabIcon(0, QIcon("assets/logo/tab_bill.png"))
        self.tabs.setTabIcon(1, QIcon("assets/logo/tab_stock.png"))
        self.tabs.setTabIcon(2, QIcon("assets/logo/tab_sales.png"))
        self.tabs.setTabIcon(3, QIcon("assets/logo/tab_settings.png"))
        self.tabs.setIconSize(QSize(24, 24))

    # ---------- Current Bill Tab ----------
    def _build_bill_tab(self):
        tab = QWidget()
        outer = QVBoxLayout(tab)
        outer.setSpacing(10)

        # Top row — bigger, aligned inputs
        row = QHBoxLayout()
        row.setSpacing(8)

        self.in_barcode = QLineEdit()
        self.in_barcode.setPlaceholderText("الباركود (8 أو 12 أو 13 رقمًا)")
        self.in_barcode.setMinimumHeight(42)
        self.in_barcode.setClearButtonEnabled(True)

        btn_find = QPushButton("بحث/إضافة")
        btn_find.setMinimumHeight(42)

        self.btn_scan_camera = QPushButton("مسح بالكاميرا"); self.btn_scan_camera.setObjectName("secondary")
        self.btn_scan_camera.setMinimumHeight(42)

        self.in_name = QLineEdit(); self.in_name.setPlaceholderText("اسم المنتج")
        self.in_name.setMinimumHeight(42)
        name_font = QFont(); name_font.setPointSize(12); name_font.setBold(True)
        self.in_name.setFont(name_font)

        self.in_price = QDoubleSpinBox(); self.in_price.setMaximum(10**9); self.in_price.setDecimals(2)
        self.in_price.setMinimumHeight(42)

        self.in_qty = QDoubleSpinBox(); self.in_qty.setMaximum(10**9); self.in_qty.setDecimals(3); self.in_qty.setValue(1.0)
        self.in_qty.setMinimumHeight(42)

        self.in_unit = QComboBox(); self.in_unit.addItems(["حبة", "علبة/عبوة"])
        self.in_unit.setMinimumHeight(42)

        self.chk_manual = QComboBox(); self.chk_manual.addItems(["سعر من قاعدة البيانات", "سعر يدوي"]); self.chk_manual.setCurrentIndex(0)
        self.chk_manual.setMinimumHeight(42)

        btn_add_to_bill = QPushButton("إضافة إلى الفاتورة")
        btn_add_to_bill.setMinimumHeight(42)

        btn_remove_selected = QPushButton("حذف المحدد"); btn_remove_selected.setObjectName("danger")
        btn_remove_selected.setMinimumHeight(42)

        btn_save_sale = QPushButton("حفظ الفاتورة"); btn_save_sale.setObjectName("secondary")
        btn_save_sale.setMinimumHeight(42)

        # Stretch factors to keep things responsive
        row.addWidget(self.in_barcode, 2)
        row.addWidget(btn_find, 1)
        row.addWidget(self.btn_scan_camera, 1)
        row.addWidget(self.in_name, 2)
        row.addWidget(self.in_price, 1)
        row.addWidget(self.in_qty, 1)
        row.addWidget(self.in_unit, 1)
        row.addWidget(self.chk_manual, 1)
        row.addWidget(btn_add_to_bill, 1)
        row.addWidget(btn_remove_selected, 1)
        row.addWidget(btn_save_sale, 1)
        outer.addLayout(row)

        # bill table
        self.tbl_bill = QTableWidget(0, 7)  # extra hidden column for live_deducted
        self.tbl_bill.setWordWrap(True)
        self.tbl_bill.setHorizontalHeaderLabels(["الباركود", "الاسم", "سعر الوحدة", "الكمية", "الإجمالي", "ID", "_live"])
        self.tbl_bill.horizontalHeader().setSectionHidden(5, True)
        self.tbl_bill.horizontalHeader().setSectionHidden(6, True)
        self.tbl_bill.horizontalHeader().setStretchLastSection(True)
        self.tbl_bill.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl_bill.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)  # big name column
        self.tbl_bill.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl_bill.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tbl_bill.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.tbl_bill.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tbl_bill.setMinimumHeight(300)
        outer.addWidget(self.tbl_bill)

        # footer with total + print
        footer = QHBoxLayout()
        self.btn_print_bill = QPushButton("طباعة الفاتورة")
        footer.addWidget(self.btn_print_bill)
        footer.addStretch(1)
        self.lbl_total = QLabel("الإجمالي: 0.00")
        total_font = QFont(); total_font.setPointSize(14); total_font.setBold(True)
        self.lbl_total.setFont(total_font)
        footer.addWidget(self.lbl_total)
        outer.addLayout(footer)

        self.tabs.addTab(tab, "الفاتورة الحالية")

        # expose
        self.btn_bill_find = btn_find
        self.btn_bill_add = btn_add_to_bill
        self.btn_bill_remove = btn_remove_selected
        self.btn_bill_save = btn_save_sale

        # make product name font bigger in bill rows too
        self._bill_name_font = QFont()
        self._bill_name_font.setPointSize(14)
        self._bill_name_font.setBold(True)

    # ---------- Stock Tab ----------
    def _build_stock_tab(self):
        tab = QWidget()
        outer = QVBoxLayout(tab)
        outer.setSpacing(10)

        grp = QGroupBox("بيانات الصنف")
        form = QHBoxLayout()
        form.setSpacing(8)

        self.stk_name = QLineEdit(); self.stk_name.setPlaceholderText("اسم الصنف")
        self.stk_name.setMinimumHeight(42)
        name_font = QFont(); name_font.setPointSize(12); name_font.setBold(True)
        self.stk_name.setFont(name_font)

        self.stk_barcode = QLineEdit(); self.stk_barcode.setPlaceholderText("الباركود (8 أو 12 أو 13 رقمًا)")
        self.stk_barcode.setMinimumHeight(42)

        self.stk_price = QDoubleSpinBox(); self.stk_price.setMaximum(10**9); self.stk_price.setDecimals(2)
        self.stk_price.setMinimumHeight(42)

        self.stk_qty = QDoubleSpinBox(); self.stk_qty.setMaximum(10**9); self.stk_qty.setDecimals(3)
        self.stk_qty.setMinimumHeight(42)

        self.stk_cat = QComboBox()
        self.stk_cat.setMinimumHeight(42)

        self.stk_photo = QLineEdit(); self.stk_photo.setPlaceholderText("مسار الصورة")
        self.stk_photo.setMinimumHeight(42)

        btn_browse = QPushButton("اختيار صورة"); btn_browse.setMinimumHeight(42)
        btn_camera = QPushButton("التقاط من الكاميرا"); btn_camera.setObjectName("secondary"); btn_camera.setMinimumHeight(42)
        btn_new_cat = QPushButton("تصنيف جديد"); btn_new_cat.setMinimumHeight(42)

        self.preview = QLabel("لا توجد صورة")
        self.preview.setFixedSize(160, 160)
        self.preview.setStyleSheet("border:1px solid #2e3440; border-radius:12px;")
        self.preview.setAlignment(Qt.AlignCenter)

        form.addWidget(self.stk_name, 2)
        form.addWidget(self.stk_barcode, 1)
        form.addWidget(self.stk_price, 1)
        form.addWidget(self.stk_qty, 1)
        form.addWidget(self.stk_cat, 1)
        form.addWidget(self.stk_photo, 2)
        form.addWidget(btn_browse, 1)
        form.addWidget(btn_camera, 1)
        form.addWidget(btn_new_cat, 1)
        form.addWidget(self.preview, 0)
        grp.setLayout(form)
        outer.addWidget(grp)

        btns = QHBoxLayout()
        btn_add = QPushButton("إضافة")
        btn_update = QPushButton("تعديل")
        btn_delete = QPushButton("حذف"); btn_delete.setObjectName("danger")
        btn_refresh = QPushButton("تحديث")
        btns.addWidget(btn_add); btns.addWidget(btn_update); btns.addWidget(btn_delete); btns.addStretch(1); btns.addWidget(btn_refresh)
        outer.addLayout(btns)

        self.tbl_stock = QTableWidget(0, 10)
        self.tbl_stock.setWordWrap(True)
        self.tbl_stock.setHorizontalHeaderLabels(["ID", "الاسم", "التصنيف", "الباركود", "السعر", "المخزون", "الحالة", "الصورة", "تاريخ الإضافة", "cat_id"])
        # More responsive column behavior
        header = self.tbl_stock.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)          # name stretches
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(8, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(9, QHeaderView.ResizeToContents)
        self.tbl_stock.horizontalHeader().setSectionHidden(0, True)
        self.tbl_stock.horizontalHeader().setSectionHidden(9, True)
        self.tbl_stock.setSelectionBehavior(QAbstractItemView.SelectRows)
        outer.addWidget(self.tbl_stock)

        self.tabs.addTab(tab, "المخزون")

        self.btn_stk_browse = btn_browse
        self.btn_stk_camera = btn_camera
        self.btn_stk_new_cat = btn_new_cat
        self.btn_stk_add = btn_add
        self.btn_stk_update = btn_update
        self.btn_stk_delete = btn_delete
        self.btn_stk_refresh = btn_refresh

    # ---------- Sales Tab ----------
    def _build_sales_tab(self):
        tab = QWidget()
        outer = QVBoxLayout(tab)
        outer.setSpacing(10)

        kpi = QHBoxLayout()
        self.lbl_total_sales = QLabel("إجمالي المبيعات: 0.00")
        self.lbl_today_sales = QLabel("مبيعات اليوم: 0.00")
        self.lbl_latest_sale = QLabel("آخر عملية: -")
        kpi.addWidget(self.lbl_total_sales)
        kpi.addWidget(self.lbl_today_sales)
        kpi.addWidget(self.lbl_latest_sale)
        kpi.addStretch(1)
        outer.addLayout(kpi)

        self.tbl_sales = QTableWidget(0, 3)
        self.tbl_sales.setHorizontalHeaderLabels(["رقم العملية", "التاريخ والوقت", "الإجمالي"])
        header = self.tbl_sales.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl_sales.setSelectionBehavior(QAbstractItemView.SelectRows)
        outer.addWidget(self.tbl_sales)

        row = QHBoxLayout()
        btn_view = QPushButton("عرض تفاصيل العملية المحددة")
        btn_delete = QPushButton("حذف العملية المحددة (مع إرجاع المخزون)"); btn_delete.setObjectName("danger")
        btn_refresh = QPushButton("تحديث")
        row.addWidget(btn_view); row.addWidget(btn_delete); row.addStretch(1); row.addWidget(btn_refresh)
        outer.addLayout(row)

        self.tbl_sale_details = QTableWidget(0, 6)
        self.tbl_sale_details.setHorizontalHeaderLabels(["ID Det", "الاسم", "الباركود", "الكمية", "سعر الوحدة", "الإجمالي"])
        header2 = self.tbl_sale_details.horizontalHeader()
        header2.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header2.setSectionResizeMode(1, QHeaderView.Stretch)
        header2.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header2.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header2.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header2.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.tbl_sale_details.horizontalHeader().setSectionHidden(0, True)
        outer.addWidget(self.tbl_sale_details)

        self.tabs.addTab(tab, "المبيعات")

        self.btn_sale_view = btn_view
        self.btn_sale_delete = btn_delete
        self.btn_sale_refresh = btn_refresh

    # ---------- Settings Tab ----------
    def _build_settings_tab(self):
        tab = QWidget()
        outer = QVBoxLayout(tab)

        grp = QGroupBox("إعدادات المتجر")
        form = QVBoxLayout()
        self.sett_shop_name = QLineEdit(); self.sett_shop_name.setPlaceholderText("اسم المتجر (يظهر عنوان التطبيق والفاتورة)")
        self.sett_contact = QLineEdit(); self.sett_contact.setPlaceholderText("هاتف / بريد إلكتروني")
        self.sett_location = QLineEdit(); self.sett_location.setPlaceholderText("العنوان / الموقع")
        self.sett_currency = QLineEdit(); self.sett_currency.setPlaceholderText("العملة (مثال: د.ج ، ر.س ، د.ك ، MAD ، USD)")
        for w in (self.sett_shop_name, self.sett_contact, self.sett_location, self.sett_currency):
            w.setMinimumHeight(40)
        form.addWidget(self.sett_shop_name)
        form.addWidget(self.sett_contact)
        form.addWidget(self.sett_location)
        form.addWidget(self.sett_currency)

        btn_save = QPushButton("حفظ الإعدادات"); btn_save.setObjectName("secondary")
        btn_save.setMinimumHeight(42)
        form.addWidget(btn_save)
        grp.setLayout(form)

        outer.addWidget(grp)
        outer.addStretch(1)

        self.tabs.addTab(tab, "الإعدادات")

        self.btn_settings_save = btn_save

    # ---------- Helpers ----------
    def msg(self, title, text):
        QMessageBox.information(self, title, text)

    def set_preview_image(self, path: str):
        if path and len(path.strip()) > 0 and QPixmap(path).isNull() is False:
            pix = QPixmap(path).scaled(self.preview.width(), self.preview.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.preview.setPixmap(pix)
        else:
            self.preview.setText("لا توجد صورة")
