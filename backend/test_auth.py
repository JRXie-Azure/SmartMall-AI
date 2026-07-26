"""Quick auth test script"""
import urllib.request
import json

BASE = "http://localhost:8001"

# 1. Health check
try:
    r = urllib.request.urlopen(f"{BASE}/api/health")
    print(f"[OK] Health: {r.read().decode()}")
except Exception as e:
    print(f"[FAIL] Health: {e}")
    exit()

# 2. Login
try:
    data = json.dumps({"username": "admin", "password": "admin123"}).encode()
    req = urllib.request.Request(f"{BASE}/api/auth/login", data=data, headers={"Content-Type": "application/json"})
    r = urllib.request.urlopen(req)
    body = json.loads(r.read().decode())
    print(f"[OK] Login response: {body}")
    token = body.get("access_token", "")
    print(f"[OK] Token: {token[:50]}...")
except Exception as e:
    print(f"[FAIL] Login: {e}")
    exit()

# 3. Test cart with token
try:
    req = urllib.request.Request(f"{BASE}/api/cart/items", headers={"Authorization": f"Bearer {token}"})
    r = urllib.request.urlopen(req)
    body = r.read().decode()
    print(f"[OK] Cart GET: {body[:200]}")
except Exception as e:
    print(f"[FAIL] Cart GET: {e}")

# 4. Test add to cart
try:
    data = json.dumps({"product_id": 1, "quantity": 1}).encode()
    req = urllib.request.Request(f"{BASE}/api/cart/items", data=data, headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
    r = urllib.request.urlopen(req)
    body = r.read().decode()
    print(f"[OK] Cart POST: {body[:200]}")
except Exception as e:
    print(f"[FAIL] Cart POST: {e}")

# 5. Test orders
try:
    req = urllib.request.Request(f"{BASE}/api/orders", headers={"Authorization": f"Bearer {token}"})
    r = urllib.request.urlopen(req)
    body = r.read().decode()
    print(f"[OK] Orders GET: {body[:200]}")
except Exception as e:
    print(f"[FAIL] Orders GET: {e}")
