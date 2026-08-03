package com.smartmall.controller;

import com.smartmall.common.ApiException;
import com.smartmall.common.CacheService;
import com.smartmall.dto.OrderDtos;
import com.smartmall.entity.*;
import com.smartmall.repository.*;
import com.smartmall.security.CurrentUser;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.PageRequest;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

/**
 * 订单接口，对应 routers/orders.py。
 *
 * <p>状态机: pending → paid → shipped → completed，另有 cancelled / refunded 分支。
 * 普通用户只能做「取消」和「确认收货」，其余流转需管理员。
 */
@RestController
@RequestMapping("/api/orders")
@RequiredArgsConstructor
public class OrderController {

    /** 合法状态流转表，与 Python 版 ORDER_TRANSITIONS 一致 */
    static final Map<String, List<String>> TRANSITIONS = Map.of(
            "pending", List.of("paid", "cancelled"),
            "paid", List.of("shipped", "refunded", "cancelled"),
            "shipped", List.of("completed", "refunded"),
            "completed", List.of(),
            "cancelled", List.of(),
            "refunded", List.of()
    );

    /** 用户自助可做的流转 */
    static final Map<String, List<String>> USER_ALLOWED = Map.of(
            "pending", List.of("cancelled"),
            "shipped", List.of("completed")
    );

    static final Map<String, String> STATUS_LABELS = Map.of(
            "pending", "待付款",
            "paid", "已付款",
            "shipped", "已发货",
            "completed", "已完成",
            "cancelled", "已取消",
            "refunded", "已退款"
    );

    private static final DateTimeFormatter ORDER_NO_FMT = DateTimeFormatter.ofPattern("yyyyMMddHHmmss");

    private final OrderRepository orderRepository;
    private final OrderItemRepository orderItemRepository;
    private final CartItemRepository cartItemRepository;
    private final ProductRepository productRepository;
    private final AddressRepository addressRepository;
    private final CacheService cache;

    @GetMapping({"", "/"})
    public List<OrderDtos.OrderRes> listOrders(
            @RequestParam(required = false) String status,
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(name = "page_size", defaultValue = "20") int pageSize,
            @CurrentUser User user) {

        if (page < 1) throw ApiException.badRequest("page 必须 >= 1");
        if (pageSize < 1 || pageSize > 100) throw ApiException.badRequest("page_size 需在 1-100 之间");

        var pageable = PageRequest.of(page - 1, pageSize);
        var result = (status == null || status.isBlank())
                ? orderRepository.findByUserIdOrderByCreatedAtDescIdDesc(user.getId(), pageable)
                : orderRepository.findByUserIdAndStatusOrderByCreatedAtDescIdDesc(user.getId(), status, pageable);

        return withItems(result.getContent());
    }

    @PostMapping({"", "/"})
    @Transactional
    public OrderDtos.OrderRes createOrder(@Valid @RequestBody OrderDtos.OrderCreateReq req,
                                          @CurrentUser User user) {
        List<CartItem> cartItems = cartItemRepository.findByUserIdOrderByIdAsc(user.getId());
        if (cartItems.isEmpty()) {
            throw ApiException.badRequest("购物车为空");
        }

        // 地址快照：没传 address_id 时退化为用户名 + 手机号，与 Python 版一致
        Map<String, Object> snapshot = new LinkedHashMap<>();
        snapshot.put("name", user.getUsername());
        snapshot.put("phone", (user.getPhone() == null || user.getPhone().isBlank())
                ? "13800138000" : user.getPhone());
        if (req.addressId() != null) {
            Address addr = addressRepository.findByIdAndUserId(req.addressId(), user.getId()).orElse(null);
            if (addr != null) {
                snapshot = new LinkedHashMap<>();
                snapshot.put("name", addr.getName());
                snapshot.put("phone", addr.getPhone());
                snapshot.put("province", addr.getProvince());
                snapshot.put("city", addr.getCity());
                snapshot.put("district", addr.getDistrict());
                snapshot.put("detail", addr.getDetail());
            }
        }

        // 先算总价并校验库存，任一商品不足就整单失败
        double total = 0;
        List<OrderItem> pending = new ArrayList<>();
        List<Product> touched = new ArrayList<>();
        for (CartItem ci : cartItems) {
            Product p = productRepository.findById(ci.getProductId()).orElse(null);
            if (p == null) {
                continue;
            }
            if (p.getStock() < ci.getQuantity()) {
                throw ApiException.badRequest("商品 " + p.getName() + " 库存不足 (剩余 " + p.getStock() + ")");
            }
            total += p.getPrice() * ci.getQuantity();
            pending.add(OrderItem.builder()
                    .productId(p.getId())
                    .productName(p.getName())
                    .productImage(p.getImage())
                    .price(p.getPrice())
                    .quantity(ci.getQuantity())
                    .build());
            touched.add(p);
        }
        if (pending.isEmpty()) {
            throw ApiException.badRequest("购物车商品无效");
        }

        Order order = Order.builder()
                .userId(user.getId())
                .orderNo(generateOrderNo())
                .status("pending")
                .totalAmount(total)
                .addressSnapshot(snapshot)
                .note(req.note())
                .build();
        order = orderRepository.save(order);

        for (int i = 0; i < pending.size(); i++) {
            OrderItem oi = pending.get(i);
            oi.setOrderId(order.getId());
            Product p = touched.get(i);
            p.setStock(p.getStock() - oi.getQuantity());
            p.setSales(p.getSales() + oi.getQuantity());
        }
        orderItemRepository.saveAll(pending);
        productRepository.saveAll(touched);
        cartItemRepository.deleteAll(cartItems);

        cache.deletePattern("products:*");
        cache.deletePattern("admin:*");
        return OrderDtos.OrderRes.from(order, pending);
    }

    /** 必须放在 /{orderId} 之前，否则 "stats" 会被当成 orderId */
    @GetMapping("/stats/summary")
    public Map<String, Object> stats(@CurrentUser User user) {
        List<Order> orders = orderRepository
                .findByUserIdOrderByCreatedAtDescIdDesc(user.getId(), PageRequest.of(0, Integer.MAX_VALUE))
                .getContent();

        Map<String, Object> s = new LinkedHashMap<>();
        s.put("total", orders.size());
        for (String st : List.of("pending", "paid", "shipped", "completed", "cancelled")) {
            s.put(st, orders.stream().filter(o -> st.equals(o.getStatus())).count());
        }
        s.put("total_amount", orders.stream()
                .filter(o -> !"cancelled".equals(o.getStatus()))
                .mapToDouble(Order::getTotalAmount).sum());
        return s;
    }

    @GetMapping("/{orderId}")
    public OrderDtos.OrderRes getOrder(@PathVariable Long orderId, @CurrentUser User user) {
        Order order = orderRepository.findById(orderId)
                .orElseThrow(() -> ApiException.notFound("订单不存在"));
        if (!order.getUserId().equals(user.getId()) && "user".equals(user.getRole())) {
            throw ApiException.forbidden("无权查看此订单");
        }
        return OrderDtos.OrderRes.from(order, orderItemRepository.findByOrderIdOrderByIdAsc(orderId));
    }

    @PutMapping("/{orderId}/status")
    @Transactional
    public OrderDtos.OrderRes updateStatus(@PathVariable Long orderId,
                                           @Valid @RequestBody OrderDtos.OrderStatusUpdateReq req,
                                           @CurrentUser User user) {
        Order order = orderRepository.findById(orderId)
                .orElseThrow(() -> ApiException.notFound("订单不存在"));

        boolean isOwner = order.getUserId().equals(user.getId());
        boolean isAdmin = "admin".equals(user.getRole());
        if (!isOwner && !isAdmin) {
            throw ApiException.forbidden("无权操作此订单");
        }

        List<String> allowed = isAdmin
                ? TRANSITIONS.getOrDefault(order.getStatus(), List.of())
                : USER_ALLOWED.getOrDefault(order.getStatus(), List.of());

        if (!allowed.contains(req.status())) {
            String prefix = isAdmin ? "订单状态不能从" : "您不能将订单从";
            throw ApiException.badRequest(prefix
                    + "「" + label(order.getStatus()) + "」变为「" + label(req.status()) + "」");
        }

        order.setStatus(req.status());
        LocalDateTime now = LocalDateTime.now();
        switch (req.status()) {
            case "paid" -> order.setPaidAt(now);
            case "shipped" -> {
                order.setShippedAt(now);
                if (req.trackingNo() != null) order.setTrackingNo(req.trackingNo());
                if (req.logisticsCompany() != null) order.setLogisticsCompany(req.logisticsCompany());
            }
            case "completed" -> order.setCompletedAt(now);
            case "cancelled", "refunded" -> restoreStock(orderId);
            default -> {
            }
        }

        orderRepository.save(order);
        cache.deletePattern("products:*");
        cache.deletePattern("admin:*");
        return OrderDtos.OrderRes.from(order, orderItemRepository.findByOrderIdOrderByIdAsc(orderId));
    }

    /** 取消/退款时把库存和销量还回去 */
    private void restoreStock(Long orderId) {
        List<OrderItem> items = orderItemRepository.findByOrderIdOrderByIdAsc(orderId);
        List<Product> changed = new ArrayList<>();
        for (OrderItem item : items) {
            productRepository.findById(item.getProductId()).ifPresent(p -> {
                p.setStock(p.getStock() + item.getQuantity());
                p.setSales(Math.max(0, p.getSales() - item.getQuantity()));
                changed.add(p);
            });
        }
        productRepository.saveAll(changed);
    }

    static String label(String status) {
        return STATUS_LABELS.getOrDefault(status, status);
    }

    static String generateOrderNo() {
        String rand = UUID.randomUUID().toString().substring(0, 4).toUpperCase();
        return "SM" + LocalDateTime.now().format(ORDER_NO_FMT) + rand;
    }

    /** 批量补明细，避免 N+1 */
    private List<OrderDtos.OrderRes> withItems(List<Order> orders) {
        if (orders.isEmpty()) {
            return List.of();
        }
        List<Long> ids = orders.stream().map(Order::getId).toList();
        Map<Long, List<OrderItem>> grouped = new HashMap<>();
        for (OrderItem oi : orderItemRepository.findByOrderIdInOrderByIdAsc(ids)) {
            grouped.computeIfAbsent(oi.getOrderId(), k -> new ArrayList<>()).add(oi);
        }
        return orders.stream()
                .map(o -> OrderDtos.OrderRes.from(o, grouped.getOrDefault(o.getId(), List.of())))
                .toList();
    }
}
