import sys, os
# Add backend to path
backend = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend)
os.chdir(backend)

# Import the app object directly (not as string)
from app.main import app

import uvicorn
print("=" * 50)
print("SmartMall AI starting on http://0.0.0.0:8001")
print("=" * 50)
uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
