import sys, os

backend = r'C:\Users\谢键荣\SmartMall-AI\backend'
sys.path.insert(0, backend)
os.chdir(backend)

from app.main import app
import uvicorn

uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
