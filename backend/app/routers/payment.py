"""
支付路由 — 微信支付 V3 / 支付宝 / 模拟支付
集成框架:
- 微信支付 V3 API (统一下单 Native 扫码 + 支付回调验签解密)
- 支付宝电脑网站支付 alipay.trade.page.pay + 异步回调验签
- 模拟支付 (开发环境无真实支付时使用，直接将订单状态改为 paid)

依赖库 (可选，未安装时自动降级为模拟模式):
- wechatpayv3:        pip install wechatpayv3
- alipay-sdk-python:  pip install alipay-sdk-python

支付成功后联动订单状态: pending → paid，并写入 paid_at。
"""
import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db, cache_delete_pattern
from app.models import Order, User
from app.auth import get_current_user

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/api/payment", tags=["支付"])

# ====== 可选依赖: 微信支付 / 支付宝 SDK (未安装则降级为模拟模式) ======
try:
    from wechatpayv3 import WeChatPay, PayType  # type: ignore
    HAS_WXPAY_SDK = True
except ImportError:
    WeChatPay = None  # type: ignore
    PayType = None  # type: ignore
    HAS_WXPAY_SDK = False

try:
    from alipay import AliPay  # type: ignore  # alipay-sdk-python
    HAS_ALIPAY_SDK = True
except ImportError:
    AliPay = None  # type: ignore
    HAS_ALIPAY_SDK = False


# ==================== 辅助函数 ====================

def _mark_order_paid(db: Session, order: Order, payment_method: str) -> None:
    """
    将订单标记为已付款 (pending → paid)，并设置 paid_at / payment_method。
    - 幂等: 订单已为 paid 时直接返回，不重复处理。
    - 状态非法 (非 pending) 时抛出 HTTPException，阻止状态污染。
    """
    if order.status == "paid":
        logger.info("订单 %s 已是已付款状态，跳过重复处理", order.order_no)
        return
    if order.status != "pending":
        logger.warning(
            "订单 %s 当前状态为 %s (非 pending)，拒绝更新为 paid",
            order.order_no, order.status,
        )
        raise HTTPException(
            status_code=400,
            detail=f"订单当前状态为 {order.status}，无法支付",
        )
    order.status = "paid"
    order.paid_at = datetime.now()
    order.payment_method = payment_method
    db.commit()
    db.refresh(order)
    logger.info(
        "订单 %s 支付成功: 方式=%s, 金额=%.2f",
        order.order_no, payment_method, order.total_amount,
    )
    # 清理商品/管理后台相关缓存
    cache_delete_pattern("products:*")
    cache_delete_pattern("admin:*")


def _get_wxpay_client():
    """初始化微信支付 V3 客户端。未配置或未安装 SDK 时返回 None。"""
    if not HAS_WXPAY_SDK:
        logger.warning("wechatpayv3 库未安装，微信支付不可用 (pip install wechatpayv3)")
        return None
    if not settings.wxpay_enabled:
        logger.warning("微信支付未完成配置 (缺少 APPID/MCHID/API_V3_KEY/CERT_SERIAL_NO)，跳过初始化")
        return None
    try:
        with open(settings.WXPAY_PRIVATE_KEY_PATH, "r", encoding="utf-8") as f:
            private_key = f.read()
        wxpay = WeChatPay(
            wechatpay={
                "private_key": private_key,
                "cert_serial_no": settings.WXPAY_CERT_SERIAL_NO,
                "public_key": None,  # 微信支付平台公钥/证书，按需配置
            },
            parterid=settings.WXPAY_MCHID,
            appid=settings.WXPAY_APPID,
            app_secret="",
            apiv3_key=settings.WXPAY_API_V3_KEY,
            notify_url=settings.WXPAY_NOTIFY_URL,
        )
        return wxpay
    except FileNotFoundError:
        logger.error("微信支付私钥文件不存在: %s", settings.WXPAY_PRIVATE_KEY_PATH)
        return None
    except Exception as e:
        logger.error("初始化微信支付客户端失败: %s", e, exc_info=True)
        return None


def _get_alipay_client():
    """初始化支付宝客户端。未配置或未安装 SDK 时返回 None。"""
    if not HAS_ALIPAY_SDK:
        logger.warning("alipay-sdk-python 库未安装，支付宝不可用 (pip install alipay-sdk-python)")
        return None
    if not settings.alipay_enabled:
        logger.warning("支付宝未完成配置 (缺少 ALIPAY_APP_ID)，跳过初始化")
        return None
    try:
        with open(settings.ALIPAY_PRIVATE_KEY_PATH, "r", encoding="utf-8") as f:
            app_private_key = f.read()
        with open(settings.ALIPAY_PUBLIC_KEY_PATH, "r", encoding="utf-8") as f:
            alipay_public_key = f.read()
        alipay = AliPay(
            appid=settings.ALIPAY_APP_ID,
            app_notify_url=settings.ALIPAY_NOTIFY_URL,
            app_private_key_string=app_private_key,
            alipay_public_key_string=alipay_public_key,
            sign_type="RSA2",
            debug=settings.ALIPAY_SANDBOX,  # True=沙箱网关, False=正式网关
            verbose=False,
        )
        return alipay
    except FileNotFoundError as e:
        logger.error("支付宝密钥文件不存在: %s", e)
        return None
    except Exception as e:
        logger.error("初始化支付宝客户端失败: %s", e, exc_info=True)
        return None


def _decide_payment_method(method: Optional[str]) -> str:
    """
    根据请求参数 + 配置自动决定支付方式。
    返回: wxpay / alipay / mock
    优先级: 显式指定(校验可用) → 自动选择真实支付 → DEBUG 回退模拟支付。
    """
    if method:
        method = method.lower()
        if method == "wxpay":
            if HAS_WXPAY_SDK and settings.wxpay_enabled:
                return "wxpay"
            logger.warning("指定微信支付但不可用 (SDK 未安装或未配置)，将尝试自动降级")
        elif method == "alipay":
            if HAS_ALIPAY_SDK and settings.alipay_enabled:
                return "alipay"
            logger.warning("指定支付宝但不可用 (SDK 未安装或未配置)，将尝试自动降级")
        elif method == "mock":
            if settings.DEBUG:
                return "mock"
            raise HTTPException(status_code=400, detail="模拟支付仅在 DEBUG 模式下可用")
        else:
            raise HTTPException(status_code=400, detail=f"不支持的支付方式: {method}")

    # 自动选择: 优先真实支付，最后回退模拟支付
    if HAS_WXPAY_SDK and settings.wxpay_enabled:
        return "wxpay"
    if HAS_ALIPAY_SDK and settings.alipay_enabled:
        return "alipay"
    if settings.DEBUG:
        logger.info("未配置真实支付且处于 DEBUG 模式，使用模拟支付")
        return "mock"
    raise HTTPException(status_code=503, detail="未配置任何可用支付方式 (微信/支付宝均未启用)")


def _get_order_for_payment(db: Session, order_id: int, user: User) -> Order:
    """获取订单并完成权限 + 状态校验，返回可支付的订单对象。"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    if order.user_id != user.id and user.role == "user":
        raise HTTPException(status_code=403, detail="无权操作此订单")
    if order.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"订单当前状态为 {order.status}，无需支付",
        )
    return order


# ==================== 路由端点 ====================

@router.post("/create/{order_id}")
def create_payment(
    order_id: int,
    method: Optional[str] = Query(
        None, description="支付方式: wxpay / alipay / mock，留空则自动选择"
    ),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    创建支付 — 根据配置自动选择支付方式。
    返回各支付方式所需的支付参数 (微信 code_url / 支付宝跳转 URL / 模拟支付提示)。
    """
    order = _get_order_for_payment(db, order_id, user)
    payment_method = _decide_payment_method(method)
    logger.info(
        "用户 %s 为订单 %s 创建支付: 方式=%s, 金额=%.2f",
        user.id, order.order_no, payment_method, order.total_amount,
    )

    if payment_method == "wxpay":
        return _create_wxpay_payment(order)
    if payment_method == "alipay":
        return _create_alipay_payment(order)
    # mock
    return {
        "method": "mock",
        "order_id": order.id,
        "order_no": order.order_no,
        "amount": order.total_amount,
        "message": "模拟支付模式，请调用 GET /api/payment/mock/{order_id} 完成支付",
        "mock_url": f"/api/payment/mock/{order.id}",
    }


def _create_wxpay_payment(order: Order) -> dict:
    """微信支付 V3 统一下单 (Native 扫码支付)。"""
    wxpay = _get_wxpay_client()
    if wxpay is None:
        raise HTTPException(status_code=503, detail="微信支付暂不可用 (未配置或 SDK 未安装)")

    try:
        # 微信支付金额单位为分
        amount_total = int(round(order.total_amount * 100))
        code, message = wxpay.pay(
            description=f"SmartMall 订单 {order.order_no}",
            out_trade_no=order.order_no,
            amount={"total": amount_total, "currency": "CNY"},
            pay_type=PayType.NATIVE,
            notify_url=settings.WXPAY_NOTIFY_URL,
        )
        if code != 200:
            logger.error("微信支付统一下单失败 code=%s message=%s", code, message)
            raise HTTPException(status_code=502, detail=f"微信支付下单失败: {message}")

        data = json.loads(message) if isinstance(message, str) else message
        code_url = data.get("code_url")
        logger.info("微信支付统一下单成功: 订单=%s, code_url=%s", order.order_no, code_url)
        return {
            "method": "wxpay",
            "order_id": order.id,
            "order_no": order.order_no,
            "amount": order.total_amount,
            "code_url": code_url,
            "message": "请使用微信扫码完成支付",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("微信支付统一下单异常: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"微信支付下单异常: {e}")


def _create_alipay_payment(order: Order) -> dict:
    """支付宝电脑网站支付 alipay.trade.page.pay，返回跳转 URL。"""
    alipay = _get_alipay_client()
    if alipay is None:
        raise HTTPException(status_code=503, detail="支付宝暂不可用 (未配置或 SDK 未安装)")

    try:
        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order.order_no,
            total_amount=str(order.total_amount),
            subject=f"SmartMall 订单 {order.order_no}",
            return_url=settings.ALIPAY_RETURN_URL,
            notify_url=settings.ALIPAY_NOTIFY_URL,
        )
        pay_url = f"{settings.ALIPAY_GATEWAY}?{order_string}"
        logger.info("支付宝下单成功: 订单=%s, 跳转 URL 已生成", order.order_no)
        return {
            "method": "alipay",
            "order_id": order.id,
            "order_no": order.order_no,
            "amount": order.total_amount,
            "pay_url": pay_url,
            "message": "请跳转到支付宝完成支付",
        }
    except Exception as e:
        logger.error("支付宝下单异常: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"支付宝下单异常: {e}")


@router.post("/wxpay/notify")
async def wxpay_notify(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    微信支付回调 — 验签 + 解密 + 更新订单状态。
    微信要求返回 200 且 JSON {"code": "SUCCESS"} 表示处理成功。
    """
    logger.info("收到微信支付回调请求: %s %s", request.method, request.url.path)
    headers = dict(request.headers)
    try:
        body = (await request.body()).decode("utf-8")
    except Exception as e:
        logger.error("读取微信回调 body 失败: %s", e)
        return {"code": "FAIL", "message": "读取请求体失败"}

    wxpay = _get_wxpay_client()
    if wxpay is None:
        logger.error("微信支付客户端未初始化，无法处理回调")
        return {"code": "FAIL", "message": "微信支付未配置"}

    # 验签 + 解密
    try:
        result = wxpay.callback(headers, body)
    except Exception as e:
        logger.error("微信支付回调验签/解密失败: %s", e, exc_info=True)
        return {"code": "FAIL", "message": "验签失败"}

    if not result or result.get("event_type") != "TRANSACTION.SUCCESS":
        logger.warning("微信回调非成功交易事件，忽略: %s", result)
        return {"code": "SUCCESS", "message": "已接收"}

    try:
        resource = result.get("resource", {}) or {}
        out_trade_no = resource.get("out_trade_no")
        trade_state = resource.get("trade_state")
        transaction_id = resource.get("transaction_id")
        logger.info(
            "微信回调交易: out_trade_no=%s, trade_state=%s, transaction_id=%s",
            out_trade_no, trade_state, transaction_id,
        )

        if trade_state != "SUCCESS":
            logger.warning("微信回调交易状态非 SUCCESS: %s，忽略", trade_state)
            return {"code": "SUCCESS", "message": "已接收"}

        order = db.query(Order).filter(Order.order_no == out_trade_no).first()
        if not order:
            logger.error("微信回调: 订单 %s 不存在", out_trade_no)
            return {"code": "FAIL", "message": "订单不存在"}

        _mark_order_paid(db, order, "wxpay")
        return {"code": "SUCCESS", "message": "成功"}
    except HTTPException as e:
        logger.error("微信回调处理订单失败: %s", e.detail)
        return {"code": "FAIL", "message": str(e.detail)}
    except Exception as e:
        logger.error("微信回调处理异常: %s", e, exc_info=True)
        return {"code": "FAIL", "message": "内部错误"}


@router.post("/alipay/notify")
async def alipay_notify(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    支付宝异步回调 — 验签 + 更新订单状态。
    支付宝要求返回纯文本 "success" 表示处理成功，否则会定时重试。
    """
    logger.info("收到支付宝异步回调请求: %s %s", request.method, request.url.path)
    try:
        form_data = await request.form()
        data = {k: v for k, v in form_data.items()}
    except Exception as e:
        logger.error("读取支付宝回调表单失败: %s", e)
        return "fail"

    out_trade_no = data.get("out_trade_no")
    trade_status = data.get("trade_status")
    logger.info(
        "支付宝回调: out_trade_no=%s, trade_status=%s, total_amount=%s",
        out_trade_no, trade_status, data.get("total_amount"),
    )

    alipay = _get_alipay_client()
    if alipay is None:
        logger.error("支付宝客户端未初始化，无法处理回调")
        return "fail"

    # 验签: sign / sign_type 不参与签名，需先剔除
    try:
        signature = data.pop("sign", None)
        data.pop("sign_type", None)
        verified = alipay.verify(data, signature) if signature else False
    except Exception as e:
        logger.error("支付宝回调验签异常: %s", e, exc_info=True)
        return "fail"

    if not verified:
        logger.error("支付宝回调验签失败: out_trade_no=%s", out_trade_no)
        return "fail"
    logger.info("支付宝回调验签成功: out_trade_no=%s", out_trade_no)

    # 仅处理交易成功状态
    if trade_status not in ("TRADE_SUCCESS", "TRADE_FINISHED"):
        logger.info("支付宝回调交易状态 %s，无需更新订单", trade_status)
        return "success"

    try:
        order = db.query(Order).filter(Order.order_no == out_trade_no).first()
        if not order:
            logger.error("支付宝回调: 订单 %s 不存在", out_trade_no)
            return "fail"
        _mark_order_paid(db, order, "alipay")
        return "success"
    except HTTPException as e:
        logger.error("支付宝回调处理订单失败: %s", e.detail)
        return "fail"
    except Exception as e:
        logger.error("支付宝回调处理异常: %s", e, exc_info=True)
        return "fail"


@router.get("/mock/{order_id}")
def mock_payment(
    order_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    模拟支付 — 仅在 DEBUG 模式下可用。
    直接将订单状态从 pending 改为 paid，无需真实资金流转。
    """
    if not settings.DEBUG:
        raise HTTPException(status_code=403, detail="模拟支付仅在 DEBUG 模式下可用")

    order = _get_order_for_payment(db, order_id, user)
    _mark_order_paid(db, order, "mock")
    return {
        "message": "模拟支付成功",
        "order_id": order.id,
        "order_no": order.order_no,
        "status": order.status,
        "paid_at": order.paid_at,
        "payment_method": "mock",
    }
