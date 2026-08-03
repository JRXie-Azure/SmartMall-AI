package com.smartmall.config;

import com.smartmall.security.CurrentUserArgumentResolver;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.method.support.HandlerMethodArgumentResolver;
import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.List;

/**
 * 静态资源与参数解析器。
 *
 * <p>前端 index.html 用相对路径调 /api/...，因此必须由后端同源托管，
 * 否则跨域 + Token 存储都要改前端。这里直接复用 Python 版的 backend/static，
 * 保证两套后端跑的是同一份前端代码，不会出现"改了一边忘了另一边"。
 */
@Slf4j
@Configuration
@RequiredArgsConstructor
public class WebMvcConfig implements WebMvcConfigurer {

    private final CurrentUserArgumentResolver currentUserArgumentResolver;
    private final SmartMallProperties props;

    @Override
    public void addArgumentResolvers(List<HandlerMethodArgumentResolver> resolvers) {
        resolvers.add(currentUserArgumentResolver);
    }

    @Override
    public void addResourceHandlers(ResourceHandlerRegistry registry) {
        List<String> staticLocations = new ArrayList<>();
        Path resolved = resolveStaticDir();
        if (resolved != null) {
            staticLocations.add(resolved.toUri().toString());
            log.info("前端静态目录: {}", resolved);
        }
        staticLocations.add("classpath:/static/");

        registry.addResourceHandler("/static/**")
                .addResourceLocations(staticLocations.toArray(String[]::new));

        // 根路径下的资源 (index.html 及其同级文件)
        registry.addResourceHandler("/**")
                .addResourceLocations(staticLocations.toArray(String[]::new));

        // 上传目录
        Path uploadDir = Paths.get(props.getUpload().getDir()).toAbsolutePath().normalize();
        try {
            Files.createDirectories(uploadDir);
        } catch (IOException e) {
            log.warn("上传目录创建失败: {}", uploadDir, e);
        }
        registry.addResourceHandler("/uploads/**")
                .addResourceLocations(uploadDir.toUri().toString());
    }

    /** 返回第一个存在的静态目录，都不存在返回 null（回落 classpath） */
    private Path resolveStaticDir() {
        for (String candidate : props.getWeb().getStaticDirs()) {
            Path p = Paths.get(candidate).toAbsolutePath().normalize();
            if (Files.isDirectory(p)) {
                return p;
            }
        }
        return null;
    }
}
