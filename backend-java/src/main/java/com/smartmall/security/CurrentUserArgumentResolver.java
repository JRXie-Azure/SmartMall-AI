package com.smartmall.security;

import com.smartmall.common.ApiException;
import com.smartmall.entity.User;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.core.MethodParameter;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.bind.support.WebDataBinderFactory;
import org.springframework.web.context.request.NativeWebRequest;
import org.springframework.web.method.support.HandlerMethodArgumentResolver;
import org.springframework.web.method.support.ModelAndViewContainer;

/** 把 {@code @CurrentUser User} 解析成实体，复刻 FastAPI 的依赖注入手感 */
@Component
public class CurrentUserArgumentResolver implements HandlerMethodArgumentResolver {

    @Override
    public boolean supportsParameter(MethodParameter parameter) {
        return parameter.hasParameterAnnotation(CurrentUser.class)
                && User.class.isAssignableFrom(parameter.getParameterType());
    }

    @Override
    public Object resolveArgument(MethodParameter parameter,
                                  ModelAndViewContainer mavContainer,
                                  NativeWebRequest webRequest,
                                  WebDataBinderFactory binderFactory) {

        CurrentUser meta = parameter.getParameterAnnotation(CurrentUser.class);
        boolean required = meta == null || meta.required();

        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth != null && auth.getPrincipal() instanceof AuthUser authUser) {
            return authUser.getUser();
        }

        if (!required) {
            return null;
        }

        // 有 Token 但校验失败时，还原成 Python 版的具体文案
        HttpServletRequest req = webRequest.getNativeRequest(HttpServletRequest.class);
        if (req != null) {
            Object err = req.getAttribute(JwtAuthenticationFilter.ATTR_AUTH_ERROR);
            if (err instanceof ApiException apiEx) {
                throw apiEx;
            }
        }
        // 走到这里 = 请求压根没带 Token。FastAPI 的 OAuth2PasswordBearer(auto_error=True)
        // 在这种情况下返回的是 "Not authenticated"，而非 auth.py 里那条 "无效的认证凭证"
        //（后者只在 Token 能解析、但 sub 缺失或用户不存在时抛出，见 JwtAuthenticationFilter）
        throw ApiException.unauthorized("Not authenticated");
    }
}
