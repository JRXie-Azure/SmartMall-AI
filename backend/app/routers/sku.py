"""
商品 SKU 路由 — 规格变体管理
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ProductSKU, ProductVariant, Product, User as UserModel
from app.auth import get_current_admin
from app.schemas import ProductSKUCreate, ProductSKUOut, ProductVariantCreate, ProductVariantOut

router = APIRouter(prefix="/api/skus", tags=["商品SKU"])


@router.get("/product/{product_id}")
def get_product_skus(product_id: int, db: Session = Depends(get_db)):
    """获取商品的所有 SKU 和规格模板"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    return {
        "variants": [
            {"id": v.id, "name": v.name, "options": v.options}
            for v in product.variants
        ],
        "skus": [
            {
                "id": s.id, "sku_code": s.sku_code, "attributes": s.attributes,
                "price": s.price, "stock": s.stock, "image": s.image,
                "is_active": s.is_active,
            }
            for s in product.skus if s.is_active
        ],
    }


@router.post("/product/{product_id}/variants")
def create_variant(
    product_id: int,
    data: ProductVariantCreate,
    db: Session = Depends(get_db),
    admin: UserModel = Depends(get_current_admin),
):
    """创建商品规格模板 (如: 颜色)"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    variant = ProductVariant(
        product_id=product_id,
        name=data.name,
        options=data.options,
    )
    db.add(variant)
    db.commit()
    db.refresh(variant)
    return variant


@router.post("/product/{product_id}")
def create_sku(
    product_id: int,
    data: ProductSKUCreate,
    db: Session = Depends(get_db),
    admin: UserModel = Depends(get_current_admin),
):
    """创建商品 SKU"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    sku = ProductSKU(
        product_id=product_id,
        sku_code=data.sku_code,
        attributes=data.attributes,
        price=data.price,
        stock=data.stock,
        image=data.image,
    )
    db.add(sku)
    db.commit()
    db.refresh(sku)
    return sku


@router.put("/{sku_id}")
def update_sku(
    sku_id: int,
    data: ProductSKUCreate,
    db: Session = Depends(get_db),
    admin: UserModel = Depends(get_current_admin),
):
    """更新 SKU"""
    sku = db.query(ProductSKU).filter(ProductSKU.id == sku_id).first()
    if not sku:
        raise HTTPException(status_code=404, detail="SKU不存在")
    sku.sku_code = data.sku_code
    sku.attributes = data.attributes
    sku.price = data.price
    sku.stock = data.stock
    sku.image = data.image
    db.commit()
    db.refresh(sku)
    return sku


@router.delete("/{sku_id}")
def delete_sku(
    sku_id: int,
    db: Session = Depends(get_db),
    admin: UserModel = Depends(get_current_admin),
):
    """下架 SKU"""
    sku = db.query(ProductSKU).filter(ProductSKU.id == sku_id).first()
    if not sku:
        raise HTTPException(status_code=404, detail="SKU不存在")
    sku.is_active = False
    db.commit()
    return {"message": "SKU已下架"}
