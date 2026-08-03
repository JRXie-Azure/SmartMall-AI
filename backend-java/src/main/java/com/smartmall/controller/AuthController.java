package com.smartmall.controller;

import com.smartmall.common.ApiException;
import com.smartmall.dto.AuthDtos;
import com.smartmall.entity.User;
import com.smartmall.repository.UserRepository;
import com.smartmall.security.CurrentUser;
import com.smartmall.security.JwtService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.*;

/** 认证接口，对应 routers/auth.py */
@RestController
@RequestMapping("/api/auth")
@RequiredArgsConstructor
public class AuthController {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtService jwtService;

    @PostMapping("/register")
    @Transactional
    public AuthDtos.TokenRes register(@Valid @RequestBody AuthDtos.RegisterReq req) {
        if (userRepository.existsByEmailOrUsername(req.email(), req.username())) {
            throw ApiException.badRequest("用户名或邮箱已存在");
        }

        User user = User.builder()
                .email(req.email())
                .username(req.username())
                .hashedPassword(passwordEncoder.encode(req.password()))
                .build();
        user = userRepository.save(user);

        String token = jwtService.createAccessToken(user.getId(), user.getRole(), user.getUsername());
        return AuthDtos.TokenRes.of(token, user);
    }

    @PostMapping("/login")
    public AuthDtos.TokenRes login(@Valid @RequestBody AuthDtos.LoginReq req) {
        User user = userRepository.findByUsername(req.username())
                .orElseThrow(() -> ApiException.unauthorized("用户名或密码错误"));

        if (!passwordEncoder.matches(req.password(), user.getHashedPassword())) {
            throw ApiException.unauthorized("用户名或密码错误");
        }
        if (!Boolean.TRUE.equals(user.getIsActive())) {
            throw ApiException.forbidden("账号已被禁用");
        }

        String token = jwtService.createAccessToken(user.getId(), user.getRole(), user.getUsername());
        return AuthDtos.TokenRes.of(token, user);
    }

    @GetMapping("/me")
    public AuthDtos.UserInfoRes me(@CurrentUser User user) {
        return AuthDtos.UserInfoRes.from(user);
    }

    @PutMapping("/me")
    @Transactional
    public AuthDtos.UserInfoRes updateProfile(@Valid @RequestBody AuthDtos.UserUpdateReq req,
                                              @CurrentUser User user) {
        if (req.avatar() != null) {
            user.setAvatar(req.avatar());
        }
        if (req.phone() != null) {
            user.setPhone(req.phone());
        }
        if (req.email() != null) {
            if (userRepository.existsByEmailAndIdNot(req.email(), user.getId())) {
                throw ApiException.badRequest("邮箱已被使用");
            }
            user.setEmail(req.email());
        }
        return AuthDtos.UserInfoRes.from(userRepository.save(user));
    }
}
