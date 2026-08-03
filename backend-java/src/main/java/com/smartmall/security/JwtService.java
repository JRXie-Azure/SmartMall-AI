package com.smartmall.security;

import com.smartmall.config.SmartMallProperties;
import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.springframework.stereotype.Service;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Date;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * JWT 签发与校验。
 *
 * <p>刻意与 Python 版 (python-jose, HS256) 保持二进制兼容：
 * 同一 SECRET_KEY 下，Java 签发的 Token 能被 Python 校验，反之亦然。
 * payload 固定为 sub(用户ID字符串) / role / username / exp。
 */
@Service
public class JwtService {

    private final SecretKey key;
    private final long expireMinutes;

    public JwtService(SmartMallProperties props) {
        String secret = props.getJwt().getSecretKey();
        byte[] raw = secret.getBytes(StandardCharsets.UTF_8);
        if (raw.length < 32) {
            throw new IllegalStateException(
                    "SECRET_KEY 至少需要 32 字节 (HS256 要求)，当前只有 " + raw.length + " 字节");
        }
        this.key = Keys.hmacShaKeyFor(raw);
        this.expireMinutes = props.getJwt().getAccessTokenExpireMinutes();
    }

    public String createAccessToken(Long userId, String role, String username) {
        Map<String, Object> claims = new LinkedHashMap<>();
        claims.put("sub", String.valueOf(userId));
        claims.put("role", role);
        claims.put("username", username);

        Instant now = Instant.now();
        return Jwts.builder()
                .claims(claims)
                .expiration(Date.from(now.plusSeconds(expireMinutes * 60)))
                .signWith(key)
                .compact();
    }

    /** 解析并验签。失败抛 JwtException，由调用方转成 401 */
    public Claims parse(String token) throws JwtException {
        return Jwts.parser()
                .verifyWith(key)
                .build()
                .parseSignedClaims(token)
                .getPayload();
    }
}
