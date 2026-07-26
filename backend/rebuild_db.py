"""Rebuild database from scratch with updated models and seed data."""
import os
import sys
import shutil

# Set working directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 1. Clear __pycache__
for root, dirs, files in os.walk('.'):
    for d in dirs:
        if d == '__pycache__':
            path = os.path.join(root, d)
            shutil.rmtree(path, ignore_errors=True)
            print(f"  Cleared: {path}")

# 2. Delete old database
db_path = os.path.join('.', 'smartmall.db')
if os.path.exists(db_path):
    os.remove(db_path)
    print("  Old database deleted")
else:
    print("  No existing database found")

# 3. Create tables from updated models
from app.database import engine, Base
Base.metadata.create_all(bind=engine)
print("  Tables created with latest model schema")

# 4. Seed data
from app.seed import seed
seed()
print("  Seed data inserted successfully!")

print("\n=== DATABASE REBUILD COMPLETE ===")
