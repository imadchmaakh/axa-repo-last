import os
from datetime import datetime
from PyQt5.QtWidgets import QFileDialog, QTableWidgetItem, QMessageBox, QInputDialog
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog
from PyQt5.QtGui import QTextDocument

from ui_main import MainUI
import models

# Optional camera/scan dependencies (kept as in original; camera not required)
try:
    import cv2
except Exception:
    cv2 = None

try:
    from pyzbar.pyzbar import decode as zbar_decode
except Exception:
    zbar_decode = None

ASSETS_PHOTOS_DIR = os.path.join("assets", "photos")
os.makedirs(ASSETS_PHOTOS_DIR, exist_ok=True)

# --- Barcode validation: only numeric and length in 8, 12, 13 ---
ALLOWED_BARCODE_LENGTHS = {8, 12, 13}
def is_valid_barcode(code: str) -> bool:
    return code.isdigit() and (len(code) in ALLOWED_BARCODE_LENGTHS)

class Controller(MainUI):
    def __init__(self):
        super().__init__()

        # Window header buttons
        self.btn_min.clicked.connect(self.showMinimized)
        self.btn_max.clicked.connect(self._toggle_max_restore)
        self.btn_close.clicked.connect(self.close)

        # Load settings; if missing, run first-time setup
        self.currency = "د.ج"
        self._load_settings_or_first_run()

        # Initialize data
        self._load_categories()
        self._load_stock_table()
        self._load_sales_tab()
        self._apply_currency_to_inputs()

        # Bill: connect signals
        self.btn_bill_find.clicked.connect(self._bill_find)
        self.btn_bill_add.clicked.connect(self._bill_add)
        self.btn_bill_remove.clicked.connect(self._bill_remove_selected)
        self.btn_bill_save.clicked.connect(self._bill_save)
        self.btn_print_bill.clicked.connect(self._bill_print)
        self.btn_scanner_info.clicked.connect(self._show_scanner_info)

        # Hardware scanner support: scanners "type" then send Enter.
        self.in_barcode.returnPressed.connect(self._handle_scanned_barcode)

        # Stock
        self.btn_stk_browse.clicked.connect(self._browse_photo)
        self.btn_stk_camera.clicked.connect(self._capture_photo)
        self.btn_stk_new_cat.clicked.connect(self._add_new_category)
        self.btn_stk_add.clicked.connect(self._stock_add)
        self.btn_stk_update.clicked.connect(self._stock_update)
        self.btn_stk_delete.clicked.connect(self._stock_delete)
        self.btn_stk_refresh.clicked.connect(self._load_stock_table)
        self.tbl_stock.clicked.connect(self._stock_fill_form_from_selection)

        # Sales
        self.btn_sale_refresh.clicked.connect(self._load_sales_tab)
        self.btn_sale_view.clicked.connect(self._sales_view_selected)
        self.btn_sale_delete.clicked.connect(self._sales_delete_selected)
        self.tbl_sales.itemSelectionChanged.connect(self._sales_view_selected)

        # Settings save
        self.btn_settings_save.clicked.connect(self._save_settings_from_tab)

        # Enable responsive table behavior
        self._setup_responsive_tables()

    # ---------- Window Management ----------
    def _toggle_max_restore(self):
        """Toggle between maximized and normal window state"""
        if self.isMaximized():
            self.showNormal()
            self.btn_max.setText("⬜")
        else:
            self.showMaximized()
            self.btn_max.setText("❐")

    def resizeEvent(self, event):
        """Enhanced resize event handling for better responsiveness"""
        super().resizeEvent(event)
        self._update_table_responsiveness()

    def _setup_responsive_tables(self):
        """Setup responsive behavior for all tables"""
        tables = [self.tbl_bill, self.tbl_stock, self.tbl_sales, self.tbl_sale_details]
        for table in tables:
            if table:
                table.horizontalHeader().setStretchLastSection(False)
                # Enable word wrap for better text display
                table.setWordWrap(True)

    def _update_table_responsiveness(self):
        """Update table column sizes for responsiveness"""
        try:
            # Update all tables to fit content properly
            tables = [
                (self.tbl_bill, [2, 3, 4]),  # Resize specific columns, let name stretch (barcode hidden)
                (self.tbl_stock, [2, 3, 4, 5, 6, 8]),  # Let name stretch
                (self.tbl_sales, [0, 1, 2]),  # All columns resize to content
                (self.tbl_sale_details, [2, 3, 4])  # Let name stretch (barcode hidden)
            ]
            
            for table, resize_cols in tables:
                if table and table.rowCount() > 0:
                    for col in resize_cols:
                        if col < table.columnCount():
                            table.resizeColumnToContents(col)
        except Exception:
            pass

    # ---------- Settings (first-run & editing) ----------
    def _load_settings_or_first_run(self):
        """Load settings or show first-run setup dialog"""
        s = models.get_settings()
        if not s:
            # First run: ask user for info (no logos shown here by design)
            QMessageBox.information(self, "الإعداد الأول", "مرحبًا! برجاء إدخال معلومات المتجر أولًا.")
            shop_name, ok1 = QInputDialog.getText(self, "اسم المتجر", "اسم المتجر:")
            if not ok1 or not shop_name.strip():
                shop_name = "متجري"
            contact, _ = QInputDialog.getText(self, "معلومات الاتصال", "هاتف / بريد إلكتروني (اختياري):")
            location, _ = QInputDialog.getText(self, "الموقع", "العنوان / الموقع (اختياري):")
            currency, ok4 = QInputDialog.getText(self, "العملة", "اكتب رمز العملة (مثال: د.ج ، ر.س ، MAD ، USD):")
            if not ok4 or not currency.strip():
                currency = "د.ج"
            models.save_settings(shop_name.strip(), (contact or "").strip(), (location or "").strip(), currency.strip())
            s = models.get_settings()

        self._apply_settings_to_ui(s)

    def _apply_settings_to_ui(self, s):
        """Apply settings to UI elements"""
        self.lbl_title.setText(s["shop_name"])
        self.setWindowTitle(s["shop_name"])
        self.sett_shop_name.setText(s["shop_name"])
        self.sett_contact.setText(s["contact"] or "")
        self.sett_location.setText(s["location"] or "")
        self.sett_currency.setText(s["currency"])
        self.currency = s["currency"]

    def _save_settings_from_tab(self):
        """Save settings from the settings tab"""
        shop_name = self.sett_shop_name.text().strip() or "متجري"
        contact = self.sett_contact.text().strip()
        location = self.sett_location.text().strip()
        currency = self.sett_currency.text().strip() or "د.ج"
        models.save_settings(shop_name, contact, location, currency)
        s = models.get_settings()
        self._apply_settings_to_ui(s)
        self._apply_currency_to_inputs()
        self.msg("تم", "تم حفظ الإعدادات.")

    def _apply_currency_to_inputs(self):
        """Apply currency symbol to input fields"""
        self.in_price.setPrefix(f"السعر ({self.currency}): ")
        self.stk_price.setPrefix(f"السعر ({self.currency}): ")
        self.stk_qty.setPrefix("المخزون: ")
        self.in_qty.setPrefix("الكمية: ")
        # Refresh KPI and totals to show currency
        self._bill_recalc_total()
        self._load_sales_tab()

    # ---------- Categories ----------
    def _load_categories(self):
        """Load categories into combo box"""
        cats = models.get_categories()
        self.stk_cat.clear()
        for c in cats:
            self.stk_cat.addItem(c["name"], c["id"])

    def _add_new_category(self):
        """Add new category dialog"""
        name, ok = QInputDialog.getText(self, "تصنيف جديد", "اسم التصنيف:")
        if ok and name.strip():
            try:
                models.add_category(name.strip())
                self._load_categories()
                self.msg("تم", "تم إضافة التصنيف.")
            except Exception as e:
                QMessageBox.warning(self, "خطأ", f"تعذر إضافة التصنيف:\n{e}")

    # ---------- Stock Management ----------
    def _browse_photo(self):
        """Browse for product photo"""
        path, _ = QFileDialog.getOpenFileName(self, "اختر صورة", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if path:
            self.stk_photo.setText(path)
            self.set_preview_image(path)

    def _capture_photo(self):
        """Capture photo using camera"""
        if cv2 is None:
            QMessageBox.warning(self, "الكاميرا", "OpenCV غير مثبت. نفّذ:\npy -m pip install opencv-python")
            return
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            QMessageBox.warning(self, "الكاميرا", "تعذر فتح الكاميرا.")
            return
        QMessageBox.information(self, "التقاط", "سيتم فتح نافذة الكاميرا.\nاضغط مفتاح C لالتقاط الصورة، Q للإلغاء.")
        path_saved = None
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            cv2.imshow("Camera - Press C to capture, Q to cancel", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('c'):
                fname = f"photo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
                path_saved = os.path.join(ASSETS_PHOTOS_DIR, fname)
                cv2.imwrite(path_saved, frame)
                break
            elif key == ord('q'):
                break
        cap.release()
        cv2.destroyAllWindows()
        if path_saved:
            self.stk_photo.setText(path_saved)
            self.set_preview_image(path_saved)
            self.msg("تم", f"تم حفظ الصورة: {path_saved}")

    def _stock_add(self):
        """Add new stock item"""
        try:
            name = self.stk_name.text().strip()
            if not name:
                self.msg("تنبيه", "الرجاء إدخال الاسم.")
                return
            barcode = self.stk_barcode.text().strip()
            if barcode:
                if not is_valid_barcode(barcode):
                    self.msg("خطأ", "الباركود يجب أن يكون أرقامًا صحيحة (EAN-13: 13 رقم، UPC-A: 12 رقم، EAN-8: 8 أرقام)")
                    return
            cat_id = self.stk_cat.currentData()
            price = float(self.stk_price.value())
            qty = float(self.stk_qty.value())
            photo = self.stk_photo.text().strip() or None
            models.add_item(name, cat_id, barcode or None, price, qty, photo)
            self._load_stock_table()
            self.msg("تم", "تمت إضافة الصنف.")
            self._clear_stock_form()
        except Exception as e:
            QMessageBox.warning(self, "خطأ", f"تعذر إضافة الصنف:\n{e}")

    def _stock_update(self):
        """Update selected stock item"""
        row = self._selected_row(self.tbl_stock)
        if row is None:
            self.msg("تنبيه", "اختر صفًا للتعديل.")
            return
        item_id = int(self.tbl_stock.item(row, 0).text())
        try:
            name = self.stk_name.text().strip()
            if not name:
                self.msg("تنبيه", "الرجاء إدخال الاسم.")
                return
            barcode = self.stk_barcode.text().strip()
            if barcode:
                if not is_valid_barcode(barcode):
                    self.msg("خطأ", "الباركود يجب أن يكون أرقامًا صحيحة (EAN-13: 13 رقم، UPC-A: 12 رقم، EAN-8: 8 أرقام)")
                    return
            cat_id = self.stk_cat.currentData()
            price = float(self.stk_price.value())
            qty = float(self.stk_qty.value())
            photo = self.stk_photo.text().strip() or None
            models.update_item(item_id, name, cat_id, barcode or None, price, qty, photo)
            self._load_stock_table()
            self.msg("تم", "تم تعديل الصنف.")
        except Exception as e:
            QMessageBox.warning(self, "خطأ", f"تعذر تعديل الصنف:\n{e}")

    def _stock_delete(self):
        """Delete selected stock item"""
        row = self._selected_row(self.tbl_stock)
        if row is None:
            self.msg("تنبيه", "اختر صفًا للحذف.")
            return
        item_id = int(self.tbl_stock.item(row, 0).text())
        confirm = QMessageBox.question(self, "تأكيد", "سيتم حذف الصنف وجميع تفاصيل البيع المرتبطة به.\nهل أنت متأكد؟")
        if confirm == QMessageBox.Yes:
            try:
                models.delete_item(item_id)  # CASCADE removes sale_details
                self._load_stock_table()
                self.msg("تم", "تم حذف الصنف وكافة التفاصيل المرتبطة.")
            except Exception as e:
                QMessageBox.warning(self, "خطأ", f"تعذر حذف الصنف:\n{e}")

    def _clear_stock_form(self):
        """Clear stock form fields"""
        self.stk_name.clear()
        self.stk_barcode.clear()
        self.stk_price.setValue(0)
        self.stk_qty.setValue(0)
        self.stk_photo.clear()
        self.set_preview_image("")

    def _stock_fill_form_from_selection(self):
        """Fill stock form from selected table row"""
        row = self._selected_row(self.tbl_stock)
        if row is None:
            return
        self.stk_name.setText(self.tbl_stock.item(row, 1).text())
        cat_name = self.tbl_stock.item(row, 2).text()
        idx = self.stk_cat.findText(cat_name)
        if idx >= 0:
            self.stk_cat.setCurrentIndex(idx)
        barcode_item = self.tbl_stock.item(row, 3)
        self.stk_barcode.setText(barcode_item.text() if barcode_item else "")
        self.stk_price.setValue(float(self.tbl_stock.item(row, 4).text()))
        self.stk_qty.setValue(float(self.tbl_stock.item(row, 5).text()))
        photo_item = self.tbl_stock.item(row, 7)
        photo_path = photo_item.text() if photo_item else ""
        self.stk_photo.setText(photo_path)
        self.set_preview_image(photo_path)

    def _load_stock_table(self):
        """Load stock data into table with enhanced formatting"""
        items = models.get_items()
        self.tbl_stock.setRowCount(0)
        
        for r in items:
            row = self.tbl_stock.rowCount()
            self.tbl_stock.insertRow(row)
            
            # ID (hidden)
            self.tbl_stock.setItem(row, 0, QTableWidgetItem(str(r["id"])))
            
            # Name with larger, bold font
            name_item = QTableWidgetItem(r["name"])
            name_font = QFont(self.arabic_font.family(), 13, QFont.Bold)
            name_item.setFont(name_font)
            self.tbl_stock.setItem(row, 1, name_item)

            # Category
            self.tbl_stock.setItem(row, 2, QTableWidgetItem(r["category_name"] or "غير مصنّف"))
            
            # Barcode
            self.tbl_stock.setItem(row, 3, QTableWidgetItem(r["barcode"] or ""))
            
            # Price
            price_text = f"{r['price']:.0f}" if r['price'] == int(r['price']) else f"{r['price']:.2f}"
            self.tbl_stock.setItem(row, 4, QTableWidgetItem(price_text))
            
            # Stock count
            stock_text = f"{r['stock_count']:.0f}" if r['stock_count'] == int(r['stock_count']) else f"{r['stock_count']:.1f}"
            stock_item = QTableWidgetItem(stock_text)
            if (r["stock_count"] or 0) <= 0:
                stock_item.setForeground(Qt.red)
            self.tbl_stock.setItem(row, 5, stock_item)

            # Status
            status_text = "نفد المخزون" if (r["stock_count"] or 0) <= 0 else "متاح"
            status_item = QTableWidgetItem(status_text)
            if (r["stock_count"] or 0) <= 0:
                status_item.setForeground(Qt.red)
                status_item.setObjectName("OutOfStock")
            self.tbl_stock.setItem(row, 6, status_item)

            # Photo path (hidden)
            self.tbl_stock.setItem(row, 7, QTableWidgetItem(r["photo_path"] or ""))
            
            # Add date
            self.tbl_stock.setItem(row, 8, QTableWidgetItem(r["add_date"] or ""))
            
            # Category ID (hidden)
            self.tbl_stock.setItem(row, 9, QTableWidgetItem(str(r["category_id"] or "")))

            # Set row height for better readability
            self.tbl_stock.setRowHeight(row, 40)

        # Update responsiveness
        self._update_table_responsiveness()

    # ---------- Bill Management ----------
    def _handle_scanned_barcode(self):
        """
        Enhanced barcode scanning with automatic addition to bill.
        Handles hardware barcode scanners (keyboard wedge).
        """
        barcode = self.in_barcode.text().strip()
        if not barcode:
            return
            
        if not is_valid_barcode(barcode):
            self.msg("خطأ", "الباركود يجب أن يكون أرقامًا صحيحة (EAN-13: 13 رقم، UPC-A: 12 رقم، EAN-8: 8 أرقام)")
            self.in_barcode.selectAll()
            self.in_barcode.setFocus()
            return
            
        item = models.get_item_by_barcode(barcode)
        if item:
            # Auto-fill fields
            self.in_name.setText(item["name"])
            if self.chk_manual.currentIndex() == 0:  # Use DB price
                self.in_price.setValue(float(item["price"]))
            
            # Auto-add to bill with current quantity
            self._bill_add(auto_from_scan=True)
            
            # Show success message briefly
            self.msg("تم", f"تم إضافة {item['name']} إلى الفاتورة")
        else:
            self.msg("ملاحظة", "لم يتم العثور على منتج بهذا الباركود. يمكنك إدخاله يدويًا وإضافته للمخزون لاحقًا.")
            self.in_barcode.selectAll()
            self.in_barcode.setFocus()

    def _show_scanner_info(self):
        """Show information about barcode scanner setup"""
        info_text = """
معلومات ماسح الباركود:

• يدعم النظام مواسح الباركود USB (نوع لوحة المفاتيح)
• الأنواع المدعومة:
  - EAN-13 (13 رقم)
  - UPC-A (12 رقم) 
  - EAN-8 (8 أرقام)

• طريقة الاستخدام:
  1. وجه الماسح نحو الباركود
  2. اضغط الزناد أو الزر
  3. سيظهر الرقم في حقل الباركود تلقائيًا
  4. اضغط Enter أو انقر "بحث" للعثور على المنتج

• للإضافة السريعة:
  - بعد المسح، سيتم البحث تلقائيًا
  - إذا وُجد المنتج، سيُضاف للفاتورة مباشرة

ملاحظة: تأكد من أن الماسح مضبوط على وضع "لوحة المفاتيح"
        """
        QMessageBox.information(self, "معلومات ماسح الباركود", info_text)
    def _bill_find(self):
        """Find item by barcode and populate fields"""
        barcode = self.in_barcode.text().strip()
        if not barcode:
            self.msg("تنبيه", "أدخل الباركود أولًا.")
            return
            
        if not is_valid_barcode(barcode):
            self.msg("خطأ", "الباركود يجب أن يكون أرقامًا صحيحة (EAN-13: 13 رقم، UPC-A: 12 رقم، EAN-8: 8 أرقام)")
            return
            
        item = models.get_item_by_barcode(barcode)
        if item:
            self.in_name.setText(item["name"])
            if self.chk_manual.currentIndex() == 0:
                self.in_price.setValue(float(item["price"]))
            if (item["stock_count"] or 0) <= 0:
                QMessageBox.warning(self, "نفد المخزون", "هذا المنتج نفد من المخزون. يمكنك تحديث كميته من تبويب المخزون.")
        else:
            self.msg("ملاحظة", "لم يتم العثور على منتج بهذا الباركود. يمكنك إدخاله يدويًا وإضافته للمخزون لاحقًا.")

    def _bill_add(self, auto_from_scan=False):
        """Add item to current bill with real-time stock deduction"""
        barcode = self.in_barcode.text().strip()
        if barcode and not is_valid_barcode(barcode):
            self.msg("خطأ", "الباركود يجب أن يكون أرقامًا صحيحة (EAN-13: 13 رقم، UPC-A: 12 رقم، EAN-8: 8 أرقام)")
            return
            
        name = self.in_name.text().strip()
        if not name:
            self.msg("تنبيه", "أدخل الاسم.")
            return
            
        price_each = float(self.in_price.value())
        qty = float(self.in_qty.value())
        if qty <= 0:
            self.msg("تنبيه", "الكمية يجب أن تكون أكبر من صفر.")
            return

        # Get item from database
        item = models.get_item_by_barcode(barcode) if barcode else None
        item_id = item["id"] if item else None
        
        # Check stock availability
        if item and (item["stock_count"] or 0) < qty:
            reply = QMessageBox.question(
                self, "تنبيه المخزون", 
                f"الكمية المطلوبة ({qty:.0f if qty == int(qty) else qty}) أكبر من المتاح ({item['stock_count']:.0f if item['stock_count'] == int(item['stock_count']) else item['stock_count']}).\n"
                "هل تريد المتابعة؟ سيصبح المخزون سالبًا.",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        subtotal = price_each * qty
        
        # Add to bill table
        row = self.tbl_bill.rowCount()
        self.tbl_bill.insertRow(row)

        self.tbl_bill.setItem(row, 0, QTableWidgetItem(barcode or ""))
        
        # Name with larger font
        name_item = QTableWidgetItem(name)
        name_item.setFont(self._bill_name_font)
        self.tbl_bill.setItem(row, 1, name_item)

        price_text = f"{price_each:.0f}" if price_each == int(price_each) else f"{price_each:.2f}"
        qty_text = f"{qty:.0f}" if qty == int(qty) else f"{qty:.1f}"
        subtotal_text = f"{subtotal:.0f}" if subtotal == int(subtotal) else f"{subtotal:.2f}"
        
        self.tbl_bill.setItem(row, 2, QTableWidgetItem(f"{price_text} {self.currency}"))
        self.tbl_bill.setItem(row, 3, QTableWidgetItem(qty_text))
        self.tbl_bill.setItem(row, 4, QTableWidgetItem(f"{subtotal_text} {self.currency}"))
        self.tbl_bill.setItem(row, 5, QTableWidgetItem(str(item_id) if item_id else ""))

        # Set row height for better readability
        self.tbl_bill.setRowHeight(row, 45)

        # Real-time stock deduction
        if item_id:
            try:
                models.adjust_stock(item_id, -qty)
                self._load_stock_table()  # Refresh stock display
            except Exception as e:
                QMessageBox.warning(self, "خطأ في المخزون", f"تعذر تحديث المخزون:\n{e}")

        self._bill_recalc_total()

        # Reset inputs for next item
        if not auto_from_scan:
            self.in_name.clear()
            if self.chk_manual.currentIndex() == 0:
                self.in_price.setValue(0)
            self.in_qty.setValue(1.0)

        self.in_barcode.clear()
        self.in_barcode.setFocus()

    def _bill_remove_selected(self):
        """Remove selected item from bill and restore stock"""
        row = self._selected_row(self.tbl_bill)
        if row is None:
            self.msg("تنبيه", "اختر سطرًا للحذف.")
            return

        # Get item details before removal
        item_id_item = self.tbl_bill.item(row, 5)
        qty_item = self.tbl_bill.item(row, 3)
        
        item_id_text = item_id_item.text().strip() if item_id_item else ""
        qty_text = qty_item.text().strip() if qty_item else "0"
        
        # Restore stock if item exists in database
        try:
            if item_id_text:
                item_id = int(item_id_text)
                qty = float(qty_text)
                models.adjust_stock(item_id, +qty)  # Restore stock
                self._load_stock_table()  # Refresh stock display
        except Exception as e:
            QMessageBox.warning(self, "خطأ في المخزون", f"تعذر استرداد المخزون:\n{e}")
        finally:
            self.tbl_bill.removeRow(row)
            self._bill_recalc_total()

    def _bill_recalc_total(self):
        """Recalculate and display bill total"""
        total = 0.0
        for r in range(self.tbl_bill.rowCount()):
            total_item = self.tbl_bill.item(r, 4)
            if total_item:
                try:
                    # Extract numeric value from "amount currency" format
                    total += float(total_item.text().split()[0])
                except (ValueError, IndexError):
                    pass
                    
        total_text = f"{total:.0f}" if total == int(total) else f"{total:.2f}"
        self.lbl_total.setText(f"الإجمالي: {total_text} {self.currency}")
        self._update_table_responsiveness()

    def _bill_save(self):
        """Save current bill as a sale"""
        if self.tbl_bill.rowCount() == 0:
            self.msg("تنبيه", "الفاتورة فارغة.")
            return

        total = 0.0
        bill_lines = []
        
        for r in range(self.tbl_bill.rowCount()):
            barcode_item = self.tbl_bill.item(r, 0)
            name_item = self.tbl_bill.item(r, 1)
            price_item = self.tbl_bill.item(r, 2)
            qty_item = self.tbl_bill.item(r, 3)
            subtotal_item = self.tbl_bill.item(r, 4)
            item_id_item = self.tbl_bill.item(r, 5)
            
            barcode = barcode_item.text() if barcode_item else ""
            name = name_item.text() if name_item else ""
            price_each = float(price_item.text().split()[0]) if price_item else 0.0
            qty = float(qty_item.text()) if qty_item else 0.0
            subtotal = float(subtotal_item.text().split()[0]) if subtotal_item else 0.0
            item_id_text = item_id_item.text().strip() if item_id_item else ""
            item_id = int(item_id_text) if item_id_text else None
            
            total += subtotal
            bill_lines.append((item_id, barcode, name, qty, price_each))

        # Create sale record
        sale_id = models.add_sale(total_price=total)

        # Add sale details (stock already adjusted in real-time)
        for (item_id, barcode, name, qty, price_each) in bill_lines:
            if item_id is None:
                # Create new item with zero stock for unknown products
                cat = models.get_category_by_name("غير مصنّف")
                cat_id = cat["id"] if cat else None
                models.add_item(name=name, category_id=cat_id, barcode=barcode or None,
                              price=price_each, stock_count=0, photo_path=None)
                item_row = models.get_item_by_barcode(barcode) if barcode else None
                item_id = item_row["id"] if item_row else None

            if item_id:
                models.add_sale_detail(sale_id, item_id, qty, price_each)

        # Clear bill and refresh displays
        self.tbl_bill.setRowCount(0)
        self._bill_recalc_total()
        self._load_stock_table()
        self._load_sales_tab()
        
        self.msg("تم", f"تم حفظ الفاتورة بنجاح.\nرقم العملية: {sale_id}")

    def _bill_print(self):
        """Print current bill with enhanced formatting"""
        if self.tbl_bill.rowCount() == 0:
            self.msg("تنبيه", "لا توجد عناصر لطباعة الفاتورة الحالية.")
            return

        # Get shop settings
        s = models.get_settings()
        shop = s["shop_name"]
        contact = s["contact"] or ""
        location = s["location"] or ""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Build table rows
        rows_html = ""
        total = 0.0
        
        for r in range(self.tbl_bill.rowCount()):
            name_item = self.tbl_bill.item(r, 1)
            price_item = self.tbl_bill.item(r, 2)
            qty_item = self.tbl_bill.item(r, 3)
            subtotal_item = self.tbl_bill.item(r, 4)
            
            name = name_item.text() if name_item else ""
            price_each = float(price_item.text().split()[0]) if price_item else 0.0
            qty = float(qty_item.text()) if qty_item else 0.0
            subtotal = float(subtotal_item.text().split()[0]) if subtotal_item else 0.0
            
            total += subtotal
            
            # Format numbers without unnecessary decimals
            price_text = f"{price_each:.0f}" if price_each == int(price_each) else f"{price_each:.2f}"
            qty_text = f"{qty:.0f}" if qty == int(qty) else f"{qty:.1f}"
            subtotal_text = f"{subtotal:.0f}" if subtotal == int(subtotal) else f"{subtotal:.2f}"
            
            rows_html += f"""
            <tr>
                <td style="font-size:14pt;font-weight:600;">{name}</td>
                <td>{qty_text}</td>
                <td>{price_text} {self.currency}</td>
                <td>{subtotal_text} {self.currency}</td>
            </tr>
            """

        # Format total without unnecessary decimals
        total_text = f"{total:.0f}" if total == int(total) else f"{total:.2f}"

        # Create HTML invoice
        html = f"""
        <html dir="rtl">
        <head>
            <meta charset="utf-8">
            <style>
                body {{ 
                    font-family: 'Segoe UI', Arial; 
                    margin: 20px;
                    background: white;
                    color: black;
                }}
                h1 {{ 
                    margin: 0; 
                    text-align: center;
                    color: #2563eb;
                    border-bottom: 2px solid #2563eb;
                    padding-bottom: 10px;
                }}
                .header-info {{
                    text-align: center;
                    margin: 10px 0;
                    color: #64748b;
                }}
                table {{ 
                    width: 100%; 
                    border-collapse: collapse; 
                    margin-top: 20px;
                }}
                th, td {{ 
                    border: 1px solid #cbd5e1; 
                    padding: 8px; 
                    text-align: right; 
                }}
                th {{ 
                    background: #f1f5f9; 
                    font-weight: bold;
                    color: #1e293b;
                }}
                .total-row {{
                    background: #dbeafe;
                    font-weight: bold;
                    font-size: 14pt;
                }}
                .footer {{
                    margin-top: 30px;
                    text-align: center;
                    color: #64748b;
                    font-size: 10pt;
                }}
            </style>
        </head>
        <body>
            <h1>{shop}</h1>
            <div class="header-info">{location}</div>
            <div class="header-info">{contact}</div>
            <hr>
            <div style="text-align: center; margin: 15px 0;">
                <strong>التاريخ والوقت: {now}</strong>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>الاسم</th>
                        <th>الكمية</th>
                        <th>سعر الوحدة</th>
                        <th>الإجمالي</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
                <tfoot>
                    <tr class="total-row">
                        <th colspan="3" style="text-align:left;">الإجمالي النهائي</th>
                        <th>{total_text} {self.currency}</th>
                    </tr>
                </tfoot>
            </table>
            <div class="footer">
                شكرًا لتعاملكم معنا
            </div>
        </body>
        </html>
        """
        
        # Print document
        doc = QTextDocument()
        doc.setHtml(html)
        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrintDialog(printer, self)
        dialog.setWindowTitle("طباعة الفاتورة")
        if dialog.exec_() == QPrintDialog.Accepted:
            doc.print_(printer)

    # ---------- Sales Management ----------
    def _load_sales_tab(self):
        """Load sales data and KPIs"""
        # Load KPIs
        total_sales = models.get_sales_total()
        today_sales = models.get_sales_summary_today()
        latest = models.get_latest_sale()
        
        total_text = f"{total_sales:.0f}" if total_sales == int(total_sales) else f"{total_sales:.2f}"
        today_text = f"{today_sales:.0f}" if today_sales == int(today_sales) else f"{today_sales:.2f}"
        
        self.lbl_total_sales.setText(f"إجمالي المبيعات: {total_text} {self.currency}")
        self.lbl_today_sales.setText(f"مبيعات اليوم: {today_text} {self.currency}")
        
        if latest:
            latest_total_text = f"{latest['total_price']:.0f}" if latest['total_price'] == int(latest['total_price']) else f"{latest['total_price']:.2f}"
            self.lbl_latest_sale.setText(
                f"آخر عملية: #{latest['id']} - {latest['datetime']} - {latest_total_text} {self.currency}"
            )
        else:
            self.lbl_latest_sale.setText("آخر عملية: -")

        # Load sales table
        sales = models.get_sales()
        self.tbl_sales.setRowCount(0)
        
        for s in sales:
            row = self.tbl_sales.rowCount()
            self.tbl_sales.insertRow(row)
            self.tbl_sales.setItem(row, 0, QTableWidgetItem(str(s["id"])))
            self.tbl_sales.setItem(row, 1, QTableWidgetItem(s["datetime"]))
            price_text = f"{s['total_price']:.0f}" if s['total_price'] == int(s['total_price']) else f"{s['total_price']:.2f}"
            self.tbl_sales.setItem(row, 2, QTableWidgetItem(f"{price_text} {self.currency}"))
            self.tbl_sales.setRowHeight(row, 35)

        # Clear details table
        self.tbl_sale_details.setRowCount(0)
        self._update_table_responsiveness()

    def _sales_view_selected(self):
        """View details of selected sale"""
        row = self._selected_row(self.tbl_sales)
        if row is None:
            return
            
        sale_id = int(self.tbl_sales.item(row, 0).text())
        details = models.get_sale_details(sale_id)
        
        self.tbl_sale_details.setRowCount(0)
        for d in details:
            r = self.tbl_sale_details.rowCount()
            self.tbl_sale_details.insertRow(r)
            
            self.tbl_sale_details.setItem(r, 0, QTableWidgetItem(str(d["id"])))
            
            # Name with larger font
            name_item = QTableWidgetItem(d["name"])
            name_font = QFont(self.arabic_font.family(), 13, QFont.Bold)
            name_item.setFont(name_font)
            self.tbl_sale_details.setItem(r, 1, name_item)
            
            # Format numbers without unnecessary decimals
            qty_text = f"{d['quantity']:.0f}" if d['quantity'] == int(d['quantity']) else f"{d['quantity']:.1f}"
            price_text = f"{d['price_each']:.0f}" if d['price_each'] == int(d['price_each']) else f"{d['price_each']:.2f}"
            subtotal_text = f"{d['subtotal']:.0f}" if d['subtotal'] == int(d['subtotal']) else f"{d['subtotal']:.2f}"
            
            self.tbl_sale_details.setItem(r, 2, QTableWidgetItem(qty_text))
            self.tbl_sale_details.setItem(r, 3, QTableWidgetItem(f"{price_text} {self.currency}"))
            self.tbl_sale_details.setItem(r, 4, QTableWidgetItem(f"{subtotal_text} {self.currency}"))
            self.tbl_sale_details.setItem(r, 5, QTableWidgetItem(d["barcode"] or ""))  # Hidden barcode column
            
            self.tbl_sale_details.setRowHeight(r, 40)
            
        self._update_table_responsiveness()

    def _sales_delete_selected(self):
        """Delete selected sale with stock restoration"""
        row = self._selected_row(self.tbl_sales)
        if row is None:
            self.msg("تنبيه", "اختر عملية لحذفها.")
            return
            
        sale_id = int(self.tbl_sales.item(row, 0).text())
        confirm = QMessageBox.question(
            self, "تأكيد", 
            "هل تريد حذف العملية؟\nسيتم إرجاع الكميات للمخزون.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if confirm == QMessageBox.Yes:
            try:
                models.delete_sale(sale_id, restock=True)
                self._load_sales_tab()
                self._load_stock_table()
                self.msg("تم", "تم حذف العملية وإرجاع المخزون بنجاح.")
            except Exception as e:
                QMessageBox.warning(self, "خطأ", f"تعذر حذف العملية:\n{e}")


    # ---------- Utility Methods ----------
    def _selected_row(self, table):
        """Get selected row index from table"""
        rows = table.selectionModel().selectedRows()
        if not rows:
            return None
        return rows[0].row()