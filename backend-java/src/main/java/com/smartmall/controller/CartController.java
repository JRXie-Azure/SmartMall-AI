package com.smartmall.controller;

import com.smartmall.common.ApiException;
import com.smartmall.dto.OrderDtos;
import com.smartmall.dto.ProductDtos;
import com.smartmall.entity.CartItem;
import com.smartmall.entity.Product;
import com.smartmall.entity.User;
import com.smartmall.repository.CartItemRepository;
import com.smartmall.repository.ProductRepository;
import com.smartmall.security.CurrentUser;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/** 购物车接口，对应 routers/cart.py */
@RestController
@RequestMapping("/api/cart")
@RequiredArgsConstructor
public class CartController {

    private final CartItemRepository cartItemRepository;
    private final ProductRepository productRepository;

    @GetMapping("/items")
    public List<OrderDtos.CartItemRes> listItems(@CurrentUser User user) {
        return cartItemRepository.findByUserIdOrderByIdAsc(user.getId())
                .stream().map(this::toRes).toList();
    }

    @PostMapping("/items")
    @Transactional
    public OrderDtos.CartItemRes addToCart(@Valid @RequestBody OrderDtos.CartItemCreateReq req,
                                           @CurrentUser User user) {
        Product product = productRepository.findById(req.productId())
                .orElseThrow(() -> ApiException.notFound("商品不存在"));

        if (product.getStock() < req.quantity()) {
            throw ApiException.badRequest("库存不足 (剩余 " + product.getStock() + ")");
        }

        var existing = cartItemRepository.findByUserIdAndProductId(user.getId(), req.productId());
        if (existing.isPresent()) {
            CartItem item = existing.get();
            item.setQuantity(item.getQuantity() + req.quantity());
            if (item.getQuantity() > product.getStock()) {
                throw ApiException.badRequest("超过库存 (剩余 " + product.getStock() + ")");
            }
            return toRes(cartItemRepository.save(item));
        }

        CartItem item = CartItem.builder()
                .userId(user.getId())
                .productId(req.productId())
                .quantity(req.quantity())
                .build();
        return toRes(cartItemRepository.save(item));
    }

    @PutMapping("/items/{itemId}")
    @Transactional
    public OrderDtos.CartItemRes updateItem(@PathVariable Long itemId,
                                            @Valid @RequestBody OrderDtos.CartItemUpdateReq req,
                                            @CurrentUser User user) {
        CartItem item = cartItemRepository.findByIdAndUserId(itemId, user.getId())
                .orElseThrow(() -> ApiException.notFound("购物车项不存在"));

        Product product = productRepository.findById(item.getProductId()).orElse(null);
        if (product != null && req.quantity() > product.getStock()) {
            throw ApiException.badRequest("超过库存 (剩余 " + product.getStock() + ")");
        }
        item.setQuantity(req.quantity());
        return toRes(cartItemRepository.save(item));
    }

    @DeleteMapping("/items/{itemId}")
    @Transactional
    public Map<String, Object> removeItem(@PathVariable Long itemId, @CurrentUser User user) {
        CartItem item = cartItemRepository.findByIdAndUserId(itemId, user.getId())
                .orElseThrow(() -> ApiException.notFound("购物车项不存在"));
        cartItemRepository.delete(item);
        return Map.of("message", "已移除");
    }

    @DeleteMapping("/items")
    @Transactional
    public Map<String, Object> clearCart(@CurrentUser User user) {
        cartItemRepository.deleteByUserId(user.getId());
        return Map.of("message", "购物车已清空");
    }

    @GetMapping("/count")
    public Map<String, Object> count(@CurrentUser User user) {
        return Map.of("count", cartItemRepository.countByUserId(user.getId()));
    }

    /** 前端购物车页要直接渲染商品名/图/价，所以内嵌完整 product 对象 */
    private OrderDtos.CartItemRes toRes(CartItem item) {
        ProductDtos.ProductRes product = productRepository.findById(item.getProductId())
                .map(ProductDtos.ProductRes::from).orElse(null);
        return new OrderDtos.CartItemRes(item.getId(), item.getProductId(), item.getQuantity(), product);
    }
}
