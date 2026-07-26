"""数据库迁移：添加新字段"""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), "smartmall.db")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Add new columns to products table
columns = [
    ("brand", "VARCHAR(100) DEFAULT ''"),
    ("is_recommend", "BOOLEAN DEFAULT 0"),
    ("is_new", "BOOLEAN DEFAULT 0"),
    ("is_sale", "BOOLEAN DEFAULT 0"),
]

for col_name, col_type in columns:
    try:
        cursor.execute(f"ALTER TABLE products ADD COLUMN {col_name} {col_type}")
        print(f"  + Added column: {col_name}")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e).lower():
            print(f"  - Column {col_name} already exists, skipping")
        else:
            raise

# Delete old seed data and re-seed
cursor.execute("DELETE FROM products")
print("  - Old product data cleared")

conn.commit()
conn.close()

# Now run seed
from app.seed import seed
seed()
print("\n[MIGRATION OK] Database updated successfully!")
