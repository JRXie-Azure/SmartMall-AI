package com.smartmall.common;

import lombok.Getter;
import org.springframework.http.HttpStatus;

/**
 * 业务异常，等价于 FastAPI 的 HTTPException。
 * 抛出后由 {@link GlobalExceptionHandler} 统一渲染成 {"detail": "..."}。
 */
@Getter
public class ApiException extends RuntimeException {

    private final int status;

    public ApiException(int status, String detail) {
        super(detail);
        this.status = status;
    }

    public ApiException(HttpStatus status, String detail) {
        this(status.value(), detail);
    }

    public static ApiException badRequest(String detail) {
        return new ApiException(HttpStatus.BAD_REQUEST, detail);
    }

    public static ApiException unauthorized(String detail) {
        return new ApiException(HttpStatus.UNAUTHORIZED, detail);
    }

    public static ApiException forbidden(String detail) {
        return new ApiException(HttpStatus.FORBIDDEN, detail);
    }

    public static ApiException notFound(String detail) {
        return new ApiException(HttpStatus.NOT_FOUND, detail);
    }

    public static ApiException serviceUnavailable(String detail) {
        return new ApiException(HttpStatus.SERVICE_UNAVAILABLE, detail);
    }
}
