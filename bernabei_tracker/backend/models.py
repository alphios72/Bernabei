from typing import Optional, List
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship

class ProductBase(SQLModel):
    bernabei_code: str = Field(index=True, unique=True) # Unique ID from site
    name: str = Field(index=True)
    product_link: str
    image_url: Optional[str] = None
    category: Optional[str] = None
    current_price: Optional[float] = None
    last_checked_at: Optional[datetime] = None

class Product(ProductBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    price_history: List["PriceHistory"] = Relationship(back_populates="product")

class ProductRead(ProductBase):
    id: int
    is_price_ok: bool = False
    is_lowest_all_time: bool = False
    discount_percentage: float = 0.0

class PriceHistory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="product.id")
    price: float
    ordinary_price: Optional[float] = None
    lowest_price_30_days: Optional[float] = None
    tags: Optional[str] = None # JSON string or comma-separated
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    product: Product = Relationship(back_populates="price_history")
