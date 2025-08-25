from datetime import datetime, date
from database import get_connection

# ---------- Settings ----------
def get_settings():
    """Get application settings"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, shop_name, contact, location, currency FROM settings WHERE id=1")
    row = cur.fetchone()
    conn.close()
    return row

def save_settings(shop_name: str, contact: str, location: str, currency: str):
    """Save application settings"""
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
    """Add new product category"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO categories (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()

def get_categories():
    """Get all product categories"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM categories ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return rows

def get_category_by_name(name: str):
    """Get category by name"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM categories WHERE name = ?", (name,))
    row = cur.fetchone()
    conn.close()
    return row

# ---------- Items/Products ----------
def add_item(name, category_id, barcode, price, stock_count, photo_path, add_date=None):
    """Add new product item"""
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
    """Update existing product item"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE items SET name=?, category_id=?, barcode=?, price=?, stock_count=?, photo_path=?
        WHERE id=?
    """, (name, category_id, barcode, price, stock_count, photo_path, item_id))
    conn.commit()
    conn.close()

def delete_item(item_id):
    """Delete product item (CASCADE will remove related sale_details)"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM items WHERE id=?", (item_id,))
    conn.commit()
    conn.close()

def get_items():
    """Get all product items with category information"""
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
    """Get product item by barcode"""
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
    """Get product item by ID"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM items WHERE id=?", (item_id,))
    row = cur.fetchone()
    conn.close()
    return row

def adjust_stock(item_id, delta_quantity):
    """Adjust stock quantity for an item (positive to add, negative to subtract)"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE items SET stock_count = stock_count + ? WHERE id=?", (delta_quantity, item_id))
    conn.commit()
    conn.close()

def get_low_stock_items(threshold=5):
    """Get items with stock below threshold"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT i.id, i.name, i.stock_count, c.name AS category_name
        FROM items i
        LEFT JOIN categories c ON c.id = i.category_id
        WHERE i.stock_count <= ?
        ORDER BY i.stock_count ASC
    """, (threshold,))
    rows = cur.fetchall()
    conn.close()
    return rows

# ---------- Sales ----------
def add_sale(total_price, dt=None):
    """Add new sale record"""
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
    """Add sale detail record"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO sale_details (sale_id, item_id, quantity, price_each)
        VALUES (?, ?, ?, ?)
    """, (sale_id, item_id, quantity, price_each))
    conn.commit()
    conn.close()

def get_sales(limit=200):
    """Get sales records with limit"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, datetime, total_price FROM sales ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_sale_details(sale_id):
    """Get details for a specific sale"""
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
    """Get total sales for today"""
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
    """Get total sales amount"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(SUM(total_price), 0) FROM sales")
    total = cur.fetchone()[0]
    conn.close()
    return total

def get_latest_sale():
    """Get the most recent sale"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, datetime, total_price FROM sales ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    conn.close()
    return row

def delete_sale(sale_id, restock=True):
    """Delete sale and optionally restore stock"""
    if restock:
        # Get sale details before deletion to restore stock
        details = get_sale_details(sale_id)
        for d in details:
            adjust_stock(d["item_id"], d["quantity"])
    
    conn = get_connection()
    cur = conn.cursor()
    # Delete sale details first (foreign key constraint)
    cur.execute("DELETE FROM sale_details WHERE sale_id=?", (sale_id,))
    # Delete sale record
    cur.execute("DELETE FROM sales WHERE id=?", (sale_id,))
    conn.commit()
    conn.close()

# ---------- Analytics and Reports ----------
def get_sales_by_date_range(start_date, end_date):
    """Get sales within date range"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, datetime, total_price 
        FROM sales 
        WHERE substr(datetime,1,10) BETWEEN ? AND ?
        ORDER BY datetime DESC
    """, (start_date, end_date))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_top_selling_items(limit=10):
    """Get top selling items by quantity"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT i.name, i.barcode, SUM(sd.quantity) as total_sold,
               SUM(sd.quantity * sd.price_each) as total_revenue
        FROM sale_details sd
        JOIN items i ON i.id = sd.item_id
        GROUP BY sd.item_id
        ORDER BY total_sold DESC
        LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows

def get_sales_summary_by_category():
    """Get sales summary grouped by category"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT c.name as category_name, 
               COUNT(DISTINCT sd.sale_id) as num_sales,
               SUM(sd.quantity) as total_quantity,
               SUM(sd.quantity * sd.price_each) as total_revenue
        FROM sale_details sd
        JOIN items i ON i.id = sd.item_id
        LEFT JOIN categories c ON c.id = i.category_id
        GROUP BY i.category_id
        ORDER BY total_revenue DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows