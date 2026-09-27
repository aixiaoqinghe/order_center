from decimal import Decimal

from sqlalchemy.orm import Session
from app.models.inventory import Inventory
from app.models.product import Product
from app.schemas.product import ProductCreate
from app.utils.exceptions import ProductNotFoundError

def product_detail(db: Session, product_id: int) -> dict:
    """商品详情:跨 product + inventory 拼接; inventory 无记录则 available_stock=0"""
    product = db.query(Product).filter(Product.product_id == product_id).first()
    if product is None:
        raise ProductNotFoundError(f"商品不存在:{product_id}")
    inventory = db.query(Inventory).filter(Inventory.product_id == product_id).first()
    if inventory is None:
        available_stock = 0
    else:
        available_stock = inventory.total_stock - inventory.locked_stock

    # 手动拼装成 dict (因为 available_stock 不是 ORM 属性)
    return {
        "product_id": product.product_id,
        "product_name": product.product_name,
        "product_createtime": product.product_createtime,
        "product_type": product.product_type,
        "product_amount": product.product_amount,
        "available_stock": available_stock,
    }


def create_product(db: Session, data: ProductCreate) -> dict:
    """创建商品: product + inventory 两张表，一个事务"""
    try:
        # 1.插 product
        product = Product(
            product_name=data.product_name,
            product_type=data.product_type,
            product_amount=data.product_amount,
        )
        db.add(product)
        db.flush()    # 拿到 product_id, 不 commit

        # 2.插 inventory, 用同一个 product_id
        inventory = Inventory(
            product_id=product.product_id,
            total_stock=data.total_stock,
            locked_stock=0,
        )
        db.add(inventory)
        db.commit()
        db.refresh(product)

    except Exception:
        db.rollback()
        raise

    return {
        "product_id": product.product_id,
        "product_name": product.product_name,
        "product_amount": product.product_amount,
        "total_stock": data.total_stock,
    }

def product_page_list(db: Session, page: int, size: int) -> dict:
    """分页列表： count + offset/limit 查询"""
    total = db.query(Product).count()
    offset = (page - 1) * size
    products = (
        db.query(Product)
        .order_by(Product.product_id)
        .offset(offset)
        .limit(size)
        .all()
    )
    return {"list": products, "total": total, "page": page, "size": size}