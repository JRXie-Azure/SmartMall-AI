package com.smartmall.controller;

import com.fasterxml.jackson.core.type.TypeReference;
import com.smartmall.common.ApiException;
import com.smartmall.common.CacheService;
import com.smartmall.dto.ProductDtos;
import com.smartmall.entity.Order;
import com.smartmall.entity.OrderItem;
import com.smartmall.entity.Product;
import com.smartmall.entity.User;
import com.smartmall.repository.*;
import com.smartmall.security.CurrentUser;
import com.smartmall.security.Roles;
import com.smartmall.service.RagService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;

import java.sql.Date;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

/** 管理后台接口，对应 routers/admin.py。所有端点都要求 admin 角色 */
@RestController
@RequestMapping("/api/admin")
@RequiredArgsConstructor
public class AdminController {

    private static final DateTimeFormatter DAY = DateTimeFormatter.ofPattern("yyyy-MM-dd");

    private final ProductRepository productRepository;
    private final OrderRepository orderRepository;
    private final OrderItemRepository orderItemRepository;
    private final UserRepository userRepository;
    private final RagService ragService;
    private final CacheService cache;

    // ====== 统计看板 ======

    /**
     * 管理后台统计（含 ECharts 需要的时间序列）。
     *
     * <p>注意一个刻意保留的口径：日期区间是 [now-days, now)，即最后一天是「昨天」，
     * 今天不计入。Python 版 {@code for i in range(days)} 就是这个效果，
     * 为了让两套后端的 /api/admin/stats 能逐字节比对，这里不做「修正」。
     */
    @GetMapping("/stats")
    @Transactional(readOnly = true)
    public Map<String, Object> getStats(@RequestParam(defaultValue = "30") int days,
                                        @CurrentUser User admin) {
        Roles.requireAdmin(admin);
        if (days < 1 || days > 365) {
            throw new ApiException(422, "days: 需在 1-365 之间");
        }

        String cacheKey = "admin:stats:" + days;
        Map<String, Object> cached = cache.get(cacheKey, new TypeReference<Map<String, Object>>() {
        });
        if (cached != null) {
            return cached;
        }

        LocalDateTime now = LocalDateTime.now();
        LocalDate firstDay = now.minusDays(days).toLocalDate();
        LocalDateTime since = firstDay.atStartOfDay();
        LocalDateTime until = firstDay.plusDays(days).atStartOfDay();

        long totalProducts = productRepository.count();
        long totalOrders = orderRepository.count();
        double totalSales = nz(orderRepository.sumAmountExcludingCancelled());
        long totalUsers = userRepository.count();

        // ---- 销售趋势（补齐零值日） ----
        Map<String, double[]> trendRaw = new HashMap<>();
        for (Object[] row : orderRepository.salesTrendBetween(since, until)) {
            trendRaw.put(dayKey(row[0]), new double[]{
                    ((Number) row[1]).doubleValue(), ((Number) row[2]).doubleValue()});
        }
        List<Map<String, Object>> salesTrend = new ArrayList<>(days);
        List<Map<String, Object>> userGrowth = new ArrayList<>(days);

        Map<String, Long> growthRaw = new HashMap<>();
        for (Object[] row : userRepository.countGroupByDaySince(since)) {
            growthRaw.put(dayKey(row[0]), ((Number) row[1]).longValue());
        }

        for (int i = 0; i < days; i++) {
            String key = firstDay.plusDays(i).format(DAY);
            double[] v = trendRaw.getOrDefault(key, new double[]{0, 0});
            Map<String, Object> t = new LinkedHashMap<>();
            t.put("date", key);
            t.put("sales", round2(v[0]));
            t.put("orders", (long) v[1]);
            salesTrend.add(t);

            Map<String, Object> g = new LinkedHashMap<>();
            g.put("date", key);
            g.put("count", growthRaw.getOrDefault(key, 0L));
            userGrowth.add(g);
        }

        // ---- 订单状态分布 ----
        List<Map<String, Object>> orderStatusDist = orderRepository.countGroupByStatus().stream()
                .map(r -> kv("status", r[0], "count", ((Number) r[1]).longValue()))
                .toList();

        // ---- 品类分布 ----
        List<Map<String, Object>> categoryDist = productRepository.countGroupByCategoryName().stream()
                .map(r -> kv("category", r[0], "count", ((Number) r[1]).longValue()))
                .toList();

        // ---- 热销 TOP 10 ----
        List<Map<String, Object>> topProducts = orderItemRepository
                .findTopSoldProducts(PageRequest.of(0, 10)).stream()
                .map(r -> kv("name", r[0], "sales", ((Number) r[1]).longValue()))
                .toList();

        // ---- AI 转化率: 含推荐位商品的订单占比 ----
        double aiConversion = 0.0;
        if (totalOrders > 0) {
            long hit = orderItemRepository.countDistinctOrdersWithRecommendedProduct();
            aiConversion = Math.round(hit * 1000.0 / totalOrders) / 10.0;
        }

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("total_products", totalProducts);
        result.put("total_orders", totalOrders);
        result.put("total_sales", round2(totalSales));
        result.put("total_revenue", round2(totalSales)); // 兼容前端字段
        result.put("total_users", totalUsers);
        result.put("ai_conversion", aiConversion);
        result.put("sales_trend", salesTrend);
        result.put("order_status_dist", orderStatusDist);
        result.put("category_dist", categoryDist);
        result.put("user_growth", userGrowth);
        result.put("top_products", topProducts);

        cache.set(cacheKey, result, 60);
        return result;
    }

    // ====== 商品管理 ======

    @GetMapping("/products")
    public Map<String, Object> listProducts(@RequestParam(defaultValue = "1") int page,
                                            @RequestParam(name = "page_size", defaultValue = "20") int pageSize,
                                            @RequestParam(name = "audit_status", required = false) String auditStatus,
                                            @CurrentUser User admin) {
        Roles.requireAdmin(admin);
        validatePaging(page, pageSize);

        // 显式声明 createdAt DESC + id ASC：仅靠方法名的 OrderByCreatedAtDesc 没有 tie-break，
        // 种子数据里大量商品 created_at 相同，H2 的返回顺序会与 SQLite（rowid 兜底）不一致
        var pageable = PageRequest.of(page - 1, pageSize,
                Sort.by(Sort.Direction.DESC, "createdAt").and(Sort.by(Sort.Direction.ASC, "id")));
        Page<Product> result = (auditStatus == null || auditStatus.isBlank())
                ? productRepository.findAll(pageable)
                : productRepository.findByAuditStatus(auditStatus, pageable);

        Map<String, Object> out = new LinkedHashMap<>();
        out.put("items", result.getContent().stream().map(ProductDtos.AdminProductRes::from).toList());
        out.put("total", result.getTotalElements());
        out.put("page", page);
        out.put("page_size", pageSize);
        return out;
    }

    @PostMapping("/products")
    @Transactional
    public ProductDtos.ProductRes createProduct(@Valid @RequestBody ProductDtos.ProductCreateReq req,
                                                @CurrentUser User admin) {
        Roles.requireAdmin(admin);
        Product product = Product.builder()
                .name(req.name())
                .description(req.description())
                .price(req.price())
                .originalPrice(req.originalPrice())
                .image(req.image())
                .images(new ArrayList<>(req.images()))
                .brand(req.brand())
                .stock(req.stock())
                .categoryId(req.categoryId())
                .tags(new ArrayList<>(req.tags()))
                .isRecommend(req.isRecommend())
                .isNew(req.isNew())
                .isSale(req.isSale())
                .auditStatus("approved")
                .build();
        product = productRepository.save(product);
        invalidate();
        return ProductDtos.ProductRes.from(product);
    }

    @PutMapping("/products/{productId}")
    @Transactional
    public ProductDtos.ProductRes updateProduct(@PathVariable Long productId,
                                                @RequestBody ProductDtos.ProductUpdateReq req,
                                                @CurrentUser User admin) {
        Roles.requireAdmin(admin);
        Product p = productRepository.findById(productId)
                .orElseThrow(() -> ApiException.notFound("商品不存在"));

        // null 表示「未提交该字段」，对应 Pydantic 的 exclude_unset
        if (req.name() != null) p.setName(req.name());
        if (req.description() != null) p.setDescription(req.description());
        if (req.price() != null) p.setPrice(req.price());
        if (req.originalPrice() != null) p.setOriginalPrice(req.originalPrice());
        if (req.image() != null) p.setImage(req.image());
        if (req.images() != null) p.setImages(new ArrayList<>(req.images()));
        if (req.brand() != null) p.setBrand(req.brand());
        if (req.stock() != null) p.setStock(req.stock());
        if (req.categoryId() != null) p.setCategoryId(req.categoryId());
        if (req.tags() != null) p.setTags(new ArrayList<>(req.tags()));
        if (req.isRecommend() != null) p.setIsRecommend(req.isRecommend());
        if (req.isNew() != null) p.setIsNew(req.isNew());
        if (req.isSale() != null) p.setIsSale(req.isSale());
        if (req.isActive() != null) p.setIsActive(req.isActive());
        if (req.auditStatus() != null) p.setAuditStatus(req.auditStatus());

        p = productRepository.save(p);
        invalidate();
        return ProductDtos.ProductRes.from(p);
    }

    /** 软删除：只下架，不物理删除，保证历史订单的商品快照仍可追溯 */
    @DeleteMapping("/products/{productId}")
    @Transactional
    public Map<String, Object> deleteProduct(@PathVariable Long productId, @CurrentUser User admin) {
        Roles.requireAdmin(admin);
        Product p = productRepository.findById(productId)
                .orElseThrow(() -> ApiException.notFound("商品不存在"));
        p.setIsActive(false);
        productRepository.save(p);
        invalidate();
        return Map.of("message", "已下架");
    }

    @PutMapping("/products/{productId}/audit")
    @Transactional
    public Map<String, Object> auditProduct(@PathVariable Long productId,
                                            @RequestBody ProductDtos.ProductAuditReq req,
                                            @CurrentUser User admin) {
        Roles.requireAdmin(admin);
        Product p = productRepository.findById(productId)
                .orElseThrow(() -> ApiException.notFound("商品不存在"));

        String status = req.auditStatus();
        if (!"approved".equals(status) && !"rejected".equals(status)) {
            throw ApiException.badRequest("审核状态无效");
        }
        p.setAuditStatus(status);
        if ("rejected".equals(status)) {
            p.setIsActive(false);
        }
        productRepository.save(p);
        invalidate();
        return Map.of("message", "商品已" + ("approved".equals(status) ? "通过" : "拒绝") + "审核");
    }

    // ====== 用户管理 ======

    @GetMapping("/users")
    public Map<String, Object> listUsers(@RequestParam(defaultValue = "1") int page,
                                         @RequestParam(name = "page_size", defaultValue = "20") int pageSize,
                                         @RequestParam(required = false) String role,
                                         @CurrentUser User admin) {
        Roles.requireAdmin(admin);
        validatePaging(page, pageSize);

        var pageable = PageRequest.of(page - 1, pageSize);
        Page<User> result = (role == null || role.isBlank())
                ? userRepository.findAllByOrderByCreatedAtDescIdAsc(pageable)
                : userRepository.findByRoleOrderByCreatedAtDescIdAsc(role, pageable);

        List<Map<String, Object>> items = result.getContent().stream().map(u -> {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("id", u.getId());
            m.put("username", u.getUsername());
            m.put("email", u.getEmail());
            m.put("role", u.getRole());
            m.put("is_active", !Boolean.FALSE.equals(u.getIsActive()));
            m.put("avatar", u.getAvatar());
            m.put("phone", u.getPhone());
            m.put("created_at", u.getCreatedAt());
            return m;
        }).toList();

        Map<String, Object> out = new LinkedHashMap<>();
        out.put("items", items);
        out.put("total", result.getTotalElements());
        out.put("page", page);
        out.put("page_size", pageSize);
        return out;
    }

    @PutMapping("/users/{userId}/status")
    @Transactional
    public Map<String, Object> toggleUserStatus(@PathVariable Long userId, @CurrentUser User admin) {
        Roles.requireAdmin(admin);
        User u = userRepository.findById(userId)
                .orElseThrow(() -> ApiException.notFound("用户不存在"));
        if (u.getId().equals(admin.getId())) {
            throw ApiException.badRequest("不能禁用自己");
        }
        boolean active = !Boolean.FALSE.equals(u.getIsActive());
        u.setIsActive(!active);
        userRepository.save(u);

        Map<String, Object> out = new LinkedHashMap<>();
        out.put("message", "用户已" + (u.getIsActive() ? "启用" : "禁用"));
        out.put("is_active", u.getIsActive());
        return out;
    }

    /** 角色变更。Python 版把 role 放在 query string，这里保持一致 */
    @PutMapping("/users/{userId}/role")
    @Transactional
    public Map<String, Object> updateUserRole(@PathVariable Long userId,
                                              @RequestParam String role,
                                              @CurrentUser User admin) {
        Roles.requireAdmin(admin);
        if (!Roles.USER.equals(role) && !Roles.MERCHANT.equals(role) && !Roles.ADMIN.equals(role)) {
            throw ApiException.badRequest("角色无效");
        }
        User u = userRepository.findById(userId)
                .orElseThrow(() -> ApiException.notFound("用户不存在"));
        u.setRole(role);
        userRepository.save(u);
        return Map.of("message", "角色已更新为 " + role);
    }

    // ====== 订单管理 ======

    @GetMapping("/orders")
    @Transactional(readOnly = true)
    public Map<String, Object> listAllOrders(@RequestParam(defaultValue = "1") int page,
                                             @RequestParam(name = "page_size", defaultValue = "20") int pageSize,
                                             @RequestParam(required = false) String status,
                                             @CurrentUser User admin) {
        Roles.requireAdmin(admin);
        validatePaging(page, pageSize);

        var pageable = PageRequest.of(page - 1, pageSize);
        Page<Order> result = (status == null || status.isBlank())
                ? orderRepository.findAllByOrderByCreatedAtDescIdDesc(pageable)
                : orderRepository.findByStatusOrderByCreatedAtDescIdDesc(status, pageable);

        List<Order> orders = result.getContent();

        // 批量取用户名与首条明细，避免 Python 版那样每行两次查询
        Set<Long> userIds = new HashSet<>();
        List<Long> orderIds = new ArrayList<>();
        orders.forEach(o -> {
            userIds.add(o.getUserId());
            orderIds.add(o.getId());
        });
        Map<Long, String> usernames = new HashMap<>();
        userRepository.findAllById(userIds).forEach(u -> usernames.put(u.getId(), u.getUsername()));

        Map<Long, OrderItem> firstItems = new HashMap<>();
        if (!orderIds.isEmpty()) {
            for (OrderItem it : orderItemRepository.findByOrderIdInOrderByIdAsc(orderIds)) {
                firstItems.putIfAbsent(it.getOrderId(), it);
            }
        }

        List<Map<String, Object>> items = new ArrayList<>(orders.size());
        for (Order o : orders) {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("id", o.getId());
            m.put("order_no", o.getOrderNo());
            m.put("user_id", o.getUserId());
            m.put("username", usernames.getOrDefault(o.getUserId(), "用户" + o.getUserId()));
            m.put("status", o.getStatus());
            m.put("total_amount", o.getTotalAmount());
            m.put("created_at", o.getCreatedAt() == null ? null : o.getCreatedAt().toString());
            OrderItem first = firstItems.get(o.getId());
            m.put("items", first == null ? List.of()
                    : List.of(Map.of("product_name", first.getProductName(),
                    "quantity", first.getQuantity())));
            items.add(m);
        }

        Map<String, Object> out = new LinkedHashMap<>();
        out.put("items", items);
        out.put("total", result.getTotalElements());
        out.put("page", page);
        out.put("page_size", pageSize);
        return out;
    }

    @PutMapping("/orders/{orderId}/status")
    @Transactional
    public Map<String, Object> updateOrderStatus(@PathVariable Long orderId,
                                                 @Valid @RequestBody OrderStatusBody req,
                                                 @CurrentUser User admin) {
        Roles.requireAdmin(admin);
        Order order = orderRepository.findById(orderId)
                .orElseThrow(() -> ApiException.notFound("订单不存在"));

        List<String> allowed = OrderController.TRANSITIONS.getOrDefault(order.getStatus(), List.of());
        if (!allowed.contains(req.status())) {
            throw ApiException.badRequest(
                    "订单状态不能从 " + order.getStatus() + " 变为 " + req.status());
        }

        order.setStatus(req.status());
        LocalDateTime now = LocalDateTime.now();
        switch (req.status()) {
            case "paid" -> order.setPaidAt(now);
            case "shipped" -> {
                order.setShippedAt(now);
                if (req.trackingNo() != null && !req.trackingNo().isBlank()) {
                    order.setTrackingNo(req.trackingNo());
                }
                if (req.logisticsCompany() != null && !req.logisticsCompany().isBlank()) {
                    order.setLogisticsCompany(req.logisticsCompany());
                }
            }
            case "completed" -> order.setCompletedAt(now);
            default -> {
                // cancelled / refunded 无额外时间戳
            }
        }
        orderRepository.save(order);
        cache.deletePattern("admin:*");
        return Map.of("message", "订单状态已更新为 " + req.status());
    }

    /** 请求体用 snake_case（tracking_no / logistics_company），由全局 Jackson 命名策略转换 */
    public record OrderStatusBody(String status, String trackingNo, String logisticsCompany) {
    }

    // ====== 内部工具 ======

    private void invalidate() {
        cache.deletePattern("products:*");
        cache.deletePattern("admin:*");
        // 商品变更后 RAG 索引失效，下次语义搜索会自动重建
        ragService.markStale();
    }

    private static void validatePaging(int page, int pageSize) {
        if (page < 1) throw new ApiException(422, "page: 必须 >= 1");
        if (pageSize < 1 || pageSize > 100) throw new ApiException(422, "page_size: 需在 1-100 之间");
    }

    private static Map<String, Object> kv(String k1, Object v1, String k2, Object v2) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put(k1, v1);
        m.put(k2, v2);
        return m;
    }

    /** 原生查询里 DATE() 在 MySQL 返回 java.sql.Date，在 H2 返回 LocalDate，这里统一成 yyyy-MM-dd */
    private static String dayKey(Object raw) {
        if (raw instanceof Date d) {
            return d.toLocalDate().format(DAY);
        }
        if (raw instanceof LocalDate d) {
            return d.format(DAY);
        }
        if (raw instanceof java.sql.Timestamp ts) {
            return ts.toLocalDateTime().toLocalDate().format(DAY);
        }
        if (raw instanceof LocalDateTime dt) {
            return dt.toLocalDate().format(DAY);
        }
        String s = String.valueOf(raw);
        return s.length() >= 10 ? s.substring(0, 10) : s;
    }

    private static double nz(Double v) {
        return v == null ? 0.0 : v;
    }

    private static double round2(double v) {
        return Math.round(v * 100.0) / 100.0;
    }

    @SuppressWarnings("unused")
    private static LocalDateTime startOfDay(LocalDate d) {
        return LocalDateTime.of(d, LocalTime.MIDNIGHT);
    }
}
