from sqlalchemy.orm import declarative_base, Mapped, mapped_column
from sqlalchemy import Integer, String, Float
from typing import Dict, Optional
import json

Base = declarative_base()


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)

    category: Mapped[Optional[str]] = mapped_column(String)
    brand: Mapped[Optional[str]] = mapped_column(String)

    price: Mapped[float] = mapped_column(Float)
    color: Mapped[Optional[str]] = mapped_column(String)

    features: Mapped[str] = mapped_column(String)  # Stored as JSON string
    rating: Mapped[float] = mapped_column(Float, default=0.0)

    stock: Mapped[int] = mapped_column(Integer, default=0)

    image: Mapped[Optional[str]] = mapped_column(String)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "brand": self.brand,
            "price": self.price,
            "color": self.color,
            "features": json.loads(self.features),
            "rating": self.rating,
            "stock": self.stock,
            "image": self.image,
        }

import enum
from datetime import datetime
from sqlalchemy import ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.orm import relationship

# Add these enums
class OrderStatus(enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RETURNED = "returned"

class ReturnStatus(enum.Enum):
    REQUESTED = "requested"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"

# Add new User table
class User(Base):
    __tablename__ = "users"
    
    user_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    orders = relationship("Order", back_populates="user")

# Modify existing Order class
class Order(Base):
    __tablename__ = "orders"
    
    order_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(100), ForeignKey("users.user_id"), nullable=False)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer)
    total_price: Mapped[float] = mapped_column(Float)
    status: Mapped[OrderStatus] = mapped_column(SQLEnum(OrderStatus), default=OrderStatus.PENDING)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="orders")
    product = relationship("Product")
    returns = relationship("OrderReturn", back_populates="order")

    def to_dict(self):
        return {
            "order_id": self.order_id,
            "user_id": self.user_id,
            "product_id": self.product_id,
            "product_name": self.product.name if self.product else None,
            "quantity": self.quantity,
            "total_price": self.total_price,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

# Add new OrderReturn table
class OrderReturn(Base):
    __tablename__ = "order_returns"
    
    return_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.order_id"), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(String(500))
    status: Mapped[ReturnStatus] = mapped_column(SQLEnum(ReturnStatus), default=ReturnStatus.REQUESTED)
    refund_amount: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    order = relationship("Order", back_populates="returns")

    def to_dict(self):
        return {
            "return_id": self.return_id,
            "order_id": self.order_id,
            "reason": self.reason,
            "status": self.status.value,
            "refund_amount": self.refund_amount,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }

class SuspiciousReturn(Base):
    __tablename__ = "suspicious_returns"

    review_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[str] = mapped_column(String(100), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(String(500))
    review_notes: Mapped[str] = mapped_column(String(500), default="Awaiting review")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)