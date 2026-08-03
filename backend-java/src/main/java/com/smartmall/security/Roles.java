package com.smartmall.security;

import com.smartmall.common.ApiException;
import com.smartmall.entity.User;

/**
 * 角色校验 —— 对应 Python 版 auth.py 的 get_current_admin / get_current_merchant / require_role。
 *
 * <p>没有做成 {@code @PreAuthorize}，是为了让 403 的响应体文案跟 Python 版逐字一致
 * （{@code {"detail": "需要管理员权限"}}），前端的错误提示不用改。
 */
public final class Roles {

    public static final String USER = "user";
    public static final String MERCHANT = "merchant";
    public static final String ADMIN = "admin";

    private Roles() {
    }

    public static User requireAdmin(User user) {
        if (!ADMIN.equals(user.getRole())) {
            throw ApiException.forbidden("需要管理员权限");
        }
        return user;
    }

    public static User requireMerchant(User user) {
        if (!MERCHANT.equals(user.getRole()) && !ADMIN.equals(user.getRole())) {
            throw ApiException.forbidden("需要商家或管理员权限");
        }
        return user;
    }

    public static boolean isAdmin(User user) {
        return user != null && ADMIN.equals(user.getRole());
    }
}
