import sqlite3
import os

DB_NAME = "store.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def _table_has_item_fk_cascade_on_sale_details(conn):
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_key_list(sale_details)")
    fks = cur.fetchall()
    for fk in fks:
        if fk["table"] == "items" and fk["from"] == "item_id" and fk["on_delete"].lower() == "cascade":
            return True
    return False

def setup_database():
    must_seed = not os.path.exists(DB_NAME)
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY CHECK (id=1),
        shop_name TEXT NOT NULL,
        contact TEXT,
        location TEXT,
        currency TEXT NOT NULL
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category_id INTEGER,
        barcode TEXT UNIQUE,
        price REAL NOT NULL DEFAULT 0,
        stock_count REAL NOT NULL DEFAULT 0,
        photo_path TEXT,
        add_date TEXT,
        FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        datetime TEXT NOT NULL,
        total_price REAL NOT NULL DEFAULT 0
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS sale_details (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sale_id INTEGER NOT NULL,
        item_id INTEGER NOT NULL,
        quantity REAL NOT NULL,
        price_each REAL NOT NULL,
        FOREIGN KEY (sale_id) REFERENCES sales(id) ON DELETE CASCADE,
        FOREIGN KEY (item_id) REFERENCES items(id) -- migrated to CASCADE below if needed
    );
    """)

    conn.commit()

    # migrate sale_details.item_id to ON DELETE CASCADE if needed
    if not _table_has_item_fk_cascade_on_sale_details(conn):
        cur.execute("PRAGMA foreign_keys = OFF;")
        conn.commit()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS _sale_details_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            quantity REAL NOT NULL,
            price_each REAL NOT NULL,
            FOREIGN KEY (sale_id) REFERENCES sales(id) ON DELETE CASCADE,
            FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
        );
        """)
        cur.execute("""
        INSERT INTO _sale_details_new (id, sale_id, item_id, quantity, price_each)
        SELECT id, sale_id, item_id, quantity, price_each FROM sale_details;
        """)
        cur.execute("DROP TABLE sale_details;")
        cur.execute("ALTER TABLE _sale_details_new RENAME TO sale_details;")
        conn.commit()
        cur.execute("PRAGMA foreign_keys = ON;")
        conn.commit()

    if must_seed:
        cur.execute("INSERT OR IGNORE INTO categories(name) VALUES (?)", ("غير مصنّف",))
        # Settings will be filled on first run via UI, but ensure a row exists?
        # We leave it empty so first-run dialog shows.
        conn.commit()

    conn.close()

if __name__ == "__main__":
    setup_database()
