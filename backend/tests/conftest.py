import pytest


@pytest.fixture(autouse=True)
def clear_rate_limit():
    """每个测试前清除登录限流计数, 避免测试间互相影响"""
    from app.routers.auth import _login_attempts
    _login_attempts.clear()
    yield
    _login_attempts.clear()
