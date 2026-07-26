"""初始化演示数据 — 包含商品、分类、测试账号、浏览记录"""
from app.database import engine, Base, SessionLocal
from app.models import (
    User, Category, Product, ProductView, Favorite, Review, Order, OrderItem
)
from app.auth import hash_password
import random


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    if db.query(User).first():
        print("数据库已有数据，跳过初始化")
        db.close()
        return

    # ====== 用户 ======
    admin = User(email="admin@smartmall.com", username="admin", hashed_password=hash_password("admin123"), role="admin")
    merchant = User(email="shop@smartmall.com", username="merchant", hashed_password=hash_password("shop123"), role="merchant")
    demo = User(email="demo@smartmall.com", username="demo", hashed_password=hash_password("demo123"), role="user")
    demo2 = User(email="test@smartmall.com", username="testuser", hashed_password=hash_password("test123"), role="user")
    db.add_all([admin, merchant, demo, demo2])
    db.flush()

    # ====== 分类 ======
    categories = [
        Category(name="运动鞋", icon="👟", sort_order=1),
        Category(name="休闲鞋", icon="👞", sort_order=2),
        Category(name="手机数码", icon="📱", sort_order=3),
        Category(name="电脑办公", icon="💻", sort_order=4),
        Category(name="服装", icon="👔", sort_order=5),
        Category(name="配饰", icon="⌚", sort_order=6),
    ]
    db.add_all(categories)
    db.flush()

    # ====== 商品 ======
    products = [
        Product(name="Nike Air Max 270", brand="Nike", price=899, original_price=1299, description="Nike Air Max 270 采用大面积Air气垫，带来极致缓震体验。轻盈透气的网面鞋面，时尚百搭。", category_id=1, sales=2341, rating=4.8, image="https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop", is_recommend=True, is_sale=True, stock=100, tags=["跑步","气垫","透气"]),
        Product(name="Adidas Ultra Boost 22", brand="Adidas", price=1099, original_price=1499, description="Boost中底科技，回弹性能卓越。Primeknit编织鞋面，包裹性极佳，跑步首选。", category_id=1, sales=1892, rating=4.9, image="https://images.unsplash.com/photo-1608231387042-66d1773070a5?w=400&h=400&fit=crop", is_recommend=True, is_new=True, stock=150, tags=["跑步","boost","回弹"]),
        Product(name="New Balance 574", brand="New Balance", price=599, original_price=799, description="经典复古跑鞋，ENCAP缓震中底，百搭休闲风格，适合日常穿搭。", category_id=2, sales=3456, rating=4.7, image="https://images.unsplash.com/photo-1539185441755-769473a23570?w=400&h=400&fit=crop", is_sale=True, stock=200, tags=["复古","休闲","百搭"]),
        Product(name="Converse Chuck 70", brand="Converse", price=459, original_price=599, description="经典高帮帆布鞋，Chuck 70升级版本，更舒适的脚感和更好的质感。", category_id=2, sales=4521, rating=4.6, image="https://images.unsplash.com/photo-1607522370275-fcfa99b8ae77?w=400&h=400&fit=crop", stock=300, tags=["帆布","高帮","经典"]),
        Product(name="Puma RS-X", brand="Puma", price=799, original_price=999, description="复古未来主义设计，RS缓震科技，大胆撞色设计，潮流必备。", category_id=1, sales=1234, rating=4.5, image="https://images.unsplash.com/photo-1606107557195-0e29a4b5b4aa?w=400&h=400&fit=crop", is_new=True, stock=80, tags=["潮流","撞色","复古"]),
        Product(name="Vans Old Skool", brand="Vans", price=399, original_price=499, description="经典侧边条纹板鞋，耐磨华夫底，街头文化标志性鞋款。", category_id=2, sales=5678, rating=4.7, image="https://images.unsplash.com/photo-1525966222134-fcfa99b8ae77?w=400&h=400&fit=crop", is_sale=True, stock=250, tags=["板鞋","街头","滑板"]),
        Product(name="Asics Gel-Kayano 29", brand="Asics", price=1199, original_price=1399, description="顶级稳定系跑鞋，GEL缓震胶+FF BLAST中底科技，长距离跑步利器。", category_id=1, sales=987, rating=4.8, image="https://images.unsplash.com/photo-1595950653106-6c9ebd614d3a?w=400&h=400&fit=crop", is_recommend=True, is_new=True, stock=60, tags=["跑步","稳定","专业"]),
        Product(name="Jordan 1 Mid", brand="Jordan", price=999, original_price=1299, description="经典中帮篮球鞋，Air-Sole气垫，传奇设计，潮流与性能并存。", category_id=1, sales=3210, rating=4.9, image="https://images.unsplash.com/photo-1556906781-9a412961c28c?w=400&h=400&fit=crop", is_sale=True, stock=90, tags=["篮球","air","经典"]),
        Product(name="iPhone 15 Pro", brand="Apple", price=7999, original_price=8999, description="A17 Pro芯片，钛金属边框，4800万像素主摄，Pro级影像体验。", category_id=3, sales=2450, rating=4.9, image="https://images.unsplash.com/photo-1695048133142-1a20484d2569?w=400&h=400&fit=crop", is_recommend=True, is_new=True, stock=40, tags=["手机","5G","旗舰"]),
        Product(name="AirPods Pro 2", brand="Apple", price=1799, original_price=1999, description="自适应降噪，H2芯片，USB-C充电，空间音频沉浸体验。", category_id=3, sales=3780, rating=4.7, image="https://images.unsplash.com/photo-1606220588913-b3aacb4d2f46?w=400&h=400&fit=crop", is_recommend=True, stock=100, tags=["耳机","降噪","蓝牙"]),
        Product(name="MacBook Air M3", brand="Apple", price=8999, original_price=9999, description="M3芯片，13.6英寸Liquid视网膜屏，18小时续航，轻薄便携。", category_id=4, sales=920, rating=4.8, image="https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=400&h=400&fit=crop", is_recommend=True, stock=30, tags=["笔记本","M3","轻薄"]),
        Product(name="iPad Air", brand="Apple", price=4799, original_price=4999, description="M1芯片，10.9英寸全面屏，支持Apple Pencil，学习创作利器。", category_id=3, sales=1320, rating=4.8, image="https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=400&h=400&fit=crop", is_new=True, is_sale=True, stock=55, tags=["平板","M1","创作"]),
        Product(name="Sony WH-1000XM5", brand="Sony", price=2599, original_price=2899, description="业界领先降噪，30小时续航，LDAC高解析度音频，舒适佩戴。", category_id=3, sales=1567, rating=4.8, image="https://images.unsplash.com/photo-1583394838336-acd977736f90?w=400&h=400&fit=crop", is_recommend=True, stock=70, tags=["耳机","降噪","头戴"]),
        Product(name="Xiaomi 14", brand="Xiaomi", price=3999, original_price=4299, description="骁龙8 Gen3，徕卡光学镜头，5000mAh电池，120W快充。", category_id=3, sales=2890, rating=4.6, image="https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=400&h=400&fit=crop", is_sale=True, stock=120, tags=["手机","5G","快充"]),
        Product(name="Logitech MX Master 3S", brand="Logitech", price=799, original_price=899, description="无线办公鼠标，8K DPI，静音点击，多设备切换，USB-C快充。", category_id=4, sales=1345, rating=4.7, image="https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=400&h=400&fit=crop", is_new=True, stock=150, tags=["鼠标","办公","无线"]),
        Product(name="Apple Watch Series 9", brand="Apple", price=2999, original_price=3199, description="S9芯片，亮度翻倍，双指互点手势，健康监测全面升级。", category_id=6, sales=1789, rating=4.7, image="https://images.unsplash.com/photo-1546868871-7041f2a55e12?w=400&h=400&fit=crop", is_recommend=True, stock=100, tags=["手表","健康","运动"]),
    ]
    db.add_all(products)
    db.flush()

    # ====== 浏览记录 (用于协同过滤) ======
    for _ in range(30):
        pv = ProductView(
            user_id=random.choice([3, 4]),  # demo, testuser
            product_id=random.choice([p.id for p in products[:8]]),
            view_count=random.randint(1, 5),
            duration=random.randint(10, 120),
        )
        db.add(pv)

    # ====== 收藏 ======
    favorites = [
        Favorite(user_id=3, product_id=1),
        Favorite(user_id=3, product_id=9),
        Favorite(user_id=4, product_id=2),
        Favorite(user_id=4, product_id=7),
    ]
    db.add_all(favorites)

    # ====== 评价 ======
    reviews = [
        Review(user_id=3, product_id=1, rating=5, content="气垫很软，跑步特别舒服！"),
        Review(user_id=4, product_id=1, rating=4, content="鞋子不错，就是价格有点贵。"),
        Review(user_id=3, product_id=9, rating=5, content="拍照效果太棒了，A17芯片性能强劲！"),
        Review(user_id=4, product_id=6, rating=5, content="经典款，百搭，质量好。"),
    ]
    db.add_all(reviews)

    db.commit()
    db.close()
    print("[OK] 数据库初始化完成！")
    print("  管理员: admin / admin123")
    print("  商家:   merchant / shop123")
    print("  用户:   demo / demo123")
    print("  用户:   testuser / test123")


if __name__ == "__main__":
    seed()
