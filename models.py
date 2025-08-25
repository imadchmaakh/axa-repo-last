from datetime import datetime, date
from database import get_connection

# ---------- Settings ----------
def get_settings():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, shop_name, contact, location, currency FROM settings WHERE id=1")
    row = cur.fetchone()
    conn.close()
    return row

def save_settings(shop_name: str, contact: str, location: str, currency: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO settings (id, shop_name, contact, location, currency)
        VALUES (1, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
          shop_name=excluded.shop_name,
          contact=excluded.contact,
          location=excluded.location,
          currency=excluded.currency
    """, (shop_name, contact, location, currency))
    conn.commit()
    conn.close()

# ---------- Categories ----------
def add_category(name: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO categories (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()

def get_categories():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM categories ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return rows

def get_category_by_name(name: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM categories WHERE name = ?", (name,))
    row = cur.fetchone()
    conn.close()
    return row

# ---------- Items ----------
def add_item(name, category_id, barcode, price, stock_count, photo_path, add_date=None):
    if not add_date:
        add_date = datetime.now().isoformat(timespec="seconds")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO items (name, category_id, barcode, price, stock_count, photo_path, add_date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (name, category_id, barcode, price, stock_count, photo_path, add_date))
    conn.commit()
    conn.close()

def update_item(item_id, name, category_id, barcode, price, stock_count, photo_path):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE items SET name=?, category_id=?, barcode=?, price=?, stock_count=?, photo_path=?
        WHERE id=?
    """, (name, category_id, barcode, price, stock_count, photo_path, item_id))
    conn.commit()
    conn.close()

def delete_item(item_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM items WHERE id=?", (item_id,))
    conn.commit()
    conn.close()

def get_items():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT i.id, i.name, i.barcode, i.price, i.stock_count, i.photo_path, i.add_date,
               c.name AS category_name, i.category_id
        FROM items i
        LEFT JOIN categories c ON c.id = i.category_id
        ORDER BY i.id DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows

def get_item_by_barcode(barcode):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, name, barcode, price, stock_count, photo_path, category_id
        FROM items WHERE barcode=?
    """, (barcode,))
    row = cur.fetchone()
    conn.close()
    return row

def get_item_by_id(item_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM items WHERE id=?", (item_id,))
    row = cur.fetchone()
    conn.close()
    return row

def adjust_stock(item_id, delta_quantity):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE items SET stock_count = stock_count + ? WHERE id=?", (delta_quantity, item_id))
    conn.commit()
    conn.close()

# ---------- Sales ----------
def add_sale(total_price, dt=None):
    if not dt:
        dt = datetime.now().isoformat(timespec="seconds")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO sales (datetime, total_price) VALUES (?,?)", (dt, total_price))
    sale_id = cur.lastrowid
    conn.commit()
    conn.close()
    return sale_id

def add_sale_detail(sale_id, item_id, quantity, price_each):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO sale_details (sale_id, item_id, quantity, price_each)
        VALUES (?, ?, ?, ?)
    """, (sale_id, item_id, quantity, price_each))
    conn.commit()
    conn.close()

def get_sales(limit=200):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, datetime, total_price FROM sales ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_sale_details(sale_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT sd.id, sd.item_id, i.name, i.barcode, sd.quantity, sd.price_each,
               (sd.quantity*sd.price_each) AS subtotal
        FROM sale_details sd
        JOIN items i ON i.id = sd.item_id
        WHERE sd.sale_id=?
        ORDER BY sd.id
    """, (sale_id,))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_sales_summary_today():
    today = date.today().isoformat()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT COALESCE(SUM(total_price), 0)
        FROM sales
        WHERE substr(datetime,1,10)=?
    """, (today,))
    total_today = cur.fetchone()[0]
    conn.close()
    return total_today

def get_sales_total():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(SUM(total_price), 0) FROM sales")
    total = cur.fetchone()[0]
    conn.close()
    return total

def get_latest_sale():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, datetime, total_price FROM sales ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    conn.close()
    return row

def delete_sale(sale_id, restock=True):
    if restock:
        details = get_sale_details(sale_id)
        for d in details:
            adjust_stock(d["item_id"], d["quantity"])
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM sale_details WHERE sale_id=?", (sale_id,))
    cur.execute("DELETE FROM sales WHERE id=?", (sale_id,))
    conn.commit()
    conn.close()
