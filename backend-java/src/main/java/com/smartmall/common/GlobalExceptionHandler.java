package com.smartmall.common;

import jakarta.servlet.http.HttpServletRequest;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.core.AuthenticationException;
import org.springframework.validation.FieldError;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.servlet.NoHandlerFoundException;
import org.springframework.web.servlet.resource.NoResourceFoundException;

import java.util.Map;
import java.util.stream.Collectors;

/**
 * 全局异常处理 —— 输出与 FastAPI 完全一致的 {"detail": "..."} 结构。
 *
 * <p>前端 index.html 统一读取 err.detail 展示错误提示，因此这里的响应体格式
 * 不能改成常见的 {code, message, data}，否则会破坏前后端契约。
 */
@Slf4j
@RestControllerAdvice
public class GlobalExceptionHandler {

    private static ResponseEntity<Map<String, Object>> detail(int status, String message) {
        return ResponseEntity.status(status).body(Map.of("detail", message));
    }

    @ExceptionHandler(ApiException.class)
    public ResponseEntity<Map<String, Object>> handleApi(ApiException ex) {
        return detail(ex.getStatus(), ex.getMessage());
    }

    /** @Valid 校验失败 —— FastAPI 用 422，这里保持一致。 */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<Map<String, Object>> handleValidation(MethodArgumentNotValidException ex) {
        String msg = ex.getBindingResult().getFieldErrors().stream()
                .map(f -> fieldName(f) + ": " + f.getDefaultMessage())
                .collect(Collectors.joining("; "));
        return detail(HttpStatus.UNPROCESSABLE_ENTITY.value(), msg.isEmpty() ? "请求参数校验失败" : msg);
    }

    private static String fieldName(FieldError f) {
        // Java 字段是 camelCase，对外暴露成 snake_case，错误提示也要对齐
        return f.getField().replaceAll("([a-z0-9])([A-Z])", "$1_$2").toLowerCase();
    }

    @ExceptionHandler(MissingServletRequestParameterException.class)
    public ResponseEntity<Map<String, Object>> handleMissingParam(MissingServletRequestParameterException ex) {
        return detail(HttpStatus.UNPROCESSABLE_ENTITY.value(), "缺少必需参数: " + ex.getParameterName());
    }

    @ExceptionHandler(MethodArgumentTypeMismatchException.class)
    public ResponseEntity<Map<String, Object>> handleTypeMismatch(MethodArgumentTypeMismatchException ex) {
        return detail(HttpStatus.UNPROCESSABLE_ENTITY.value(), "参数类型错误: " + ex.getName());
    }

    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ResponseEntity<Map<String, Object>> handleUnreadable(HttpMessageNotReadableException ex) {
        return detail(HttpStatus.BAD_REQUEST.value(), "请求体格式错误");
    }

    /** 未携带凭证时的兜底 —— 与 FastAPI 的 OAuth2PasswordBearer 文案保持一致 */
    @ExceptionHandler(AuthenticationException.class)
    public ResponseEntity<Map<String, Object>> handleAuth(AuthenticationException ex) {
        return detail(HttpStatus.UNAUTHORIZED.value(), "Not authenticated");
    }

    @ExceptionHandler(AccessDeniedException.class)
    public ResponseEntity<Map<String, Object>> handleDenied(AccessDeniedException ex) {
        return detail(HttpStatus.FORBIDDEN.value(), "无权访问");
    }

    @ExceptionHandler(HttpRequestMethodNotSupportedException.class)
    public ResponseEntity<Map<String, Object>> handleMethod(HttpRequestMethodNotSupportedException ex) {
        return detail(HttpStatus.METHOD_NOT_ALLOWED.value(), "Method Not Allowed");
    }

    /**
     * 未匹配到任何 handler。
     *
     * <p>注意这里必须同时接住 {@link NoResourceFoundException}：WebMvcConfig 把 {@code /**}
     * 映射到了静态资源目录，所以未命中的 {@code /api/**} 不会抛 NoHandlerFoundException，
     * 而是在静态资源阶段抛 NoResourceFoundException。不显式处理就会被下面的 catch-all
     * 吃成 500，而 FastAPI 对不存在的路由返回的是 404。
     */
    @ExceptionHandler({NoHandlerFoundException.class, NoResourceFoundException.class})
    public ResponseEntity<Map<String, Object>> handleNotFound(Exception ex) {
        return detail(HttpStatus.NOT_FOUND.value(), "Not Found");
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<Map<String, Object>> handleOther(Exception ex, HttpServletRequest request) {
        log.error("未处理异常 {} {}", request.getMethod(), request.getRequestURI(), ex);
        return detail(HttpStatus.INTERNAL_SERVER_ERROR.value(), "服务器内部错误");
    }
}
