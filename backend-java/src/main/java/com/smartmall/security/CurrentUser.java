package com.smartmall.security;

import java.lang.annotation.*;

/**
 * 注入当前登录用户，等价于 FastAPI 的 {@code Depends(get_current_user)}。
 *
 * <p>{@code @CurrentUser User user} —— 未登录直接 401。
 * <p>{@code @CurrentUser(required = false) User user} —— 未登录注入 null，
 * 等价于 {@code Depends(get_current_user_optional)}。
 */
@Target(ElementType.PARAMETER)
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface CurrentUser {

    boolean required() default true;
}
