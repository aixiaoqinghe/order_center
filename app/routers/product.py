from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from fastapi import Query

from app.database import get_db
from app.schemas.common import Response
from app.schemas.product import (
    ProductCreate,
    ProductCreateOut,
    ProductDetailOut,
    ProductListData,
)
from app.services import product_service

router = APIRouter(prefix="/api/product", tags=["product"])

@router.get("/list", response_model=Response[ProductListData])
def list_products(
    page: int = Query(1, ge=1, le=100, description="页码"),
    size: int = Query(30, ge=10, le=50, description="每页数量"),
    db: Session = Depends(get_db),
):
    """商品列表（分页）"""
    data = product_service.product_page_list(db, page, size)
    return Response(msg="success found", data=data)

@router.get("/{product_id}", response_model=Response[ProductDetailOut])
def get_product(product_id: int, db: Session = Depends(get_db)):
    """商品详情"""
    data = product_service.product_detail(db, product_id)
    return Response(msg="success found", data=data)

@router.post("/create", response_model=Response[ProductCreateOut])
def create_product(data: ProductCreate, db: Session = Depends(get_db)):
    """创建商品"""
    result = product_service.create_product(db, data)
    return Response(msg="success created", data=result)
