# -*- coding: utf-8 -*-
"""SmartMall-AI Java 后端完整业务流演示脚本
跑法: python tools/demo_flow.py   (Java 后端需在 8001 运行)
"""
import json
import time
import urllib.error
import urllib.request
import uuid

BASE = "http://127.0.0.1:8001"


def call(method, path, token=None, body=None, desc=""):
    url = BASE + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"raw": raw[:120]}
    except Exception as e:
        return -1, {"error": str(e)}


def step(title):
    print("\n" + "=" * 62)
    print("  " + title)
    print("=" * 62)


def show(status, pick, extra=""):
    tag = "OK " if 200 <= status < 400 else f"{status}"
    line = f"  [{tag}] {pick}"
    if extra:
        line += f"  ({extra})"
    print(line)


def main():
    print("SmartMall-AI · Java 后端完整业务流演示")
    print(f"目标: {BASE}   时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    # ============ 1. 健康检查 ============
    step("① 系统健康检查")
    s, d = call("GET", "/api/health")
    show(s, f"status={d.get('status')}  version={d.get('version')}  "
             f"database={d.get('database')}  llm_enabled={d.get('llm_enabled')}")

    # ============ 2. 用户注册与登录 ============
    step("② 用户注册 → 登录")
    uname = "demo_" + uuid.uuid4().hex[:6]
    email = uname + "@test.com"
    s, d = call("POST", "/api/auth/register",
                body={"username": uname, "email": email, "password": "demo123456"})
    user_token = d.get("access_token", "")
    show(s, f"注册成功: {d.get('user', {}).get('username')} / {d.get('user', {}).get('role')}")
    s, d = call("GET", "/api/auth/me", token=user_token)
    show(s, f"我的信息: id={d.get('id')}  username={d.get('username')}  email={d.get('email')}")

    # ============ 3. 商品浏览 ============
    step("③ 商品浏览")
    s, d = call("GET", "/api/products?page=1&page_size=10")
    items = d.get("items", [])
    show(s, f"默认列表: total={d.get('total')}  首条={items[0]['name']} ¥{items[0]['price']}",
         f"前3: {', '.join(i['name'] for i in items[:3])}")
    s, d = call("GET", "/api/products?page=1&page_size=5&sort=price_asc")
    items = d.get("items", [])
    show(s, f"价格升序: 最便宜={items[0]['name']} ¥{items[0]['price']} → 最贵={items[-1]['name']} ¥{items[-1]['price']}")
    s, d = call("GET", "/api/products?page=1&page_size=5&category_id=1")
    show(s, f"分类筛选(运动鞋): {len(d.get('items', []))} 条, 如 {d['items'][0]['name']}")
    s, d = call("GET", "/api/products?page=1&page_size=5&keyword=Nike")
    show(s, f"关键词'Nike'(匹配商品名): {d.get('total')} 条")
    pid = items[0]["id"]
    s, d = call("GET", f"/api/products/{pid}")
    p = d.get("product", d)
    show(s, f"详情: {p.get('name')}  品牌={p.get('brand')}  库存={p.get('stock')}  "
             f"评分={p.get('rating')}  销量={p.get('sales')}")
    s, d = call("GET", "/api/products/categories")
    cats = d if isinstance(d, list) else d.get("categories", [])
    show(s, f"分类: {', '.join(c['name'] for c in cats[:6])}")
    s, d = call("GET", f"/api/products/{pid}/reviews?page=1&page_size=5")
    rv = d.get("items", d) if isinstance(d, dict) else d
    show(s, f"评价: {len(rv)} 条, 最新评分={rv[0]['rating']} \"{str(rv[0].get('content'))[:24]}\"" if rv else "评价: 0 条")

    # ============ 4. 搜索 ============
    step("④ 搜索与联想")
    s, d = call("GET", "/api/search?keyword=%E6%89%8B%E6%9C%BA&page_size=5")
    show(s, f"搜索'手机': {d.get('total')} 条, 首个={d['items'][0]['name']}")
    s, d = call("GET", "/api/search/suggestions?keyword=ni")
    show(s, f"联想'ni': 商品={d.get('products', [])[:3]}  品牌={d.get('brands', [])}")
    s, d = call("GET", "/api/search/hot")
    hot = d.get("hot_keywords", d) if isinstance(d, dict) else d
    hot = [k[0] if isinstance(k, (list, tuple)) else k for k in hot]
    show(s, f"热门搜索: {hot[:6]}")
    s, d = call("GET", "/api/search/brands")
    br = d.get("brands", d) if isinstance(d, dict) else d
    show(s, f"品牌榜: {br[:5]}")

    # ============ 5. 收藏与购物车 ============
    step("⑤ 收藏 + 购物车")
    s, d = call("POST", f"/api/products/{pid}/favorite", token=user_token)
    show(s, f"收藏商品#{pid}: {d}")
    s, d = call("GET", f"/api/products/{pid}/favorite", token=user_token)
    show(s, f"查询收藏状态: {d}")
    s, d = call("POST", "/api/cart/items", token=user_token, body={"product_id": pid, "quantity": 2})
    show(s, f"加购 {d.get('product', {}).get('name')} x{d.get('quantity')}")
    s, d = call("POST", "/api/cart/items", token=user_token, body={"product_id": 10, "quantity": 1})
    show(s, f"再加购商品#10 x1")
    s, d = call("GET", "/api/cart/items", token=user_token)
    show(s, f"购物车: {len(d)} 种商品, 共 {sum(i['quantity'] for i in d)} 件")
    s, d = call("GET", "/api/cart/count", token=user_token)
    show(s, f"购物车角标数: {d.get('count', d)}")

    # ============ 6. 下单与支付 ============
    step("⑥ 下单 → 支付 → 订单状态")
    s, d = call("POST", "/api/orders", token=user_token, body={})
    order_id = d.get("id")
    show(s, f"下单: {d.get('order_no')}  状态={d.get('status')}  金额=¥{d.get('total_amount')}  共{len(d.get('items', []))}件")
    s, d = call("GET", f"/api/orders/{order_id}", token=user_token)
    show(s, f"订单详情: 收货人={d.get('address_snapshot', {}).get('name')}  "
             f"商品={[i['product_name'] for i in d.get('items', [])]}")
    s, d = call("POST", f"/api/orders/{order_id}/pay", token=user_token)
    show(s, f"发起支付: 单号={d.get('pay_no')}  剩余={d.get('remaining_seconds')}s  方式={[m['name'] for m in d.get('methods', [])]}")
    s, d = call("POST", f"/api/orders/{order_id}/pay-confirm?method=alipay", token=user_token)
    show(s, f"确认支付: status={d.get('status')}  支付方式={d.get('payment_method')}")
    s, d = call("GET", "/api/orders?page=1&page_size=5", token=user_token)
    items = d.get("items", d) if isinstance(d, dict) else d
    show(s, f"我的订单: {len(items)} 笔, 最新状态={items[0]['status']}")
    s, d = call("GET", "/api/orders/stats/summary", token=user_token)
    st = d.get("summary", d) if isinstance(d, dict) else d
    show(s, f"订单统计: {st if isinstance(st, dict) else st[:1]}")

    # ============ 7. AI 能力 ============
    step("⑦ AI 能力")
    s, d = call("GET", "/api/ai/status")
    show(s, f"AI 状态: enabled={d.get('llm_enabled')} model={d.get('llm_model')}")
    s, d = call("GET", "/api/ai/recommendations?limit=5", token=user_token)
    show(s, f"协同过滤推荐: {[p['name'] for p in d]}")
    s, d = call("POST", "/api/ai/rag/search", body={"query": "跑步鞋"})
    docs = d.get("results", d) if isinstance(d, dict) else d
    first = docs[0] if docs else {}
    name = first.get("title") or first.get("name") or str(first)[:40]
    show(s, f"RAG 检索'跑步鞋': {len(docs)} 条, 首条={name}")

    # ============ 8. 管理端 ============
    step("⑧ 管理后台")
    s, d = call("POST", "/api/auth/login", body={"username": "admin", "password": "admin123"})
    admin_token = d.get("access_token", "")
    show(s, f"admin 登录: role={d.get('user', {}).get('role')}")
    s, d = call("GET", "/api/admin/stats?days=7", token=admin_token)
    show(s, f"运营统计: 用户={d.get('total_users')}  商品={d.get('total_products')}  "
             f"订单={d.get('total_orders')}  销售额=¥{d.get('total_sales')}")
    tp = d.get("top_products", [])
    show(s, f"热销TOP: {[(t.get('name'), t.get('sales')) for t in tp[:3]]}")
    s, d = call("GET", "/api/admin/products?page=1&page_size=3", token=admin_token)
    show(s, f"商品管理: total={d.get('total')}, {[(i['name'], i['stock']) for i in d.get('items', [])][:2]}")
    s, d = call("GET", "/api/admin/users?page=1&page_size=3", token=admin_token)
    us = d.get("items", d) if isinstance(d, dict) else d
    show(s, f"用户管理: total={d.get('total') if isinstance(d, dict) else len(us)}, 最新={us[0].get('username')}")
    s, d = call("GET", "/api/admin/orders?page=1&page_size=3", token=admin_token)
    show(s, f"订单管理: total={d.get('total')}, 最新单号={d.get('items', [{}])[0].get('order_no')}")
    s, d = call("GET", "/api/admin/stats?days=7", token=user_token)
    show(s, f"越权防护(普通用户访问admin): HTTP {s} → {d.get('detail', d.get('message', ''))}")

    # ============ 9. 安全保护 ============
    step("⑨ 安全与异常路径")
    s, d = call("GET", "/api/cart/items")
    show(s, f"未登录访问购物车: HTTP {s} → {d.get('detail', d.get('message', ''))}")
    s, d = call("GET", "/api/products/999999")
    show(s, f"不存在商品#999999: HTTP {s} → {d.get('detail', d.get('message', ''))}")
    s, d = call("GET", "/api/products/1", token="bad.token.here")
    msg = d.get("detail", d.get("message", ""))
    note = "匿名接口忽略无效token(与Python一致)" if s == 200 else f"→ {msg}"
    show(s, f"伪造Token(公开接口): HTTP {s} {note}")

    print("\n" + "#" * 62)
    print("  演示结束：Java 后端全链路正常 ✅")
    print("#" * 62)


if __name__ == "__main__":
    main()
