import sqlite3
import os

DB_NAME = "store.db"

def get_connection():
    """
    Get database connection with proper configuration and timeout handling.
    - timeout=10 sec: Prevents 'database is locked' errors during fast UI operations.
    - WAL mode: Better concurrency for read/write.
    """
    conn = sqlite3.connect(DB_NAME, timeout=10)  # Added timeout for stability
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")       # Allows concurrent reads during writes
    conn.execute("PRAGMA synchronous = NORMAL;")     # Good balance of safety and performance
    return conn

def _table_has_item_fk_cascade_on_sale_details(conn):
    """Check if sale_details table has CASCADE foreign key for items"""
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_key_list(sale_details)")
    fks = cur.fetchall()
    for fk in fks:
        if fk["table"] == "items" and fk["from"] == "item_id" and fk["on_delete"].lower() == "cascade":
            return True
    return False

def setup_database():
    """Setup database with all required tables and indexes"""
    must_seed = not os.path.exists(DB_NAME)
    conn = get_connection()
    cur = conn.cursor()

    # Settings table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY CHECK (id=1),
        shop_name TEXT NOT NULL,
        contact TEXT,
        location TEXT,
        currency TEXT NOT NULL
    );
    """)

    # Categories table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Items table
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
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
    );
    """)

    # Sales table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        datetime TEXT NOT NULL,
        total_price REAL NOT NULL DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Sale details table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sale_details (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sale_id INTEGER NOT NULL,
        item_id INTEGER NOT NULL,
        quantity REAL NOT NULL,
        price_each REAL NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (sale_id) REFERENCES sales(id) ON DELETE CASCADE,
        FOREIGN KEY (item_id) REFERENCES items(id) -- Will migrate to CASCADE
    );
    """)

    conn.commit()

    # Ensure CASCADE for item_id in sale_details
    if not _table_has_item_fk_cascade_on_sale_details(conn):
        print("Migrating sale_details table to add CASCADE foreign key...")
        cur.execute("PRAGMA foreign_keys = OFF;")
        conn.commit()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS _sale_details_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            quantity REAL NOT NULL,
            price_each REAL NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sale_id) REFERENCES sales(id) ON DELETE CASCADE,
            FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
        );
        """)

        # Copy data
        cur.execute("""
        INSERT INTO _sale_details_new (id, sale_id, item_id, quantity, price_each, created_at)
        SELECT id, sale_id, item_id, quantity, price_each, COALESCE(created_at, datetime('now'))
        FROM sale_details;
        """)

        cur.execute("DROP TABLE sale_details;")
        cur.execute("ALTER TABLE _sale_details_new RENAME TO sale_details;")
        conn.commit()

        cur.execute("PRAGMA foreign_keys = ON;")
        conn.commit()
        print("Migration completed successfully.")

    # Create indexes for performance
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_items_barcode ON items(barcode);",
        "CREATE INDEX IF NOT EXISTS idx_items_category ON items(category_id);",
        "CREATE INDEX IF NOT EXISTS idx_items_stock ON items(stock_count);",
        "CREATE INDEX IF NOT EXISTS idx_sales_datetime ON sales(datetime);",
        "CREATE INDEX IF NOT EXISTS idx_sale_details_sale_id ON sale_details(sale_id);",
        "CREATE INDEX IF NOT EXISTS idx_sale_details_item_id ON sale_details(item_id);",
    ]
    for sql in indexes:
        cur.execute(sql)

    conn.commit()

    # Seed data if new DB
    if must_seed:
        print("Seeding initial data...")
        cur.execute("INSERT OR IGNORE INTO categories(name) VALUES (?)", ("غير مصنّف",))
        for cat in ["مواد غذائية", "مشروبات", "منظفات", "أدوات منزلية", "قرطاسية"]:
            cur.execute("INSERT OR IGNORE INTO categories(name) VALUES (?)", (cat,))
        conn.commit()
        print("Initial data seeded.")

    conn.close()
    print("Database setup completed successfully.")

def backup_database(backup_path=None):
    """Create a backup of the database"""
    if not backup_path:
        from datetime import datetime
        backup_path = f"store_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    import shutil
    shutil.copy2(DB_NAME, backup_path)
    return backup_path

def get_database_stats():
    """Return stats: table counts & DB size"""
    conn = get_connection()
    cur = conn.cursor()
    stats = {}
    for table in ['categories', 'items', 'sales', 'sale_details']:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        stats[f"{table}_count"] = cur.fetchone()[0]
    stats['db_size_bytes'] = os.path.getsize(DB_NAME) if os.path.exists(DB_NAME) else 0
    stats['db_size_mb'] = round(stats['db_size_bytes'] / (1024*1024), 2)
    conn.close()
    return stats
