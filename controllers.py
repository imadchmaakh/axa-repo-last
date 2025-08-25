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

        # window header buttons
        self.btn_min.clicked.connect(self.showMinimized)
        self.btn_max.clicked.connect(self._toggle_max_restore)
        self.btn_close.clicked.connect(self.close)

        # Load settings; if missing, run first-time setup
        self.currency = "د.ج"
        self._load_settings_or_first_run()

        # Init data
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
        self.btn_scan_camera.clicked.connect(self._scan_via_camera)

        # Hardware scanner support: scanners “type” then send Enter.
        self.in_barcode.returnPressed.connect(self._handle_scanned_barcode)

        # Stock
        self.btn_stk_browse.clicked.connect(self._browse_photo)
        self.btn_stk_camera.clicked.connect(self._capture_photo)
        self.btn_stk_new_cat.clicked.connect(self._add_new_category)
        self.btn_stk_add.clicked.connect(self._stock_add)
        self.btn_stk_update.clicked.connect(self._stock_update)
        self.btn_stk_delete.clicked.connect(self._stock_delete)
        self.btn_stk_refresh.clicked.connect(self._load_stock_table)
        self.tbl_stock.itemSelectionChanged.connect(self._stock_fill_form_from_selection)

        # Sales
        self.btn_sale_refresh.clicked.connect(self._load_sales_tab)
        self.btn_sale_view.clicked.connect(self._sales_view_selected)
        self.btn_sale_delete.clicked.connect(self._sales_delete_selected)
        self.tbl_sales.itemSelectionChanged.connect(self._sales_view_selected)

        # Settings save
        self.btn_settings_save.clicked.connect(self._save_settings_from_tab)

    # ---------- Window ----------
    def _toggle_max_restore(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    # Ensure tables adapt on resize (no clipping; better responsiveness)
    def resizeEvent(self, event):
        super().resizeEvent(event)
        try:
            self.tbl_bill.resizeColumnsToContents()
            self.tbl_stock.resizeColumnsToContents()
            self.tbl_sales.resizeColumnsToContents()
            self.tbl_sale_details.resizeColumnsToContents()
        except Exception:
            pass

    # ---------- Settings (first-run & editing) ----------
    def _load_settings_or_first_run(self):
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
        self.lbl_title.setText(s["shop_name"])
        self.setWindowTitle(s["shop_name"])
        self.sett_shop_name.setText(s["shop_name"])
        self.sett_contact.setText(s["contact"] or "")
        self.sett_location.setText(s["location"] or "")
        self.sett_currency.setText(s["currency"])
        self.currency = s["currency"]

    def _save_settings_from_tab(self):
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
        self.in_price.setPrefix(f"السعر ({self.currency}): ")
        self.stk_price.setPrefix(f"السعر ({self.currency}): ")
        self.stk_qty.setPrefix("المخزون: ")
        self.in_qty.setPrefix("الكمية: ")
        # Refresh KPI and totals to show currency
        self._bill_recalc_total()
        self._load_sales_tab()

    # ---------- Categories ----------
    def _load_categories(self):
        cats = models.get_categories()
        self.stk_cat.clear()
        for c in cats:
            self.stk_cat.addItem(c["name"], c["id"])

    def _add_new_category(self):
        name, ok = QInputDialog.getText(self, "تصنيف جديد", "اسم التصنيف:")
        if ok and name.strip():
            try:
                models.add_category(name.strip())
                self._load_categories()
                self.msg("تم", "تم إضافة التصنيف.")
            except Exception as e:
                QMessageBox.warning(self, "خطأ", f"تعذر إضافة التصنيف:\n{e}")

    # ---------- Stock ----------
    def _browse_photo(self):
        path, _ = QFileDialog.getOpenFileName(self, "اختر صورة", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if path:
            self.stk_photo.setText(path)
            self.set_preview_image(path)

    def _capture_photo(self):
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
        try:
            name = self.stk_name.text().strip()
            if not name:
                self.msg("تنبيه", "الرجاء إدخال الاسم.")
                return
            barcode = self.stk_barcode.text().strip()
            if barcode:
                if not is_valid_barcode(barcode):
                    self.msg("خطأ", "الباركود يجب أن يكون أرقامًا بطول 8 أو 12 أو 13.")
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
                    self.msg("خطأ", "الباركود يجب أن يكون أرقامًا بطول 8 أو 12 أو 13.")
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
        self.stk_name.clear()
        self.stk_barcode.clear()
        self.stk_price.setValue(0)
        self.stk_qty.setValue(0)
        self.stk_photo.clear()
        self.set_preview_image("")

    def _stock_fill_form_from_selection(self):
        row = self._selected_row(self.tbl_stock)
        if row is None:
            return
        self.stk_name.setText(self.tbl_stock.item(row, 1).text())
        cat_name = self.tbl_stock.item(row, 2).text()
        idx = self.stk_cat.findText(cat_name)
        if idx >= 0:
            self.stk_cat.setCurrentIndex(idx)
        self.stk_barcode.setText(self.tbl_stock.item(row, 3).text() if self.tbl_stock.item(row,3) else "")
        self.stk_price.setValue(float(self.tbl_stock.item(row, 4).text()))
        self.stk_qty.setValue(float(self.tbl_stock.item(row, 5).text()))
        photo_path = self.tbl_stock.item(row, 7).text() if self.tbl_stock.item(row,7) else ""
        self.stk_photo.setText(photo_path)
        self.set_preview_image(photo_path)

    def _load_stock_table(self):
        items = models.get_items()
        self.tbl_stock.setRowCount(0)
        for r in items:
            row = self.tbl_stock.rowCount()
            self.tbl_stock.insertRow(row)
            self.tbl_stock.setItem(row, 0, QTableWidgetItem(str(r["id"])))
            # name larger
            name_item = QTableWidgetItem(r["name"])
            big_font = QFont(self._bill_name_font) if hasattr(self, "_bill_name_font") else QFont()
            big_font.setPointSize(14)
            big_font.setBold(True)
            name_item.setFont(big_font)
            self.tbl_stock.setItem(row, 1, name_item)

            self.tbl_stock.setItem(row, 2, QTableWidgetItem(r["category_name"] or "غير مصنّف"))
            self.tbl_stock.setItem(row, 3, QTableWidgetItem(r["barcode"] or ""))
            self.tbl_stock.setItem(row, 4, QTableWidgetItem(f"{r['price']}"))
            self.tbl_stock.setItem(row, 5, QTableWidgetItem(f"{r['stock_count']}"))

            status_item = QTableWidgetItem("نفد المخزون" if (r["stock_count"] or 0) <= 0 else "متاح")
            if (r["stock_count"] or 0) <= 0:
                status_item.setForeground(Qt.red)
            self.tbl_stock.setItem(row, 6, status_item)

            self.tbl_stock.setItem(row, 7, QTableWidgetItem(r["photo_path"] or ""))
            self.tbl_stock.setItem(row, 8, QTableWidgetItem(r["add_date"] or ""))
            self.tbl_stock.setItem(row, 9, QTableWidgetItem(str(r["category_id"] or "")))

        # responsive fit
        self.tbl_stock.resizeColumnsToContents()

    # ---------- Bill ----------
    def _handle_scanned_barcode(self):
        """
        Handles hardware barcode scanners (keyboard wedge).
        Behavior:
        - If barcode is valid and exists: auto-fill name & price (if DB price) and auto-add line with current qty.
        - If not found: show a friendly note (no crash), keep focus for continuous scanning.
        """
        barcode = self.in_barcode.text().strip()
        if not barcode:
            return
        if not is_valid_barcode(barcode):
            self.msg("خطأ", "الباركود يجب أن يكون أرقامًا بطول 8 أو 12 أو 13.")
            self.in_barcode.selectAll()
            self.in_barcode.setFocus()
            return
        item = models.get_item_by_barcode(barcode)
        if item:
            self.in_name.setText(item["name"])
            if self.chk_manual.currentIndex() == 0:
                self.in_price.setValue(float(item["price"]))
            # auto-add with selected qty
            self._bill_add(auto_from_scan=True)
        else:
            self.msg("ملاحظة", "لم يتم العثور على منتج بهذا الباركود. يمكنك إدخاله يدويًا وإضافته للمخزون لاحقًا.")
            self.in_barcode.selectAll()
            self.in_barcode.setFocus()

    def _bill_find(self):
        barcode = self.in_barcode.text().strip()
        if not barcode:
            self.msg("تنبيه", "أدخل الباركود أولًا.")
            return
        if not is_valid_barcode(barcode):
            self.msg("خطأ", "الباركود يجب أن يكون أرقامًا بطول 8 أو 12 أو 13.")
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
        barcode = self.in_barcode.text().strip()
        if barcode and not is_valid_barcode(barcode):
            self.msg("خطأ", "الباركود يجب أن يكون أرقامًا بطول 8 أو 12 أو 13.")
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

        item = models.get_item_by_barcode(barcode) if barcode else None
        item_id = item["id"] if item else None
        if item and (item["stock_count"] or 0) < qty:
            QMessageBox.information(self, "تنبيه المخزون", "الكمية المطلوبة أكبر من المتاح. سيتم تسجيلها وقد تصبح الكمية سالبة حتى تحديث المخزون.")

        subtotal = price_each * qty
        row = self.tbl_bill.rowCount()
        self.tbl_bill.insertRow(row)

        self.tbl_bill.setItem(row, 0, QTableWidgetItem(barcode))
        name_item = QTableWidgetItem(name)
        name_item.setFont(self._bill_name_font)   # bigger font for name
        self.tbl_bill.setItem(row, 1, name_item)

        self.tbl_bill.setItem(row, 2, QTableWidgetItem(f"{price_each:.2f} {self.currency}"))
        self.tbl_bill.setItem(row, 3, QTableWidgetItem(f"{qty}"))
        self.tbl_bill.setItem(row, 4, QTableWidgetItem(f"{subtotal:.2f} {self.currency}"))
        self.tbl_bill.setItem(row, 5, QTableWidgetItem(str(item_id) if item_id else ""))

        # increase row height for readability
        self.tbl_bill.setRowHeight(row, 36)

        # Real-time stock handling: deduct immediately when added
        if item_id:
            try:
                models.adjust_stock(item_id, -qty)
            finally:
                self._load_stock_table()

        self._bill_recalc_total()

        # Reset inputs; keep focus on barcode for fast repeated scans
        if not auto_from_scan:
            self.in_name.clear()
            if self.chk_manual.currentIndex() == 0:
                self.in_price.setValue(0)
            self.in_qty.setValue(1.0)

        self.in_barcode.clear()
        self.in_barcode.setFocus()

    def _bill_remove_selected(self):
        row = self._selected_row(self.tbl_bill)
        if row is None:
            self.msg("تنبيه", "اختر سطرًا للحذف.")
            return

        # Before removing, restore stock if item_id exists
        item_id_text = self.tbl_bill.item(row, 5).text().strip() if self.tbl_bill.item(row, 5) else ""
        qty_text = self.tbl_bill.item(row, 3).text().strip() if self.tbl_bill.item(row, 3) else "0"
        try:
            if item_id_text:
                item_id = int(item_id_text)
                qty = float(qty_text)
                models.adjust_stock(item_id, +qty)  # restore
        finally:
            self.tbl_bill.removeRow(row)
            self._bill_recalc_total()
            self._load_stock_table()

    def _bill_recalc_total(self):
        total = 0.0
        for r in range(self.tbl_bill.rowCount()):
            # column 4 contains "value currency", split
            text = self.tbl_bill.item(r, 4).text()
            try:
                total += float(text.split()[0])
            except Exception:
                pass
        self.lbl_total.setText(f"الإجمالي: {total:.2f} {self.currency}")
        # keep tables tidy
        self.tbl_bill.resizeColumnsToContents()

    def _bill_save(self):
        if self.tbl_bill.rowCount() == 0:
            self.msg("تنبيه", "الفاتورة فارغة.")
            return

        total = 0.0
        bill_lines = []
        for r in range(self.tbl_bill.rowCount()):
            barcode = self.tbl_bill.item(r, 0).text()
            name = self.tbl_bill.item(r, 1).text()
            price_each = float(self.tbl_bill.item(r, 2).text().split()[0])
            qty = float(self.tbl_bill.item(r, 3).text())
            subtotal = float(self.tbl_bill.item(r, 4).text().split()[0])
            item_id_text = self.tbl_bill.item(r, 5).text().strip()
            item_id = int(item_id_text) if item_id_text else None
            total += subtotal
            bill_lines.append((item_id, barcode, name, qty, price_each))

        sale_id = models.add_sale(total_price=total)

        # IMPORTANT: Stock was already adjusted in real-time when lines were added.
        # Here we only persist details; do NOT adjust stock again to avoid double-deducting.
        for (item_id, barcode, name, qty, price_each) in bill_lines:
            if item_id is None:
                # Create item with zero stock (as before)
                cat = models.get_category_by_name("غير مصنّف")
                cat_id = cat["id"] if cat else None
                models.add_item(name=name, category_id=cat_id, barcode=barcode or None,
                                price=price_each, stock_count=0, photo_path=None)
                item_row = models.get_item_by_barcode(barcode) if barcode else None
                item_id = item_row["id"] if item_row else None

            models.add_sale_detail(sale_id, item_id, qty, price_each)

        self.tbl_bill.setRowCount(0)
        self._bill_recalc_total()
        self._load_stock_table()
        self._load_sales_tab()
        self.msg("تم", f"تم حفظ الفاتورة. رقم العملية: {sale_id}")

    def _bill_print(self):
        # Build HTML invoice with shop info + items (no logos here per requirement)
        s = models.get_settings()
        shop = s["shop_name"]
        contact = s["contact"] or ""
        location = s["location"] or ""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if self.tbl_bill.rowCount() == 0:
            self.msg("تنبيه", "لا توجد عناصر لطباعة الفاتورة الحالية.")
            return

        rows_html = ""
        total = 0.0
        for r in range(self.tbl_bill.rowCount()):
            barcode = self.tbl_bill.item(r, 0).text()
            name = self.tbl_bill.item(r, 1).text()
            price_each = float(self.tbl_bill.item(r, 2).text().split()[0])
            qty = float(self.tbl_bill.item(r, 3).text())
            subtotal = float(self.tbl_bill.item(r, 4).text().split()[0])
            total += subtotal
            rows_html += f"""
            <tr>
                <td>{barcode}</td>
                <td style="font-size:14pt;font-weight:600;">{name}</td>
                <td>{qty}</td>
                <td>{price_each:.2f} {self.currency}</td>
                <td>{subtotal:.2f} {self.currency}</td>
            </tr>
            """

        html = f"""
        <html dir="rtl">
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: 'Segoe UI', Arial; }}
                h1 {{ margin: 0; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th, td {{ border: 1px solid #888; padding: 6px; text-align: right; }}
                th {{ background: #eee; }}
            </style>
        </head>
        <body>
            <h1>{shop}</h1>
            <div>{location}</div>
            <div>{contact}</div>
            <hr>
            <div>التاريخ والوقت: {now}</div>
            <table>
                <thead>
                    <tr>
                        <th>الباركود</th>
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
                    <tr>
                        <th colspan="4" style="text-align:left;">الإجمالي</th>
                        <th>{total:.2f} {self.currency}</th>
                    </tr>
                </tfoot>
            </table>
        </body>
        </html>
        """
        doc = QTextDocument()
        doc.setHtml(html)
        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrintDialog(printer, self)
        dialog.setWindowTitle("طباعة الفاتورة")
        if dialog.exec_() == QPrintDialog.Accepted:
            doc.print_(printer)

    # ---------- Sales ----------
    def _load_sales_tab(self):
        total_sales = models.get_sales_total()
        today_sales = models.get_sales_summary_today()
        latest = models.get_latest_sale()
        self.lbl_total_sales.setText(f"إجمالي المبيعات: {total_sales:.2f} {self.currency}")
        self.lbl_today_sales.setText(f"مبيعات اليوم: {today_sales:.2f} {self.currency}")
        if latest:
            self.lbl_latest_sale.setText(f"آخر عملية: #{latest['id']} - {latest['datetime']} - {latest['total_price']:.2f} {self.currency}")
        else:
            self.lbl_latest_sale.setText("آخر عملية: -")

        sales = models.get_sales()
        self.tbl_sales.setRowCount(0)
        for s in sales:
            row = self.tbl_sales.rowCount()
            self.tbl_sales.insertRow(row)
            self.tbl_sales.setItem(row, 0, QTableWidgetItem(str(s["id"])))
            self.tbl_sales.setItem(row, 1, QTableWidgetItem(s["datetime"]))
            self.tbl_sales.setItem(row, 2, QTableWidgetItem(f"{s['total_price']:.2f} {self.currency}"))

        self.tbl_sale_details.setRowCount(0)
        self.tbl_sales.resizeColumnsToContents()

    def _sales_view_selected(self):
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
            name_item = QTableWidgetItem(d["name"])
            name_font = QFont()
            name_font.setPointSize(14); name_font.setBold(True)
            name_item.setFont(name_font)
            self.tbl_sale_details.setItem(r, 1, name_item)
            self.tbl_sale_details.setItem(r, 2, QTableWidgetItem(d["barcode"] or ""))
            self.tbl_sale_details.setItem(r, 3, QTableWidgetItem(f"{d['quantity']}"))
            self.tbl_sale_details.setItem(r, 4, QTableWidgetItem(f"{d['price_each']:.2f} {self.currency}"))
            self.tbl_sale_details.setItem(r, 5, QTableWidgetItem(f"{d['subtotal']:.2f} {self.currency}"))
        self.tbl_sale_details.resizeColumnsToContents()

    def _sales_delete_selected(self):
        row = self._selected_row(self.tbl_sales)
        if row is None:
            self.msg("تنبيه", "اختر عملية لحذفها.")
            return
        sale_id = int(self.tbl_sales.item(row, 0).text())
        confirm = QMessageBox.question(self, "تأكيد", "هل تريد حذف العملية؟ سيتم إرجاع الكميات للمخزون.")
        if confirm == QMessageBox.Yes:
            try:
                models.delete_sale(sale_id, restock=True)
                self._load_sales_tab()
                self._load_stock_table()
                self.msg("تم", "تم حذف العملية وإرجاع المخزون.")
            except Exception as e:
                QMessageBox.warning(self, "خطأ", f"تعذر حذف العملية:\n{e}")

    # ---------- Camera barcode scan (optional) ----------
    def _scan_via_camera(self):
        if cv2 is None:
            QMessageBox.warning(self, "المسح بالكاميرا", "OpenCV غير مثبت. نفّذ:\npy -m pip install opencv-python")
            return
        if zbar_decode is None:
            QMessageBox.warning(self, "المسح بالكاميرا", "المكتبة pyzbar غير متاحة أو ZBar غير مثبت.\n"
                                                          "يمكنك استخدام ماسح USB (لوحة المفاتيح)، "
                                                          "أو تثبيت pyzbar + ZBar للمسح بالكاميرا.")
            return
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            QMessageBox.warning(self, "الكاميرا", "تعذر فتح الكاميرا.")
            return
        QMessageBox.information(self, "المسح", "سيتم فتح الكاميرا. وجّه الباركود، وسيتم تعبئة الحقل تلقائيًا.\nاضغط Q للإلغاء.")
        found_code = None
        while True:
            ret, frame = cap.read()
            if not ret: break
            codes = zbar_decode(frame)
            for c in codes:
                data = c.data.decode("utf-8")
                if data and is_valid_barcode(data):
                    found_code = data
                    break
            import cv2 as _cv2
            _cv2.imshow("Scan Barcode - Press Q to cancel", frame)
            if found_code:
                break
            key = _cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
        cap.release()
        import cv2 as _cv2
        _cv2.destroyAllWindows()
        if found_code:
            self.in_barcode.setText(found_code)
            self._handle_scanned_barcode()

    # ---------- Utils ----------
    def _selected_row(self, table):
        rows = table.selectionModel().selectedRows()
        if not rows:
            return None
        return rows[0].row()
