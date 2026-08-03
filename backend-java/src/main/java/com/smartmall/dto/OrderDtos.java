package com.smartmall.dto;

import com.smartmall.entity.Address;
import com.smartmall.entity.Order;
import com.smartmall.entity.OrderItem;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

/** 购物车/地址/订单相关 DTO */
public final class OrderDtos {

    private OrderDtos() {
    }

    // ====== 购物车 ======

    public record CartItemCreateReq(Long productId, Integer quantity) {
        public CartItemCreateReq {
            if (quantity == null) quantity = 1;
        }
    }

    public record CartItemUpdateReq(@Min(value = 1, message = "数量至少为 1") Integer quantity) {
    }

    public record CartItemRes(Long id, Long productId, Integer quantity, ProductDtos.ProductRes product) {
    }

    // ====== 地址 ======

    public record AddressReq(
            @NotBlank(message = "收货人不能为空") String name,
            @NotBlank(message = "手机号不能为空") String phone,
            @NotBlank(message = "省份不能为空") String province,
            @NotBlank(message = "城市不能为空") String city,
            @NotBlank(message = "区县不能为空") String district,
            @NotBlank(message = "详细地址不能为空") String detail,
            Boolean isDefault
    ) {
        public AddressReq {
            if (isDefault == null) isDefault = false;
        }
    }

    public record AddressRes(Long id, String name, String phone, String province,
                             String city, String district, String detail,
                             Boolean isDefault, LocalDateTime createdAt) {
        public static AddressRes from(Address a) {
            return new AddressRes(a.getId(), a.getName(), a.getPhone(), a.getProvince(),
                    a.getCity(), a.getDistrict(), a.getDetail(),
                    Boolean.TRUE.equals(a.getIsDefault()), a.getCreatedAt());
        }
    }

    // ====== 订单 ======

    public record OrderCreateReq(Long addressId, String note) {
        public OrderCreateReq {
            if (note == null) note = "";
        }
    }

    public record OrderStatusUpdateReq(@NotBlank(message = "状态不能为空") String status,
                                       String trackingNo, String logisticsCompany) {
    }

    public record OrderItemRes(Long id, Long productId, String productName,
                               String productImage, Double price, Integer quantity) {
        public static OrderItemRes from(OrderItem i) {
            return new OrderItemRes(i.getId(), i.getProductId(), i.getProductName(),
                    i.getProductImage() == null ? "" : i.getProductImage(),
                    i.getPrice(), i.getQuantity());
        }
    }

    public record OrderRes(
            Long id, String orderNo, String status, Double totalAmount,
            Map<String, Object> addressSnapshot, String note,
            String trackingNo, String logisticsCompany,
            List<OrderItemRes> items,
            LocalDateTime createdAt, LocalDateTime paidAt,
            LocalDateTime shippedAt, LocalDateTime completedAt
    ) {
        public static OrderRes from(Order o, List<OrderItem> items) {
            return new OrderRes(
                    o.getId(), o.getOrderNo(), o.getStatus(), o.getTotalAmount(),
                    o.getAddressSnapshot() == null ? Map.of() : o.getAddressSnapshot(),
                    o.getNote() == null ? "" : o.getNote(),
                    o.getTrackingNo() == null ? "" : o.getTrackingNo(),
                    o.getLogisticsCompany() == null ? "" : o.getLogisticsCompany(),
                    items.stream().map(OrderItemRes::from).toList(),
                    o.getCreatedAt(), o.getPaidAt(), o.getShippedAt(), o.getCompletedAt());
        }
    }
}
