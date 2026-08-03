package com.smartmall.dto;

import com.smartmall.entity.User;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.Map;

/** 认证相关 DTO，字段与 schemas.py 的 UserRegister/UserLogin/Token/UserInfo 一一对应 */
public final class AuthDtos {

    private AuthDtos() {
    }

    public record RegisterReq(
            @Email(message = "邮箱格式不正确") @NotBlank(message = "邮箱不能为空") String email,
            @NotBlank(message = "用户名不能为空") @Size(min = 2, max = 50, message = "用户名长度需在 2-50 之间") String username,
            @NotBlank(message = "密码不能为空") @Size(min = 6, message = "密码至少 6 位") String password
    ) {
    }

    public record LoginReq(
            @NotBlank(message = "用户名不能为空") String username,
            @NotBlank(message = "密码不能为空") String password
    ) {
    }

    /** token_type 固定 bearer，user 是精简用户信息，前端登录后直接存 localStorage */
    public record TokenRes(String accessToken, String tokenType, Map<String, Object> user) {

        public static TokenRes of(String token, User u) {
            Map<String, Object> brief = new LinkedHashMap<>();
            brief.put("id", u.getId());
            brief.put("username", u.getUsername());
            brief.put("email", u.getEmail());
            brief.put("role", u.getRole());
            return new TokenRes(token, "bearer", brief);
        }
    }

    public record UserInfoRes(
            Long id, String email, String username, String role,
            String avatar, String phone, LocalDateTime createdAt
    ) {
        public static UserInfoRes from(User u) {
            return new UserInfoRes(
                    u.getId(), u.getEmail(), u.getUsername(), u.getRole(),
                    u.getAvatar() == null ? "" : u.getAvatar(),
                    u.getPhone() == null ? "" : u.getPhone(),
                    u.getCreatedAt());
        }
    }

    /** 全部可选，只更新非 null 字段 */
    public record UserUpdateReq(String avatar, String phone,
                                @Email(message = "邮箱格式不正确") String email) {
    }
}
