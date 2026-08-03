#!/usr/bin/env python3
"""
Python(FastAPI) vs Java(Spring Boot) 接口对拍。

思路：同一份数据、同一组请求，打到两个后端，逐字段比对 JSON。
两边必须连的是同一批数据（先跑 migrate_sqlite.py 把 SQLite 搬到 H2/MySQL）。

用法:
    python compare_api.py
    python compare_api.py --py http://127.0.0.1:8000 --java http://127.0.0.1:8001
    python compare_api.py --verbose        # 打印每处差异的完整路径

退出码: 0 = 全部一致, 1 = 存在差异
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

# 这些字段天生每次都不同，比对时直接摘掉
VOLATILE_KEYS = {
    "access_token",
    "token",
    "expires_in",
    "process_time",
}

# 浮点比较容差：两边一个走 Python float 一个走 Java double，
# 末位偶尔差 1 个 ULP，不算问题
FLOAT_EPS = 1e-9


class Case:
    def __init__(self, name, method, path, params=None, body=None, auth=None,
                 ignore=None, sort_key=None):
        self.name = name
        self.method = method
        self.path = path
        self.params = params or {}
        self.body = body
        self.auth = auth              # None / "user" / "admin"
        self.ignore = set(ignore or ())
        self.sort_key = sort_key


def request(base: str, method: str, path: str, params=None, body=None, token=None, timeout=30):
    url = base.rstrip("/") + path
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)

    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = "Bearer " + token

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            status = resp.status
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        status = e.code
    except Exception as e:                                   # 连不上 / 超时
        return None, {"__transport_error__": str(e)}

    try:
        return status, json.loads(raw) if raw else None
    except json.JSONDecodeError:
        return status, {"__raw__": raw[:400]}


def login(base: str, username: str, password: str):
    # Python/Java 的 UserLogin 都用 username 登录（不是 email）
    status, body = request(base, "POST", "/api/auth/login",
                           body={"username": username, "password": password})
    if status != 200 or not isinstance(body, dict):
        return None
    return body.get("access_token") or body.get("token")


def strip(node, ignore: set):
    """递归摘掉易变字段，返回可比较的结构"""
    if isinstance(node, dict):
        return {k: strip(v, ignore)
                for k, v in node.items()
                if k not in VOLATILE_KEYS and k not in ignore}
    if isinstance(node, list):
        return [strip(v, ignore) for v in node]
    return node


def diff(a, b, path="$", out=None, limit=12):
    """收集差异，返回 [(路径, 左值, 右值)]"""
    if out is None:
        out = []
    if len(out) >= limit:
        return out

    if type(a) is not type(b) and not (isinstance(a, (int, float)) and isinstance(b, (int, float))):
        out.append((path, a, b))
        return out

    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                out.append((f"{path}.{k}", "<缺失>", b[k])); continue
            if k not in b:
                out.append((f"{path}.{k}", a[k], "<缺失>")); continue
            diff(a[k], b[k], f"{path}.{k}", out, limit)
        return out

    if isinstance(a, list):
        if len(a) != len(b):
            out.append((f"{path}.length", len(a), len(b)))
            return out
        for i, (x, y) in enumerate(zip(a, b)):
            diff(x, y, f"{path}[{i}]", out, limit)
        return out

    if isinstance(a, float) or isinstance(b, float):
        if abs(float(a) - float(b)) > FLOAT_EPS:
            out.append((path, a, b))
        return out

    if a != b:
        out.append((path, a, b))
    return out


def build_cases():
    return [
        Case("健康检查", "GET", "/api/health",
             ignore={"llm_enabled", "llm_model", "database", "rate_limit"}),

        Case("商品列表-默认", "GET", "/api/products", {"page": 1, "page_size": 10}),
        Case("商品列表-价格升序", "GET", "/api/products",
             {"page": 1, "page_size": 20, "sort": "price_asc"}),
        Case("商品列表-销量降序", "GET", "/api/products",
             {"page": 2, "page_size": 12, "sort": "sales"}),
        Case("商品列表-分类筛选", "GET", "/api/products",
             {"category_id": 1, "page": 1, "page_size": 50}),
        Case("商品列表-价格区间", "GET", "/api/products",
             {"min_price": 500, "max_price": 3000, "page_size": 50}),
        Case("商品列表-关键词", "GET", "/api/products",
             {"keyword": "Nike", "page_size": 50}),
        Case("商品列表-推荐位", "GET", "/api/products",
             {"is_recommend": "true", "page_size": 50}),
        Case("商品详情", "GET", "/api/products/1"),
        Case("商品详情-不存在", "GET", "/api/products/999999"),
        Case("商品分类", "GET", "/api/products/categories"),
        Case("商品评价", "GET", "/api/products/1/reviews", {"page": 1, "page_size": 20}),

        Case("搜索-关键词", "GET", "/api/search", {"keyword": "鞋", "page_size": 20}),
        Case("搜索-关键词2", "GET", "/api/search", {"keyword": "手机", "page_size": 20}),
        Case("搜索-相关度排序", "GET", "/api/search",
             {"keyword": "Apple", "sort": "relevance", "page_size": 20}),
        Case("搜索建议", "GET", "/api/search/suggestions", {"keyword": "ni"}),
        Case("热门搜索", "GET", "/api/search/hot"),
        Case("品牌列表", "GET", "/api/search/brands"),

        Case("我的信息", "GET", "/api/auth/me", auth="user"),
        Case("购物车", "GET", "/api/cart/items", auth="user"),
        Case("购物车数量", "GET", "/api/cart/count", auth="user"),
        Case("收藏列表", "GET", "/api/products/favorites/list", auth="user"),
        Case("订单列表", "GET", "/api/orders", {"page": 1, "page_size": 20}, auth="user"),
        Case("订单统计", "GET", "/api/orders/stats/summary", auth="user"),

        Case("未登录取购物车", "GET", "/api/cart/items"),
        Case("非法 Token 商品详情", "GET", "/api/products/1"),

        Case("管理端-统计", "GET", "/api/admin/stats", {"days": 7}, auth="admin"),
        Case("管理端-商品", "GET", "/api/admin/products",
             {"page": 1, "page_size": 20}, auth="admin"),
        Case("管理端-用户", "GET", "/api/admin/users",
             {"page": 1, "page_size": 20}, auth="admin"),
        Case("管理端-订单", "GET", "/api/admin/orders",
             {"page": 1, "page_size": 20}, auth="admin"),
        Case("管理端-越权(普通用户)", "GET", "/api/admin/stats", auth="user"),

        # AI 侧：无 Key 时两边都会回"未配置"，比的是协议外壳而不是模型输出
        Case("AI 状态", "GET", "/api/ai/status",
             ignore={"llm_enabled", "llm_model", "rag_enabled", "embedding_model"}),
        Case("AI 推荐", "GET", "/api/ai/recommendations", {"limit": 5}),
        Case("RAG 检索", "POST", "/api/ai/rag/search",
             body={"query": "适合跑步的轻便鞋子", "limit": 5},
             ignore={"similarity", "matched_text"}),
        Case("RAG 检索-空查询", "POST", "/api/ai/rag/search", body={"query": ""}),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Python / Java 双后端接口对拍")
    parser.add_argument("--py", default="http://127.0.0.1:8000")
    parser.add_argument("--java", default="http://127.0.0.1:8001")
    parser.add_argument("--user", default="zhangwei")
    parser.add_argument("--user-password", default="zw123456")
    parser.add_argument("--admin", default="admin")
    parser.add_argument("--admin-password", default="admin123")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    print(f"Python: {args.py}")
    print(f"Java  : {args.java}\n")

    tokens = {}
    for role, email, pwd in (("user", args.user, args.user_password),
                             ("admin", args.admin, args.admin_password)):
        py_t = login(args.py, email, pwd)
        java_t = login(args.java, email, pwd)
        tokens[role] = (py_t, java_t)
        mark = "OK " if (py_t and java_t) else "!! "
        print(f"[{mark}] 登录 {role:<5} {email:<26} "
              f"py={'有' if py_t else '无'} java={'有' if java_t else '无'}")
    print()

    cases = build_cases()
    passed, failed = 0, []

    header = f"{'':<3}{'用例':<24}{'状态码':<14}{'结果'}"
    print(header)
    print("-" * 78)

    for case in cases:
        py_token, java_token = tokens.get(case.auth, (None, None))
        py_status, py_body = request(args.py, case.method, case.path,
                                     case.params, case.body, py_token)
        jv_status, jv_body = request(args.java, case.method, case.path,
                                     case.params, case.body, java_token)

        status_txt = f"{py_status} / {jv_status}"
        diffs = []
        if py_status != jv_status:
            diffs.append(("$.__status__", py_status, jv_status))
        else:
            a = strip(py_body, case.ignore)
            b = strip(jv_body, case.ignore)
            diffs = diff(a, b)

        if diffs:
            failed.append((case, diffs))
            print(f"{'X':<3}{case.name:<24}{status_txt:<14}{len(diffs)} 处差异")
        else:
            passed += 1
            print(f"{'v':<3}{case.name:<24}{status_txt:<14}一致")

    print("-" * 78)
    print(f"通过 {passed}/{len(cases)}，差异 {len(failed)}\n")

    if failed:
        print("=" * 78)
        print("差异明细 (左=Python 右=Java)")
        print("=" * 78)
        for case, diffs in failed:
            print(f"\n### {case.name}  [{case.method} {case.path}]")
            for path, left, right in (diffs if args.verbose else diffs[:6]):
                ls, rs = repr(left), repr(right)
                if len(ls) > 90:
                    ls = ls[:90] + "..."
                if len(rs) > 90:
                    rs = rs[:90] + "..."
                print(f"  {path}\n      py   = {ls}\n      java = {rs}")
            if not args.verbose and len(diffs) > 6:
                print(f"  ... 另有 {len(diffs) - 6} 处，加 --verbose 查看")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
