"""
初始化演示数据 — 生产级数据规模
包含: 8分类 / 42商品 / 12用户 / 80+订单(30天) / 30+评价 / 120+浏览记录 / 15+收藏
"""
from app.database import engine, Base, SessionLocal
from app.models import (
    User, Address, Category, Product, ProductView, Favorite, Review,
    Order, OrderItem, CartItem, SearchHistory,
    ProductSKU, ProductVariant, Coupon, UserCoupon,
    MarketingCampaign, Banner,
)
from app.auth import hash_password
from datetime import datetime, timedelta
from urllib.parse import quote_plus
import random

# 按分类映射的占位图颜色 (hex, 无 #)
CAT_COLORS = {
    1: "2563EB",   # 运动鞋 - blue
    2: "0D9488",   # 休闲鞋 - teal
    3: "7C3AED",   # 手机数码 - purple
    4: "4F46E5",   # 电脑办公 - indigo
    5: "DB2777",   # 服装 - pink
    6: "D97706",   # 配饰 - amber
    7: "16A34A",   # 家居生活 - green
    8: "E11D48",   # 美妆护肤 - rose
}


# 商品名称 -> Unsplash photo ID 映射 (真实产品图片)
PRODUCT_PHOTO_IDS = {
    "Nike Air Max 270": "1542291026-7eec264c27ff",
    "Adidas Ultra Boost 22": "1606107557195-0e29a4b5b4aa",
    "Asics Gel-Kayano 29": "1595950653106-6c9ebd614d3a",
    "Jordan 1 Mid": "1597045566677-8cf032ed6634",
    "New Balance 574": "1551107696-a4b0c5a0d9a2",
    "Converse Chuck 70": "1726279243973-e7323b28cf6a",
    "Vans Old Skool": "1560858001-2a568c6ea1d7",
    "Dr. Martens 1460": "1664246310534-cf20bacd75eb",
    "Timberland 6-Inch Premium": "1729174457163-169712f5ed12",
    "iPhone 15 Pro": "1710023038502-ba80a70a9f53",
    "AirPods Pro 2": "1572569511254-d8f925fe2cbb",
    "Sony WH-1000XM5": "1618366712010-f4ae9c647dcb",
    "iPad Air": "1561154464-82e9adf32764",
    "Samsung Galaxy S24 Ultra": "1707438095940-1eee18e85400",
    "DJI Mini 4 Pro": "1507582020474-9a35b7d455d9",
    "MacBook Air M3": "1611186871348-b1ce696e52c9",
    "Logitech MX Master 3S": "1605773527852-c546a8584ea3",
    "Dell XPS 13 Plus": "1593642702821-c8da6771f0c6",
    "Lenovo ThinkPad X1 Carbon": "1626890871138-a286af648586",
    "Nike Dri-FIT Tee": "1606105961732-6332674f4ee6",
    "Levi's 501 Original Jeans": "1542272604-787c3835535d",
    "Apple Watch Series 9": "1579586337278-3befd40fd17a",
    "Ray-Ban Aviator Classic": "1572635196237-14b3f281503f",
    "Fjallraven Kanken Classic": "1671628031185-8ac6a3b29ed6",
    "Nest Learning Thermostat": "1545259741-2ea3ebf61fa3",
    # --- 新增: 补充缺失商品图片 ---
    "Puma RS-X": "1611510338559-2f463335092c",
    "Li-Ning Way of Wade 10": "1605348532760-6753d2c43329",
    "Under Armour HOVR Phantom": "1483721310020-03333e577078",
    "Saucony Endorphin Speed": "1560769629-975ec94e6a86",
    "Clarks Wallabee": "1525966222134-fcfa99b8ae77",
    "Xiaomi 14": "1511707171634-5f897ff02aa9",
    "Huawei Mate 60 Pro": "1592899677977-9c10ca588bbd",
    "ASUS ROG Strix G16": "1588872657578-7efd1f1555ed",
    "Keychron K8 Pro": "1614680376573-df3480f0c6ff",
    "Uniqlo Down Jacket": "1578587018452-892bacefd3f2",
    "Adidas Track Jacket": "1591047139829-d91aecb6caea",
    "Zara Wool Overshirt": "1620799140408-edc6dcb6d633",
    "Garmin Forerunner 265": "1523275335684-37898b6baf30",
    "Herschel Little America": "1553062407-98eeb64c6a62",
    "Dyson V15 Detect": "1581091226825-a6a2a5aee158",
    "Philips Hue Starter Kit": "1585771724684-38269d6639fd",
    "Xiaomi Air Purifier 4 Pro": "1581091226825-a6a2a5aee158",
    "La Mer Crème de la Mer": "1599305090598-fe179d501227",
    "SK-II Facial Treatment Essence": "1599305090598-fe179d501227",
    "Estée Lauder Advanced Night Repair": "1599305090598-fe179d501227",
}


def product_image_url(name: str, brand: str, cat_id: int) -> str:
    """生成商品图片 URL — 优先使用真实产品图片(Unsplash), 回退到占位图"""
    photo_id = PRODUCT_PHOTO_IDS.get(name)
    if photo_id:
        return f"https://images.unsplash.com/photo-{photo_id}?w=400&h=400&fit=crop&q=80"
    # 回退: 占位图
    color = CAT_COLORS.get(cat_id, "6366F1")
    text = quote_plus(f"{brand}\n{name}")
    return f"https://placehold.co/400x400/{color}/ffffff?text={text}&font=montserrat"


# ====== 用户数据 ======
USERS = [
    ("admin@smartmall.com", "admin", "admin123", "admin"),
    ("shop@smartmall.com", "merchant", "shop123", "merchant"),
    # 普通用户 — 邮箱后缀多样化 (qq/163/gmail/outlook/foxmail)
    ("zhangwei2008@qq.com", "zhangwei", "zw123456", "user"),
    ("liling_95@163.com", "liling", "ll123456", "user"),
    ("wangfang.sc@gmail.com", "wangfang", "wf123456", "user"),
    ("liuyang2024@outlook.com", "liuyang", "ly123456", "user"),
    ("chenjie@foxmail.com", "chenjie", "cj123456", "user"),
    ("zhaomin_07@qq.com", "zhaomin", "zm123456", "user"),
    ("sunli@163.com", "sunli", "sl123456", "user"),
    ("zhouqi668@gmail.com", "zhouqi", "zq123456", "user"),
]

# ====== 地址数据 (跨 6 个城市, 手机号用真实号段) ======
ADDRESSES = [
    ("张伟", "13812345678", "广东", "深圳", "南山", "科技园南路 16 号滨海大厦"),
    ("李玲", "13987654321", "北京", "北京", "朝阳", "建国路 91 号金地中心 A 座"),
    ("王芳", "13501234567", "上海", "上海", "浦东", "世纪大道 100 号环球金融中心"),
    ("刘洋", "18611112222", "广东", "广州", "天河", "珠江新城兴民路 222 号天盈广场"),
    ("陈杰", "18833334444", "浙江", "杭州", "西湖", "文三路 478 号华星时代广场"),
    ("赵敏", "15955556666", "四川", "成都", "高新", "天府大道中段 1388 号天府国际金融中心"),
    ("孙丽", "13777778888", "湖北", "武汉", "武昌", "中南路 99 号保利广场 B 座"),
    ("周琪", "15299990000", "上海", "上海", "徐汇", "漕溪北路 333 号徐家汇中心"),
]

# ====== 分类数据 ======
CATEGORIES = [
    ("运动鞋", "👟", 1),
    ("休闲鞋", "👞", 2),
    ("手机数码", "📱", 3),
    ("电脑办公", "💻", 4),
    ("服装", "👔", 5),
    ("配饰", "⌚", 6),
    ("家居生活", "🏠", 7),
    ("美妆护肤", "💄", 8),
]

# ====== 商品数据 (name, brand, price, original_price, desc, cat_id, sales, rating, tags, flags) ======
PRODUCTS = [
    # --- 运动鞋 (cat_id=1) ---
    ("Nike Air Max 270", "Nike", 899, 1299, "Nike Air Max 270 采用大面积Air气垫，带来极致缓震体验。轻盈透气的网面鞋面，时尚百搭。", 1, 2341, 4.8, ["跑步","气垫","透气"], "recommend,sale"),
    ("Adidas Ultra Boost 22", "Adidas", 1099, 1499, "Boost中底科技，回弹性能卓越。Primeknit编织鞋面，包裹性极佳，跑步首选。", 1, 1892, 4.9, ["跑步","boost","回弹"], "recommend,new"),
    ("Asics Gel-Kayano 29", "Asics", 1199, 1399, "顶级稳定系跑鞋，GEL缓震胶+FF BLAST中底科技，长距离跑步利器。", 1, 987, 4.8, ["跑步","稳定","专业"], "recommend,new"),
    ("Puma RS-X", "Puma", 799, 999, "复古未来主义设计，RS缓震科技，大胆撞色设计，潮流必备。", 1, 1234, 4.5, ["潮流","撞色","复古"], "new"),
    ("Jordan 1 Mid", "Jordan", 999, 1299, "经典中帮篮球鞋，Air-Sole气垫，传奇设计，潮流与性能并存。", 1, 3210, 4.9, ["篮球","air","经典"], "sale"),
    ("Li-Ning Way of Wade 10", "Li-Ning", 699, 899, "韦德之道10代，碳板+䨻科技，实战篮球鞋顶级之选。", 1, 856, 4.6, ["篮球","碳板","实战"], ""),
    ("Under Armour HOVR Phantom", "Under Armour", 849, 1099, "HOVR缓震科技，智能芯片记录跑步数据，连接MapRun App。", 1, 643, 4.4, ["跑步","智能","缓震"], ""),
    ("Saucony Endorphin Speed", "Saucony", 1299, 1499, "尼龙板PWRRUN PB中底，速度型跑鞋，竞速利器。", 1, 432, 4.7, ["跑步","竞速","轻量"], "new"),

    # --- 休闲鞋 (cat_id=2) ---
    ("New Balance 574", "New Balance", 599, 799, "经典复古跑鞋，ENCAP缓震中底，百搭休闲风格，适合日常穿搭。", 2, 3456, 4.7, ["复古","休闲","百搭"], "sale"),
    ("Converse Chuck 70", "Converse", 459, 599, "经典高帮帆布鞋，Chuck 70升级版本，更舒适的脚感和更好的质感。", 2, 4521, 4.6, ["帆布","高帮","经典"], ""),
    ("Vans Old Skool", "Vans", 399, 499, "经典侧边条纹板鞋，耐磨华夫底，街头文化标志性鞋款。", 2, 5678, 4.7, ["板鞋","街头","滑板"], "sale"),
    ("Dr. Martens 1460", "Dr. Martens", 1299, 1599, "经典8孔马丁靴，Goodyear缝制工艺，耐穿耐看，英伦风必备。", 2, 2103, 4.8, ["马丁靴","英伦","复古"], "recommend"),
    ("Timberland 6-Inch Premium", "Timberland", 1499, 1799, "经典6寸工装靴，防水全粒面皮，坚固耐穿，户外潮流标志。", 2, 1876, 4.7, ["工装靴","防水","户外"], ""),
    ("Clarks Wallabee", "Clarks", 799, 999, "经典袋鼠鞋，流线型鞋身，Crepe生胶底，舒适复古。", 2, 987, 4.5, ["复古","舒适","休闲"], ""),

    # --- 手机数码 (cat_id=3) ---
    ("iPhone 15 Pro", "Apple", 7999, 8999, "A17 Pro芯片，钛金属边框，4800万像素主摄，Pro级影像体验。", 3, 2450, 4.9, ["手机","5G","旗舰"], "recommend,new"),
    ("AirPods Pro 2", "Apple", 1799, 1999, "自适应降噪，H2芯片，USB-C充电，空间音频沉浸体验。", 3, 3780, 4.7, ["耳机","降噪","蓝牙"], "recommend"),
    ("Xiaomi 14", "Xiaomi", 3999, 4299, "骁龙8 Gen3，徕卡光学镜头，5000mAh电池，120W快充。", 3, 2890, 4.6, ["手机","5G","快充"], "sale"),
    ("Sony WH-1000XM5", "Sony", 2599, 2899, "业界领先降噪，30小时续航，LDAC高解析度音频，舒适佩戴。", 3, 1567, 4.8, ["耳机","降噪","头戴"], "recommend"),
    ("iPad Air", "Apple", 4799, 4999, "M1芯片，10.9英寸全面屏，支持Apple Pencil，学习创作利器。", 3, 1320, 4.8, ["平板","M1","创作"], "new,sale"),
    ("Samsung Galaxy S24 Ultra", "Samsung", 8999, 9999, "骁龙8 Gen3，2亿像素，S Pen手写笔，钛金属边框，AI手机。", 3, 1654, 4.7, ["手机","5G","AI"], "new"),
    ("Huawei Mate 60 Pro", "Huawei", 6999, 7999, "麒麟9000S芯片，卫星通话，昆仑玻璃，XMAGE影像。", 3, 2103, 4.8, ["手机","5G","卫星"], "recommend"),
    ("DJI Mini 4 Pro", "DJI", 4788, 5288, "249g轻量无人机，全向避障，4K/100fps HDR视频，O4图传。", 3, 876, 4.7, ["无人机","4K","航拍"], "new"),

    # --- 电脑办公 (cat_id=4) ---
    ("MacBook Air M3", "Apple", 8999, 9999, "M3芯片，13.6英寸Liquid视网膜屏，18小时续航，轻薄便携。", 4, 920, 4.8, ["笔记本","M3","轻薄"], "recommend"),
    ("Logitech MX Master 3S", "Logitech", 799, 899, "无线办公鼠标，8K DPI，静音点击，多设备切换，USB-C快充。", 4, 1345, 4.7, ["鼠标","办公","无线"], "new"),
    ("Dell XPS 13 Plus", "Dell", 9999, 10999, "13.4英寸OLED屏，Intel酷睿Ultra7，轻薄设计，生产力利器。", 4, 543, 4.6, ["笔记本","OLED","轻薄"], ""),
    ("Lenovo ThinkPad X1 Carbon", "Lenovo", 12999, 13999, "14英寸商务旗舰，碳纤维机身，Intel酷睿Ultra7，军标认证。", 4, 432, 4.7, ["笔记本","商务","碳纤维"], ""),
    ("ASUS ROG Strix G16", "ASUS", 14999, 16999, "RTX 4070游戏本，16英寸240Hz屏，i9-14900HX，电竞利器。", 4, 678, 4.6, ["游戏本","RTX4070","电竞"], "new"),
    ("Keychron K8 Pro", "Keychron", 599, 699, "无线机械键盘，热插拔轴体，RGB背光，Mac/Win双模。", 4, 2345, 4.7, ["键盘","机械","无线"], "sale"),

    # --- 服装 (cat_id=5) ---
    ("Uniqlo Down Jacket", "Uniqlo", 599, 799, "高级轻羽绒，640蓬松度，可收纳袋，轻暖便携。", 5, 4521, 4.6, ["羽绒服","保暖","轻量"], "sale"),
    ("Nike Dri-FIT Tee", "Nike", 199, 259, "Dri-FIT速干面料，运动T恤，透气排汗，多色可选。", 5, 6789, 4.5, ["T恤","速干","运动"], ""),
    ("Levi's 501 Original Jeans", "Levi's", 599, 799, "经典501直筒牛仔裤，原色丹宁，百搭不挑人，永恒经典。", 5, 3456, 4.7, ["牛仔裤","经典","直筒"], ""),
    ("Adidas Track Jacket", "Adidas", 399, 499, "经典三条纹运动夹克，Regular Fit，全拉链设计，运动休闲。", 5, 2345, 4.5, ["夹克","运动","三条纹"], "sale"),
    ("Zara Wool Overshirt", "Zara", 459, 599, "美利奴羊毛混纺衬衫外套，简约设计，秋冬叠穿利器。", 5, 1234, 4.4, ["衬衫","羊毛","秋冬"], "new"),

    # --- 配饰 (cat_id=6) ---
    ("Apple Watch Series 9", "Apple", 2999, 3199, "S9芯片，亮度翻倍，双指互点手势，健康监测全面升级。", 6, 1789, 4.7, ["手表","健康","运动"], "recommend"),
    ("Garmin Forerunner 265", "Garmin", 3280, 3680, "AMOLED屏，多星定位，跑步功率，专业运动手表。", 6, 567, 4.6, ["手表","GPS","跑步"], "new"),
    ("Ray-Ban Aviator Classic", "Ray-Ban", 1280, 1480, "经典飞行员太阳镜，G-15镜片，金属框架，永恒经典。", 6, 1890, 4.7, ["太阳镜","飞行员","经典"], ""),
    ("Herschel Little America", "Herschel", 699, 899, "经典双肩背包，25L容量，笔记本电脑隔层，磁扣翻盖设计。", 6, 1567, 4.6, ["背包","双肩","通勤"], ""),
    ("Fjallraven Kanken Classic", "Fjallraven", 599, 699, "经典Kanken双肩包，Vinylon F面料，轻量耐磨，北欧设计。", 6, 3456, 4.7, ["背包","轻量","耐磨"], "sale"),

    # --- 家居生活 (cat_id=7) ---
    ("Dyson V15 Detect", "Dyson", 4690, 5290, "激光探测灰尘，压电传感器计数，LCD屏显，240AW强劲吸力。", 7, 1234, 4.8, ["吸尘器","无绳","激光"], "recommend"),
    ("Philips Hue Starter Kit", "Philips", 999, 1299, "智能LED灯泡3只+网桥，1600万色，语音控制，场景模式。", 7, 876, 4.5, ["智能灯","LED","语音"], "new"),
    ("Xiaomi Air Purifier 4 Pro", "Xiaomi", 1599, 1899, "CADR 500m³/h，OLED触控屏，甲醛数字显示，APP远程控制。", 7, 1543, 4.6, ["净化器","甲醛","智能"], "sale"),
    ("Nest Learning Thermostat", "Google", 1899, 2199, "第三代学习型温控器，自动学习习惯，节能20%，远程控制。", 7, 432, 4.5, ["温控器","智能","节能"], ""),

    # --- 美妆护肤 (cat_id=8) ---
    ("La Mer Crème de la Mer", "La Mer", 2800, 3200, "神奇活性精萃，深层滋润修复，奢华面霜，焕新肌肤。", 8, 567, 4.8, ["面霜","奢华","修复"], "recommend"),
    ("SK-II Facial Treatment Essence", "SK-II", 1590, 1790, "PITERA精华露，90%浓度，改善肤质，提亮肤色。", 8, 890, 4.7, ["精华","PITERA","提亮"], ""),
    ("Estée Lauder Advanced Night Repair", "Estée Lauder", 1080, 1280, "第七代小棕瓶，夜间修复精华，抗老紧致，保湿补水。", 8, 1234, 4.6, ["精华","抗老","修复"], "sale"),
]

# ====== 评价模板 (按品类定制, {} 会被替换为品牌名) ======
REVIEW_TEMPLATES_BY_CATEGORY = {
    1: {  # 运动鞋
        5: [
            "缓震效果真的绝了，跑了10公里膝盖完全不疼，{}气垫名不虚传",
            "比专柜便宜两百多，正品无疑。刚开始穿有点紧，两天就合脚了",
            "中底踩屎感十足，日常通勤和跑步都穿，已经回购第二双",
            "缓震确实强，之前穿别的跑鞋跑半马脚底板疼，这双完全没有",
            "轻到离谱！上脚几乎感觉不到重量，配速明显提升了",
            "{}的做工没得说，穿了三个月没变形没开胶，值这个价",
            "网面透气性很好，夏天跑完脚不闷，鞋底回弹也给力",
        ],
        4: [
            "缓震不错，就是鞋面有点闷，夏天穿可能热",
            "鞋子挺好，码数偏小半码，建议买大一号",
            "跑了200公里中底还没塌，就是鞋面有点起球",
            "{}颜值在线性能也行，就是价格小贵，等活动再入手",
        ],
        3: [
            "缓震一般，没有宣传的那么神，可能我体重太大（85kg）",
            "穿了两次鞋带就起毛了，做工配不上这个价",
        ],
    },
    2: {  # 休闲鞋
        5: [
            "经典款永远不过时，底很舒服，日常通勤神器",
            "比普通款质感好太多，鞋底更厚更软，帆布也更扎实",
            "{}侧边条纹永远的神，搭什么都好看，耐磨底滑板也OK",
            "做工扎实，缝线很平整，穿三年都不会坏",
            "收到了，防水效果不错，下雨天终于不用换鞋了",
            "复古百搭，裤脚堆叠刚刚好，上班穿也不违和",
        ],
        4: [
            "好看是好看，就是有点重，走久了脚累",
            "经典款没得说，就是新鞋有点磨脚踝，穿一周就好了",
            "质感不错，但颜色比图片深一点，不过也好看",
        ],
        3: [
            "底太硬了，没有运动鞋那种缓震感，当休闲鞋穿还行",
        ],
    },
    3: {  # 手机数码 (手机/耳机/平板/无人机)
        5: [
            "{}的生态体验确实好，设备间切换无缝衔接，用过就回不去了",
            "做工质感一流，拿在手里就能感觉到品质，对得起这个价格",
            "续航比预期好很多，重度使用一天下来还有余量",
            "音质/画质超出预期，这个价位段很难找到更好的了",
            "{}的品控一直在线，用了两个月没有任何问题，放心入手",
            "连接速度很快，延迟几乎感觉不到，日常使用体验拉满",
        ],
        4: [
            "整体体验不错，就是发热控制一般，长时间使用会降频",
            "功能都满意，就是续航稍弱，得养成随身带充电器的习惯",
            "{}东西好是好，就是定价偏高，等活动降价再考虑",
        ],
        3: [
            "信号/连接稳定性不如预期，偶尔会断开，固件有待优化",
        ],
    },
    4: {  # 电脑办公 (笔记本/鼠标/键盘)
        5: [
            "{}的做工没得说，用了两周体验非常顺畅，多任务处理完全不卡",
            "响应速度很快，办公效率明显提升，设计也很人性化",
            "质感一流放在桌面上很有档次，{}的设计确实用心了",
            "性能完全够用，日常办公加偶尔的创意工作都能胜任",
            "稳定性很好，连续用一周没出过任何问题，值这个价",
            "{}的细节做得到位，手感/体验都对得起这个价位",
        ],
        4: [
            "性能不错，就是长时间高负载会发热，建议配个散热支架",
            "整体满意，就是便携性一般，出差带着有点重",
            "性价比还行，就是品控偶有小瑕疵，不影响使用",
        ],
        3: [
            "用了一周遇到两次死机，固件稳定性有待提升",
        ],
    },
    5: {  # 服装 (羽绒服/T恤/牛仔裤/夹克)
        5: [
            "{}的面料手感很好，穿了一天就觉得很舒服，做工也对得起价格",
            "版型很正，上身效果比预期好，尺码标准不偏大偏小",
            "面料舒服透气，洗了几次没变形没起球，质量过硬",
            "剪裁合身，细节做工到位，{}的设计确实用心了",
            "颜色和图片一致没有色差，上身很有质感，已经推荐给同事",
        ],
        4: [
            "整体不错，就是拉链/纽扣有点紧，用几次就好了",
            "版型可以，但颜色比图片浅一点，不过穿上也好看",
            "面料还行，就是有点薄，深秋穿得加内搭",
        ],
        3: [
            "洗了一次缩水了，建议冷水手洗，做工一般",
        ],
    },
    6: {  # 配饰 (手表/太阳镜/背包)
        5: [
            "{}的做工没得说，质感拉满，日常佩戴/使用很有档次",
            "设计经典耐看，搭什么风格都不违和，性价比很高",
            "轻量化设计很贴心，长时间佩戴/使用也不累，{}细节到位",
            "功能/实用性超出预期，做工扎实，用过就知道值不值",
            "{}的品质一直在线，这个价位很难找到更好的替代了",
        ],
        4: [
            "整体满意，就是续航/耐用性一般，得注意保养",
            "颜值在线，就是刚上手有点不习惯，磨合几天就好了",
            "功能够用，就是某些细节可以更人性化",
        ],
        3: [
            "数据/功能不太精准，和宣传的有差距，其他方面还行",
        ],
    },
    7: {  # 家居生活 (吸尘器/智能灯/净化器/温控器)
        5: [
            "{}的智能体验确实好，App控制很流畅，设置也简单",
            "效果比预期明显，用了一周就能感受到差异，值得入手",
            "噪音控制得很好，不会打扰到家人，{}品质值得信赖",
            "操作简单，家里老人也会用，性价比很高",
            "{}的设计很贴心，解决了日常生活的痛点，体验拉满",
        ],
        4: [
            "效果不错，就是最高档噪音偏大，日常用中档刚好",
            "功能齐全，就是App偶尔断连，重启就好",
            "整体满意，就是体积偏大，小户型放有点占地方",
        ],
        3: [
            "App连接不稳定，经常掉线需要重新配对，固件待优化",
        ],
    },
    8: {  # 美妆护肤 (面霜/精华)
        5: [
            "{}的效果确实好，用了两周干燥/暗沉明显改善，贵有贵的道理",
            "质地很润但不油腻，上脸吸收快，第二天早上皮肤状态很好",
            "敏感肌用着没刺激，保湿效果持久，已经回购第二瓶",
            "用了一个月肤质明显变好，毛孔细腻了肤色也均匀了",
            "{}的肤感做得很好，不搓泥不闷痘，后续上妆也服帖",
        ],
        4: [
            "效果有，但见效慢，坚持用了一个月才看到变化",
            "保湿不错，就是香味偏浓，不喜欢香精味慎入",
            "肤感好，但容量偏小，日常用一个月就见底了",
        ],
        3: [
            "可能肤质不合适，用了长闭口，停用后恢复正常",
        ],
    },
}


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    if db.query(User).first():
        print("数据库已有数据，跳过初始化")
        db.close()
        return

    now = datetime.now()
    random.seed(42)  # 可复现

    # ====== 创建用户 ======
    user_objs = []
    for email, username, password, role in USERS:
        u = User(
            email=email, username=username,
            hashed_password=hash_password(password), role=role,
            created_at=now - timedelta(days=random.randint(30, 90)),
        )
        user_objs.append(u)
    db.add_all(user_objs)
    db.flush()

    # ====== 创建地址 ======
    addr_objs = []
    for i, (name, phone, prov, city, dist, detail) in enumerate(ADDRESSES):
        addr = Address(
            user_id=user_objs[i + 2].id,  # 普通用户开始
            name=name, phone=phone,
            province=prov, city=city, district=dist, detail=detail,
            is_default=(i == 0),
        )
        addr_objs.append(addr)
    db.add_all(addr_objs)
    db.flush()

    # ====== 创建分类 ======
    cat_objs = []
    for name, icon, sort in CATEGORIES:
        cat_objs.append(Category(name=name, icon=icon, sort_order=sort))
    db.add_all(cat_objs)
    db.flush()

    # ====== 创建商品 ======
    product_objs = []
    for name, brand, price, orig, desc, cat_id, sales, rating, tags, flags in PRODUCTS:
        p = Product(
            name=name, brand=brand, price=price, original_price=orig,
            description=desc, category_id=cat_id, sales=sales, rating=rating,
            image=product_image_url(name, brand, cat_id),
            images=[product_image_url(name, brand, cat_id) for _ in range(3)],
            tags=tags, stock=random.randint(30, 300),
            is_recommend="recommend" in flags,
            is_new="new" in flags,
            is_sale="sale" in flags,
            is_active=True,
            audit_status="approved",
            created_at=now - timedelta(days=random.randint(10, 60)),
        )
        product_objs.append(p)
    db.add_all(product_objs)
    db.flush()

    # ====== 浏览记录 (120+ 条，用于协同过滤) ======
    regular_user_ids = [u.id for u in user_objs if u.role == "user"]
    seen_views = set()
    for _ in range(150):
        uid = random.choice(regular_user_ids)
        pid = random.choice([p.id for p in product_objs])
        key = (uid, pid)
        if key in seen_views:
            continue
        seen_views.add(key)
        db.add(ProductView(
            user_id=uid, product_id=pid,
            view_count=random.randint(1, 8),
            duration=random.randint(10, 300),
            created_at=now - timedelta(days=random.randint(0, 20)),
        ))

    # ====== 收藏 (20+ 条) ======
    seen_favs = set()
    for _ in range(25):
        uid = random.choice(regular_user_ids)
        pid = random.choice([p.id for p in product_objs])
        key = (uid, pid)
        if key in seen_favs:
            continue
        seen_favs.add(key)
        db.add(Favorite(user_id=uid, product_id=pid,
                        created_at=now - timedelta(days=random.randint(0, 15))))

    # ====== 评价 (确保每个商品至少 1 条，共 75+ 条) ======
    def get_review_content(product, rating):
        """根据商品品类获取专属评价内容，{} 替换为品牌名"""
        cat_templates = REVIEW_TEMPLATES_BY_CATEGORY.get(product.category_id, {})
        if rating not in cat_templates or not cat_templates[rating]:
            rating = sorted(cat_templates.keys())[0]  # 取最高分
        template = random.choice(cat_templates[rating])
        return template.format(product.brand)

    # 先给每个商品至少 1 条评价
    for p in product_objs:
        uid = random.choice(regular_user_ids)
        rating = random.choices([5, 4, 3], weights=[0.6, 0.3, 0.1])[0]
        content = get_review_content(p, rating)
        db.add(Review(
            user_id=uid, product_id=p.id, rating=rating, content=content,
            created_at=now - timedelta(days=random.randint(1, 25)),
        ))
    # 再随机补充评价，热门商品评价更多
    for _ in range(30):
        uid = random.choice(regular_user_ids)
        p = random.choice(product_objs)
        rating = random.choices([5, 4, 3], weights=[0.6, 0.3, 0.1])[0]
        content = get_review_content(p, rating)
        db.add(Review(
            user_id=uid, product_id=p.id, rating=rating, content=content,
            created_at=now - timedelta(days=random.randint(1, 25)),
        ))

    # ====== 订单 (90+ 条，分布在 30 天内) ======
    order_statuses = ["pending", "paid", "shipped", "completed", "cancelled"]
    status_weights = [0.10, 0.15, 0.20, 0.50, 0.05]
    payment_methods = ["alipay", "wechat", "credit_card"]

    names_map = {u.id: u.username for u in user_objs}
    # 构建用户地址映射 (订单收货地址用用户真实地址)
    user_addr_map = {a.user_id: a for a in addr_objs}

    for i in range(95):
        uid = random.choice(regular_user_ids)
        # 最近 30 天内随机时间，前几天多一些
        days_ago = random.choices(
            range(30),
            weights=[max(1, 30 - d) for d in range(30)],
        )[0]
        created_at = now - timedelta(days=days_ago, hours=random.randint(0, 23), minutes=random.randint(0, 59))
        status = random.choices(order_statuses, weights=status_weights)[0]

        # 每个订单 1~4 个商品
        items_count = random.choices([1, 2, 3, 4], weights=[0.4, 0.3, 0.2, 0.1])[0]
        chosen = random.sample(product_objs, min(items_count, len(product_objs)))
        total_amount = 0
        order_items_data = []

        for p in chosen:
            qty = random.choices([1, 2, 3], weights=[0.7, 0.2, 0.1])[0]
            total_amount += round(p.price * qty, 2)
            order_items_data.append({"product": p, "quantity": qty, "price": p.price})

        # 使用用户真实注册地址作为收货地址
        addr = user_addr_map.get(uid)
        if addr:
            addr_snap = {
                "name": addr.name, "phone": addr.phone,
                "province": addr.province, "city": addr.city,
                "district": addr.district, "detail": addr.detail,
            }
        else:
            addr_snap = {
                "name": names_map.get(uid, "用户"), "phone": "13800000000",
                "province": "广东", "city": "深圳",
                "district": "南山", "detail": "科技园路 1 号",
            }

        order = Order(
            user_id=uid,
            order_no=f"SM{created_at.strftime('%Y%m%d')}{str(1001 + i).zfill(4)}",
            status=status,
            total_amount=round(total_amount, 2),
            address_snapshot=addr_snap,
            note="",
            payment_method=random.choice(payment_methods) if status != "pending" else "",
            created_at=created_at,
        )

        if status in ("paid", "shipped", "completed"):
            order.paid_at = created_at + timedelta(minutes=random.randint(5, 120))
        if status in ("shipped", "completed"):
            order.shipped_at = order.paid_at + timedelta(hours=random.randint(2, 72))
            order.tracking_no = f"SF{random.randint(100000000, 999999999)}"
            order.logistics_company = random.choice(["顺丰速运", "京东物流", "中通快递"])
        if status == "completed":
            order.completed_at = order.shipped_at + timedelta(days=random.randint(2, 7))

        db.add(order)
        db.flush()

        for item in order_items_data:
            db.add(OrderItem(
                order_id=order.id,
                product_id=item["product"].id,
                product_name=item["product"].name,
                product_image=item["product"].image,
                price=item["price"],
                quantity=item["quantity"],
            ))

    # ====== 购物车 (一些用户有购物车商品) ======
    for uid in random.sample(regular_user_ids, 4):
        for p in random.sample(product_objs, random.randint(1, 3)):
            db.add(CartItem(user_id=uid, product_id=p.id, quantity=random.randint(1, 2)))

    # ====== 搜索历史 ======
    search_keywords = ["跑鞋", "iPhone", "耳机", "背包", "羽绒服", "降噪", "机械键盘", "面霜"]
    for uid in regular_user_ids[:6]:
        for kw in random.sample(search_keywords, random.randint(2, 4)):
            db.add(SearchHistory(
                user_id=uid, keyword=kw, result_count=random.randint(3, 20),
                created_at=now - timedelta(days=random.randint(0, 10)),
            ))

    # ====== 商品 SKU 和规格 ======
    # 为部分商品添加规格和 SKU
    for i, p in enumerate(product_objs):
        if i % 5 == 0:  # 每5个商品添加规格
            colors = ["红色", "蓝色", "黑色", "白色"]
            sizes = ["S", "M", "L", "XL"]
            color_variant = ProductVariant(
                product_id=p.id,
                name="颜色",
                options=colors,
            )
            size_variant = ProductVariant(
                product_id=p.id,
                name="尺寸",
                options=sizes,
            )
            db.add(color_variant)
            db.add(size_variant)
            db.flush()

            for ci, color in enumerate(colors):
                for si, size in enumerate(sizes):
                    attrs = {"颜色": color, "尺寸": size}
                    price_adj = 1.0 + ci * 0.03
                    sku = ProductSKU(
                        product_id=p.id,
                        sku_code=f"P{p.id}-{ci+1}{si+1}",
                        attributes=attrs,
                        price=round(p.price * price_adj, 2),
                        stock=random.randint(10, 50),
                        image=p.image,
                        is_active=True,
                    )
                    db.add(sku)

    # ====== 优惠券 ======
    coupon_types = [
        ("fixed", "满100减20", 20, 100, 0),
        ("fixed", "满200减50", 50, 200, 0),
        ("percent", "9折优惠", 10, 0, 50),
        ("fixed", "新用户立减10元", 10, 0, 0),
        ("percent", "会员85折", 15, 0, 100),
    ]
    coupon_objs = []
    for i, (ctype, name, value, min_amt, max_discount) in enumerate(coupon_types):
        coupon = Coupon(
            code=f"SMART{1000 + i * 111}",
            name=name,
            description=f"{name}优惠券",
            discount_type=ctype,
            discount_value=value,
            min_order_amount=min_amt,
            max_discount=max_discount,
            valid_from=now - timedelta(days=10),
            valid_until=now + timedelta(days=30),
            total_limit=100 if i < 3 else 50,
            per_user_limit=2,
            is_active=True,
        )
        db.add(coupon)
        coupon_objs.append(coupon)
    db.flush()
    # 为部分用户发放优惠券
    for c in coupon_objs:
        for uid in random.sample(regular_user_ids, min(6, len(regular_user_ids))):
            db.add(UserCoupon(user_id=uid, coupon_id=c.id))

    # ====== 营销活动 ======
    campaigns = [
        ("discount", "夏季清仓", "全场夏季商品8折起", 20, 0),
        ("flash_sale", "限时秒杀", "每日10点限量秒杀", 50, 0),
        ("full_reduction", "满减活动", "满300减30，满500减60", 30, 300),
    ]
    campaign_images = [
        "https://picsum.photos/seed/1523348837708-15d4a09cfac2/400/400",
        "https://picsum.photos/seed/1494976040374-85c8e12f0c0e/400/400",
        "https://picsum.photos/seed/1560472127-14a111a86466/400/400",
    ]
    for i, (ctype, name, desc, discount, min_amt) in enumerate(campaigns):
        campaign = MarketingCampaign(
            name=name,
            campaign_type=ctype,
            description=desc,
            banner_image=campaign_images[i],
            discount_value=discount,
            min_order_amount=min_amt,
            start_time=now - timedelta(days=5),
            end_time=now + timedelta(days=25),
            is_active=True,
        )
        db.add(campaign)

    # ====== Banner 轮播图 ======
    banners = [
        ("夏季新品上市", "https://picsum.photos/seed/1591035897211-89f8db6a8f0a/400/400", "/products?category=5"),
        ("AI智能推荐", "https://picsum.photos/seed/1551269901-5c5e14c25df7/400/400", "/ai-chat"),
        ("会员专享优惠", "https://picsum.photos/seed/1560518883-ce09059eeffa/400/400", "/user"),
        ("限时特惠专场", "https://picsum.photos/seed/1572867055423-04b84104b8b1/400/400", "/products"),
    ]
    for i, (title, img, link) in enumerate(banners):
        banner = Banner(
            title=title,
            image=img,
            link=link,
            sort_order=i,
            is_active=True,
        )
        db.add(banner)

    db.commit()
    db.close()

    print("[OK] 数据库初始化完成！")
    print(f"  用户: {len(USERS)} 个 (admin/merchant + {len(USERS)-2} 普通用户)")
    print(f"  商品: {len(PRODUCTS)} 个 ({len(CATEGORIES)} 个分类)")
    print(f"  订单: 95+ 笔 (分布在最近 30 天, 6 城市)")
    print(f"  评价: 75+ 条 (按品类定制, 每个商品至少 1 条)")
    print(f"  浏览: 150+ 条 (协同过滤数据)")
    print(f"  收藏: 25+ 条")
    print(f"  SKU: 若干 (每5个商品含颜色/尺寸规格)")
    print(f"  优惠券: 5 张")
    print(f"  营销活动: 3 个")
    print(f"  Banner: 4 张")
    print()
    print("  管理员: admin / admin123")
    print("  商家:   merchant / shop123")
    print("  用户:   zhangwei / zw123456")


if __name__ == "__main__":
    seed()
