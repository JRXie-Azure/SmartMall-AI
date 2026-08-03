package com.smartmall.controller;

import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;

import java.awt.*;
import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;

/**
 * 本地商品占位图生成器 — 生成 PNG 图片，兼容所有浏览器 img 标签。
 *
 * <p>替代 placehold.co 外部依赖，根据商品名和分类着色。
 * 端点: GET /api/placeholder/{color}/{text}
 */
@RestController
@RequestMapping("/api/placeholder")
public class PlaceholderController {

    private static final int WIDTH = 400;
    private static final int HEIGHT = 400;

    private static final Map<String, Integer> COLOR_MAP = new HashMap<>();
    static {
        COLOR_MAP.put("2563EB", 0x2563EB); // blue
        COLOR_MAP.put("0D9488", 0x0D9488); // teal
        COLOR_MAP.put("DC2626", 0xDC2626); // red
        COLOR_MAP.put("7C3AED", 0x7C3AED); // purple
        COLOR_MAP.put("EA580C", 0xEA580C); // orange
        COLOR_MAP.put("0891B2", 0x0891B2); // cyan
        COLOR_MAP.put("4F46E5", 0x4F46E5); // indigo
        COLOR_MAP.put("059669", 0x059669); // green
        COLOR_MAP.put("B91C1C", 0xB91C1C); // dark red
        COLOR_MAP.put("6D28D9", 0x6D28D9); // violet
        COLOR_MAP.put("DB2777", 0xDB2777); // pink
        COLOR_MAP.put("D97706", 0xD97706); // amber
        COLOR_MAP.put("16A34A", 0x16A34A); // green
        COLOR_MAP.put("E11D48", 0xE11D48); // rose
    }

    @GetMapping(value = "/{color}/{text}", produces = MediaType.IMAGE_PNG_VALUE)
    @ResponseBody
    public byte[] generate(@PathVariable String color, @PathVariable String text) {
        int bgColor = COLOR_MAP.getOrDefault(color.toUpperCase(), 0x2563EB);
        String displayText = decodeText(text);
        return generatePng(bgColor, displayText);
    }

    @GetMapping(value = "/{text}", produces = MediaType.IMAGE_PNG_VALUE)
    @ResponseBody
    public byte[] generateAuto(@PathVariable String text) {
        int idx = Math.abs(text.hashCode()) % COLOR_MAP.size();
        String colorKey = (String) COLOR_MAP.keySet().toArray()[idx];
        return generatePng(COLOR_MAP.get(colorKey), decodeText(text));
    }

    private byte[] generatePng(int bgColor, String displayText) {
        BufferedImage img = new BufferedImage(WIDTH, HEIGHT, BufferedImage.TYPE_INT_RGB);
        Graphics2D g = img.createGraphics();

        // Enable anti-aliasing
        g.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
        g.setRenderingHint(RenderingHints.KEY_TEXT_ANTIALIASING, RenderingHints.VALUE_TEXT_ANTIALIAS_ON);

        // Background
        g.setColor(new Color(bgColor));
        g.fillRoundRect(0, 0, WIDTH, HEIGHT, 12, 12);

        // Parse text - split on first space for brand + product name
        String[] parts = splitText(displayText);

        // Draw brand name (larger, bold)
        g.setColor(Color.WHITE);
        g.setFont(new Font("SansSerif", Font.BOLD, 28));
        FontMetrics fm = g.getFontMetrics();
        int brandY = HEIGHT / 2 - 10;
        if (parts.length > 0) {
            String brand = truncate(parts[0], fm, WIDTH - 40);
            int brandWidth = fm.stringWidth(brand);
            g.drawString(brand, (WIDTH - brandWidth) / 2, brandY);
        }

        // Draw product name (smaller)
        g.setFont(new Font("SansSerif", Font.PLAIN, 18));
        fm = g.getFontMetrics();
        if (parts.length > 1) {
            String name = truncate(parts[1], fm, WIDTH - 40);
            int nameWidth = fm.stringWidth(name);
            g.drawString(name, (WIDTH - nameWidth) / 2, brandY + 36);
        }

        // Draw decorative line
        g.setColor(new Color(255, 255, 255, 80));
        g.setStroke(new BasicStroke(2));
        g.drawLine(100, brandY + 55, 300, brandY + 55);

        g.dispose();

        try (ByteArrayOutputStream baos = new ByteArrayOutputStream()) {
            javax.imageio.ImageIO.write(img, "PNG", baos);
            return baos.toByteArray();
        } catch (Exception e) {
            // Fallback: return minimal 1x1 pixel
            return new byte[]{(byte) 0x89, (byte) 0x50, (byte) 0x4E, (byte) 0x47};
        }
    }

    private String[] splitText(String text) {
        if (text == null || text.isEmpty()) return new String[]{"?"};
        int spaceIdx = text.indexOf(' ');
        if (spaceIdx > 0 && spaceIdx < 20 && text.length() > spaceIdx + 1) {
            return new String[]{text.substring(0, spaceIdx), text.substring(spaceIdx + 1)};
        }
        return new String[]{text};
    }

    private String truncate(String s, FontMetrics fm, int maxWidth) {
        if (fm.stringWidth(s) <= maxWidth) return s;
        while (s.length() > 1 && fm.stringWidth(s + "...") > maxWidth) {
            s = s.substring(0, s.length() - 1);
        }
        return s + "...";
    }

    private String decodeText(String text) {
        try {
            return URLDecoder.decode(text, StandardCharsets.UTF_8);
        } catch (Exception e) {
            return text;
        }
    }
}
