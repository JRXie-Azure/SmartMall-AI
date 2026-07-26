"""Test JWT encode/decode directly"""
from jose import jwt
from app.config import get_settings

settings = get_settings()
print(f"SECRET_KEY: {settings.SECRET_KEY}")
print(f"ALGORITHM: {settings.ALGORITHM}")

# Encode
payload = {"sub": 1, "exp": 9999999999}
token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
print(f"Encoded token: {token}")

# Decode
try:
    decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    print(f"Decoded payload: {decoded}")
    print("[OK] JWT encode/decode works!")
except Exception as e:
    print(f"[FAIL] JWT decode: {e}")

# Also test the actual token from login
import urllib.request, json
data = json.dumps({"username": "admin", "password": "admin123"}).encode()
req = urllib.request.Request("http://localhost:8001/api/auth/login", data=data, headers={"Content-Type": "application/json"})
r = urllib.request.urlopen(req)
body = json.loads(r.read().decode())
login_token = body["access_token"]
print(f"\nLogin token: {login_token}")

# Decode login token
try:
    decoded = jwt.decode(login_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    print(f"[OK] Login token decoded: {decoded}")
except Exception as e:
    print(f"[FAIL] Login token decode: {e}")

# Now test the actual get_current_user logic
from app.database import get_db
from app.models import User
db = next(get_db())
user_id = decoded.get("sub")
print(f"\nUser ID from token: {user_id}")
user = db.query(User).filter(User.id == user_id).first()
if user:
    print(f"[OK] User found: {user.username} (id={user.id})")
else:
    print(f"[FAIL] User with id={user_id} not found!")

# Test the actual dependency
from fastapi import HTTPException
from app.auth import get_current_user
from fastapi.security import OAuth2PasswordBearer
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Simulate what FastAPI does
print(f"\nToken header check: Bearer {login_token[:20]}...")
print(f"Token starts with expected prefix: {login_token.startswith('eyJ')}")
