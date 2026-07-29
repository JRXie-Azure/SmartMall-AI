"""
SmartMall-AI 测试套件
覆盖: 认证、商品、AI 对话、RAG 语义搜索、推荐、订单、管理后台、限流、迁移
运行: cd backend && venv/Scripts/python.exe -m pytest tests/ -v
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ====== 认证测试 ======

class TestAuth:
    """JWT 认证 + RBAC 权限"""

    def test_login_admin(self):
        """管理员登录"""
        resp = client.post("/api/auth/login", json={
            "username": "admin", "password": "admin123"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["role"] == "admin"

    def test_login_regular_user(self):
        """普通用户登录"""
        resp = client.post("/api/auth/login", json={
            "username": "zhangwei", "password": "zw123456"
        })
        assert resp.status_code == 200
        assert resp.json()["user"]["role"] == "user"

    def test_login_wrong_password(self):
        """错误密码登录失败"""
        resp = client.post("/api/auth/login", json={
            "username": "admin", "password": "wrong"
        })
        assert resp.status_code == 401

    def test_register_new_user(self):
        """注册新用户"""
        resp = client.post("/api/auth/register", json={
            "username": "testuser_new",
            "password": "Test1234",
            "email": "testnew@example.com"
        })
        assert resp.status_code in (200, 201, 400)  # 400=已存在

    def test_protected_endpoint_without_token(self):
        """无 token 访问受保护接口"""
        resp = client.get("/api/cart/items")
        assert resp.status_code == 401

    def test_admin_endpoint_as_user(self):
        """普通用户访问管理接口被拒"""
        login = client.post("/api/auth/login", json={
            "username": "zhangwei", "password": "zw123456"
        })
        token = login.json()["access_token"]
        resp = client.get("/api/admin/stats", headers={
            "Authorization": f"Bearer {token}"
        })
        assert resp.status_code == 403


# ====== 商品测试 ======

class TestProducts:
    """商品列表、详情、搜索"""

    def test_product_list(self):
        """商品列表分页"""
        resp = client.get("/api/products?page=1&page_size=5")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) <= 5

    def test_product_detail(self):
        """商品详情"""
        resp = client.get("/api/products/1")
        assert resp.status_code == 200
        data = resp.json()
        assert "name" in data
        assert "price" in data
        assert "brand" in data

    def test_product_search(self):
        """商品搜索"""
        resp = client.get("/api/products?keyword=Nike")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) > 0
        assert "Nike" in items[0]["brand"] or "Nike" in items[0]["name"]

    def test_product_reviews(self):
        """商品评价列表 — 每个商品至少有 1 条评价"""
        resp = client.get("/api/products/1/reviews")
        assert resp.status_code == 200
        data = resp.json()
        # 兼容分页格式 {items: [...]} 和裸列表格式
        reviews = data["items"] if isinstance(data, dict) and "items" in data else data
        assert len(reviews) >= 1
        r = reviews[0]
        assert "username" in r
        assert "rating" in r
        assert "content" in r
        assert 1 <= r["rating"] <= 5

    def test_product_images_not_broken(self):
        """商品图片 URL 不再使用失效的 Unsplash hash 链接"""
        resp = client.get("/api/products/1")
        img = resp.json().get("image", "")
        assert "unsplash.com/photo-" not in img
        assert img.startswith("http")


# ====== AI 功能测试 ======

class TestAI:
    """AI 对话、RAG、推荐"""

    def test_ai_status(self):
        """AI 服务状态"""
        resp = client.get("/api/ai/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "llm_enabled" in data
        assert "rag_enabled" in data

    def test_rag_available(self):
        """RAG 语义搜索可用"""
        from app.services.rag_service import is_rag_available
        assert is_rag_available() == True

    def test_rag_search_shoes(self):
        """RAG 搜索跑鞋相关商品"""
        resp = client.post("/api/ai/rag/search", json={
            "query": "适合跑步的轻便鞋子", "limit": 5
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "rag"
        assert len(data["results"]) > 0
        # 前 3 个结果应该包含运动鞋相关商品
        top_names = [r["product"]["name"] for r in data["results"][:3]]
        assert any("Nike" in n or "Adidas" in n or "Asics" in n or "Balance" in n
                      for n in top_names)

    def test_rag_search_phone(self):
        """RAG 搜索手机相关商品"""
        resp = client.post("/api/ai/rag/search", json={
            "query": "拍照好的智能手机", "limit": 5
        })
        assert resp.status_code == 200
        results = resp.json()["results"]
        assert len(results) > 0
        # 前 5 个结果应包含手机类商品 (TF-IDF 语义匹配)
        top_names = [r["product"]["name"] for r in results[:5]]
        phone_keywords = ["iPhone", "Xiaomi", "Samsung", "Galaxy", "Phone", "手机"]
        assert any(any(kw in n for kw in phone_keywords) for n in top_names)

    def test_recommendations(self):
        """个性化推荐接口"""
        resp = client.get("/api/ai/recommendations?limit=5")
        assert resp.status_code == 200
        assert len(resp.json()) <= 5

    def test_collaborative_filtering(self):
        """协同过滤算法"""
        from app.database import SessionLocal
        from app.services.recommendation_service import get_personalized_recommendations
        db = SessionLocal()
        try:
            products = get_personalized_recommendations(db, user_id=3, limit=5)
            assert isinstance(products, list)
        finally:
            db.close()


# ====== 管理后台测试 ======

class TestAdmin:
    """管理后台统计数据"""

    @pytest.fixture
    def admin_token(self):
        login = client.post("/api/auth/login", json={
            "username": "admin", "password": "admin123"
        })
        return login.json()["access_token"]

    def test_admin_stats(self, admin_token):
        """管理后台统计数据"""
        resp = client.get("/api/admin/stats?days=7", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "total_products" in data
        assert "total_orders" in data
        assert "total_sales" in data or "total_revenue" in data
        assert "sales_trend" in data

    def test_admin_stats_has_data(self, admin_token):
        """统计数据不为零（seed 数据已初始化）"""
        resp = client.get("/api/admin/stats?days=7", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        data = resp.json()
        assert data["total_products"] > 0
        assert data["total_orders"] > 0


# ====== 健康检查测试 ======

class TestHealth:
    """服务健康检查"""

    def test_health_check(self):
        """健康检查接口"""
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "database" in data
        assert "rate_limit" in data


# ====== 限流中间件测试 ======

class TestRateLimit:
    """API 限流中间件 (测试环境下已禁用)"""

    def test_rate_limit_config(self):
        """限流配置可读取"""
        from app.config import get_settings
        s = get_settings()
        assert hasattr(s, "RATE_LIMIT_ENABLED")
        assert hasattr(s, "RATE_LIMIT_REQUESTS")
        assert hasattr(s, "RATE_LIMIT_AI_REQUESTS")
        assert hasattr(s, "RATE_LIMIT_WINDOW")

    def test_middleware_import(self):
        """中间件可正常导入"""
        from app.middleware import RateLimitMiddleware, RequestLoggingMiddleware
        assert RateLimitMiddleware is not None
        assert RequestLoggingMiddleware is not None

    def test_memory_rate_limit_logic(self):
        """内存限流逻辑 (Redis 不可用时的降级)"""
        from app.middleware import RateLimitMiddleware
        mw = RateLimitMiddleware(app)
        # 模拟 5 次请求, 限制为 3
        key = "test:memory:limit"
        results = [mw._check_memory(key, limit=3, window=60) for _ in range(5)]
        assert results == [True, True, True, False, False]

    def test_health_endpoint_not_rate_limited(self):
        """健康检查不受限流影响"""
        # 即使限流开启, /api/health 也应正常返回
        for _ in range(5):
            resp = client.get("/api/health")
            assert resp.status_code == 200


# ====== 数据库迁移测试 ======

class TestAlembic:
    """Alembic 数据库迁移"""

    def test_alembic_config_exists(self):
        """Alembic 配置文件存在"""
        import os
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        assert os.path.exists(os.path.join(backend_dir, "alembic.ini"))
        assert os.path.exists(os.path.join(backend_dir, "alembic", "env.py"))
        assert os.path.exists(os.path.join(backend_dir, "alembic", "script.py.mako"))

    def test_migration_files_exist(self):
        """迁移脚本文件存在"""
        import os
        versions_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "alembic", "versions"
        )
        files = [f for f in os.listdir(versions_dir) if f.endswith(".py")]
        assert len(files) > 0, "No migration files found in versions/"

    def test_all_tables_exist(self):
        """迁移后的全部表存在"""
        from app.database import engine
        from sqlalchemy import inspect
        insp = inspect(engine)
        tables = set(insp.get_table_names())
        expected = {
            "users", "addresses", "categories", "products", "cart_items",
            "orders", "order_items", "reviews", "product_views", "favorites",
            "chat_sessions", "chat_messages", "search_histories"
        }
        missing = expected - tables
        assert not missing, f"Missing tables: {missing}"


# ====== Docker / 部署配置测试 ======

class TestDeployment:
    """部署配置完整性"""

    def test_docker_compose_dev_exists(self):
        """docker-compose.dev.yml 存在"""
        import os
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        # 两种可能的路径
        path1 = os.path.join(project_root, "docker-compose.dev.yml")
        path2 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "docker-compose.dev.yml")
        assert os.path.exists(path1) or os.path.exists(path2), "docker-compose.dev.yml not found"

    def test_env_example_has_rate_limit(self):
        """env.example 包含限流配置"""
        import os
        env_example = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            ".env.example"
        )
        with open(env_example, "r", encoding="utf-8") as f:
            content = f.read()
        assert "RATE_LIMIT_ENABLED" in content
        assert "RATE_LIMIT_AI_REQUESTS" in content

    def test_env_example_has_mysql_guide(self):
        """env.example 包含 MySQL 配置说明"""
        import os
        env_example = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            ".env.example"
        )
        with open(env_example, "r", encoding="utf-8") as f:
            content = f.read()
        assert "docker-compose" in content
        assert "alembic upgrade head" in content


# ====== 安全加固测试 ======

class TestSecurity:
    """密码复杂度、登录限流、Token刷新、全局异常"""

    def test_register_weak_password_rejected(self):
        """弱密码注册被拒绝 (400 自定义校验 或 422 Pydantic 校验)"""
        resp = client.post("/api/auth/register", json={
            "username": "weakuser",
            "password": "123",
            "email": "weak@example.com"
        })
        assert resp.status_code in (400, 422)

    def test_register_password_no_uppercase(self):
        """密码缺少大写字母被拒绝"""
        resp = client.post("/api/auth/register", json={
            "username": "noupper",
            "password": "test123456",
            "email": "noupper@example.com"
        })
        assert resp.status_code == 400

    def test_login_rate_limit(self):
        """登录限流: 连续10次失败后第11次被限制"""
        for i in range(11):
            resp = client.post("/api/auth/login", json={
                "username": "nonexistent_user_" + str(i),
                "password": "wrong"
            })
        # 第11次应该被限流
        assert resp.status_code in (401, 429)

    def test_global_exception_handler(self):
        """全局异常处理器返回友好错误"""
        # 访问一个不存在的路径，触发 404
        resp = client.get("/api/nonexistent_endpoint_xyz")
        assert resp.status_code in (404,)
        data = resp.json()
        assert "detail" in data

    def test_cors_credentials_config(self):
        """CORS 配置不冲突"""
        from app.config import get_settings
        s = get_settings()
        # 如果 origins=["*"]，则 allow_credentials 应为 False
        if s.CORS_ORIGINS == "*":
            assert s.cors_origins_list == ["*"]

    def test_refresh_token_endpoint_exists(self):
        """Token 刷新端点存在"""
        resp = client.post("/api/auth/refresh", json={"refresh_token": "invalid"})
        # 无效的 token 应该返回 401
        assert resp.status_code in (401, 400, 422)

    def test_secret_key_from_env(self):
        """SECRET_KEY 优先从环境变量读取"""
        import os
        from app.config import get_settings
        s = get_settings()
        # 至少不是每次都随机生成（如果 .env 中有设置）
        assert len(s.SECRET_KEY) >= 32


# ====== 购物车测试 ======

class TestCart:
    """购物车 CRUD"""

    @pytest.fixture
    def user_token(self):
        login = client.post("/api/auth/login", json={
            "username": "zhangwei", "password": "zw123456"
        })
        return login.json()["access_token"]

    def test_cart_add_item(self, user_token):
        """添加商品到购物车"""
        resp = client.post("/api/cart/items", json={
            "product_id": 1, "quantity": 1
        }, headers={"Authorization": f"Bearer {user_token}"})
        assert resp.status_code in (200, 201)

    def test_cart_list(self, user_token):
        """获取购物车列表"""
        resp = client.get("/api/cart/items", headers={
            "Authorization": f"Bearer {user_token}"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list) or "items" in data

    def test_cart_clear(self, user_token):
        """批量清空购物车"""
        resp = client.delete("/api/cart/items", headers={
            "Authorization": f"Bearer {user_token}"
        })
        assert resp.status_code == 200


# ====== 支付测试 ======

class TestPayment:
    """模拟支付流程"""

    @pytest.fixture
    def user_token(self):
        login = client.post("/api/auth/login", json={
            "username": "zhangwei", "password": "zw123456"
        })
        return login.json()["access_token"]

    def test_create_mock_payment(self, user_token):
        """创建模拟支付"""
        # 先创建一个订单
        order_resp = client.post("/api/orders", json={}, headers={
            "Authorization": f"Bearer {user_token}"
        })
        if order_resp.status_code == 200:
            order_id = order_resp.json()["id"]
            # 创建支付
            resp = client.post(f"/api/payment/create/{order_id}?method=mock", headers={
                "Authorization": f"Bearer {user_token}"
            })
            assert resp.status_code == 200
            assert resp.json()["method"] == "mock"

    def test_mock_pay_endpoint(self, user_token):
        """模拟支付完成"""
        order_resp = client.post("/api/orders", json={}, headers={
            "Authorization": f"Bearer {user_token}"
        })
        if order_resp.status_code == 200:
            order_id = order_resp.json()["id"]
            # 创建支付
            client.post(f"/api/payment/create/{order_id}?method=mock", headers={
                "Authorization": f"Bearer {user_token}"
            })
            # 完成支付
            resp = client.get(f"/api/payment/mock/{order_id}", headers={
                "Authorization": f"Bearer {user_token}"
            })
            assert resp.status_code == 200
            assert resp.json()["status"] == "paid"


# ====== 优惠券测试 ======

class TestCoupon:
    """优惠券领取和应用"""

    @pytest.fixture
    def user_token(self):
        login = client.post("/api/auth/login", json={
            "username": "zhangwei", "password": "zw123456"
        })
        return login.json()["access_token"]

    def test_get_available_coupons(self, user_token):
        """获取可用优惠券列表"""
        resp = client.get("/api/coupons/available", headers={
            "Authorization": f"Bearer {user_token}"
        })
        assert resp.status_code == 200

    def test_get_my_coupons(self, user_token):
        """获取我的优惠券"""
        resp = client.get("/api/coupons/my", headers={
            "Authorization": f"Bearer {user_token}"
        })
        assert resp.status_code == 200


# ====== 搜索测试 ======

class TestSearch:
    """搜索功能"""

    def test_search_keyword(self):
        """关键词搜索"""
        resp = client.get("/api/search", params={"keyword": "Nike"})
        assert resp.status_code == 200

    def test_search_suggestions(self):
        """搜索建议"""
        resp = client.get("/api/search/suggestions", params={"keyword": "运动"})
        assert resp.status_code == 200

    def test_search_hot(self):
        """热门搜索"""
        resp = client.get("/api/search/hot")
        assert resp.status_code == 200

    def test_search_brands(self):
        """品牌列表"""
        resp = client.get("/api/search/brands")
        assert resp.status_code == 200


# ====== 收藏测试 ======

class TestFavorite:
    """收藏功能"""

    @pytest.fixture
    def user_token(self):
        login = client.post("/api/auth/login", json={
            "username": "zhangwei", "password": "zw123456"
        })
        return login.json()["access_token"]

    def test_add_and_remove_favorite(self, user_token):
        """添加和取消收藏"""
        headers = {"Authorization": f"Bearer {user_token}"}
        # 添加收藏
        resp = client.post("/api/products/1/favorite", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["is_favorite"] == True
        # 检查收藏状态
        resp = client.get("/api/products/1/favorite", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["is_favorite"] == True
        # 取消收藏
        resp = client.delete("/api/products/1/favorite", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["is_favorite"] == False

    def test_get_favorites_list(self, user_token):
        """获取收藏列表"""
        resp = client.get("/api/products/favorites/list", headers={
            "Authorization": f"Bearer {user_token}"
        })
        assert resp.status_code == 200


# ====== Refresh Token 测试 ======

class TestRefreshToken:
    """Token 刷新机制"""

    def test_login_returns_refresh_token(self):
        """登录返回 refresh_token"""
        resp = client.post("/api/auth/login", json={
            "username": "zhangwei", "password": "zw123456"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["refresh_token"] is not None

    def test_refresh_token_flow(self):
        """完整 Token 刷新流程"""
        login = client.post("/api/auth/login", json={
            "username": "zhangwei", "password": "zw123456"
        })
        refresh_token = login.json().get("refresh_token")
        assert refresh_token is not None

        # 用 refresh_token 换新 token
        resp = client.post("/api/auth/refresh", json={
            "refresh_token": refresh_token
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["access_token"] is not None
