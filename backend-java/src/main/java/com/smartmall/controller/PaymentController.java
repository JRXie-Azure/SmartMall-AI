package com.smartmall.controller;

import com.smartmall.common.ApiException;
import com.smartmall.common.CacheService;
import com.smartmall.entity.Order;
import com.smartmall.entity.OrderItem;
import com.smartmall.entity.User;
import com.smartmall.repository.OrderItemRepository;
import com.smartmall.repository.OrderRepository;
import com.smartmall.security.CurrentUser;
import lombok.RequiredArgsConstructor;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.*;

/**
 * 支付接口，对应 routers/payments.py —— 模拟支付，不接真实渠道。
 * 挂在 /api/orders 前缀下，与 Python 版保持一致。
 */
@RestController
@RequestMapping("/api/orders")
@RequiredArgsConstructor
public class PaymentController {

    private static final int PAYMENT_TIMEOUT_MINUTES = 30;

    /** LinkedHashMap 保证返回顺序与 Python dict 字面量一致 */
    private static final Map<String, Map<String, String>> PAYMENT_METHODS = new LinkedHashMap<>();

    static {
        PAYMENT_METHODS.put("alipay", Map.of("name", "支付宝", "icon", "fab fa-alipay", "color", "#1677FF"));
        PAYMENT_METHODS.put("wechat", Map.of("name", "微信支付", "icon", "fab fa-weixin", "color", "#07C160"));
        PAYMENT_METHODS.put("credit_card", Map.of("name", "银行卡支付", "icon", "fas fa-credit-card", "color", "#F56C6C"));
    }

    private final OrderRepository orderRepository;
    private final OrderItemRepository orderItemRepository;
    private final CacheService cache;

    @PostMapping("/{orderId}/pay")
    public Map<String, Object> startPayment(@PathVariable Long orderId, @CurrentUser User user) {
        Order order = requirePayableOrder(orderId, user);

        long remaining = remainingSeconds(order.getCreatedAt());
        String payNo = "PAY" + LocalDateTime.now().format(
                java.time.format.DateTimeFormatter.ofPattern("yyyyMMddHHmmss"))
                + UUID.randomUUID().toString().substring(0, 6).toUpperCase();

        List<Map<String, Object>> items = new ArrayList<>();
        for (OrderItem i : orderItemRepository.findByOrderIdOrderByIdAsc(orderId)) {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("id", i.getId());
            m.put("product_id", i.getProductId());
            m.put("product_name", i.getProductName());
            m.put("product_image", i.getProductImage());
            m.put("price", i.getPrice());
            m.put("quantity", i.getQuantity());
            items.add(m);
        }

        List<Map<String, Object>> methods = new ArrayList<>();
        PAYMENT_METHODS.forEach((k, v) -> {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("key", k);
            m.put("name", v.get("name"));
            m.put("icon", v.get("icon"));
            m.put("color", v.get("color"));
            methods.add(m);
        });

        Map<String, Object> body = new LinkedHashMap<>();
        body.put("pay_no", payNo);
        body.put("order_id", order.getId());
        body.put("order_no", order.getOrderNo());
        body.put("total_amount", order.getTotalAmount());
        body.put("items", items);
        body.put("remaining_seconds", remaining);
        body.put("timeout_minutes", PAYMENT_TIMEOUT_MINUTES);
        body.put("methods", methods);
        return body;
    }

    @PostMapping("/{orderId}/pay-confirm")
    @Transactional
    public Map<String, Object> confirmPayment(@PathVariable Long orderId,
                                              @RequestParam(defaultValue = "alipay") String method,
                                              @CurrentUser User user) {
        Order order = requirePayableOrder(orderId, user);

        if (!PAYMENT_METHODS.containsKey(method)) {
            throw ApiException.badRequest("不支持的支付方式: " + method);
        }

        LocalDateTime now = LocalDateTime.now();
        order.setStatus("paid");
        order.setPaymentMethod(method);
        order.setPaidAt(now);
        orderRepository.save(order);

        cache.deletePattern("products:*");
        cache.deletePattern("admin:*");

        Map<String, Object> body = new LinkedHashMap<>();
        body.put("success", true);
        body.put("order_id", order.getId());
        body.put("order_no", order.getOrderNo());
        body.put("status", "paid");
        body.put("payment_method", PAYMENT_METHODS.get(method).get("name"));
        body.put("paid_at", now.toString());
        body.put("message", "支付成功！");
        return body;
    }

    private Order requirePayableOrder(Long orderId, User user) {
        Order order = orderRepository.findById(orderId)
                .orElseThrow(() -> ApiException.notFound("订单不存在"));
        if (!order.getUserId().equals(user.getId())) {
            throw ApiException.forbidden("无权操作此订单");
        }
        if (!"pending".equals(order.getStatus())) {
            throw ApiException.badRequest("订单状态不可支付");
        }
        if (order.getCreatedAt() != null
                && Duration.between(order.getCreatedAt(), LocalDateTime.now())
                .toMinutes() > PAYMENT_TIMEOUT_MINUTES) {
            throw ApiException.badRequest("订单已超时，请重新下单");
        }
        return order;
    }

    private static long remainingSeconds(LocalDateTime createdAt) {
        if (createdAt == null) {
            return PAYMENT_TIMEOUT_MINUTES * 60L;
        }
        long elapsed = Duration.between(createdAt, LocalDateTime.now()).getSeconds();
        return Math.max(0, PAYMENT_TIMEOUT_MINUTES * 60L - elapsed);
    }
}
