from typing import Dict, Any, List, Optional
from baseClass import Base, Product, Order
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import json

SEED_PRODUCTS = [
    {
        "id": 1,
        "name": "Nike Revolution 6",
        "category": "running shoes",
        "brand": "nike",
        "price": 2799,
        "color": "black",
        "features": ["cushioned", "breathable", "lightweight", "durable"],
        "rating": 4.5,
        "stock": 12
        # "image_url": "images/1.jpeg"
    },
    {
        "id": 2,
        "name": "Samsung Galaxy M14",
        "category": "smartphones",
        "brand": "samsung",
        "price": 12999,
        "color": "blue",
        "features": ["battery", "camera", "display", "5g"],
        "rating": 4.2,
        "stock": 4
        # "image_url": "images/2.jpeg"
    },
    {
        "id": 3,
        "name": "Adidas Ultraboost 22",
        "category": "running shoes",
        "brand": "adidas",
        "price": 3999,
        "color": "white",
        "features": ["cushioned", "responsive", "energy-return", "breathable"],
        "rating": 4.7,
        "stock": 8
        # "image_url": "images/3.jpeg"
    },
]


class SQLProductStore:
    def __init__(self, db_url: str = "sqlite:///shopgenie.db", seed_data: Optional[List[Dict[str, Any]]] = None):
        self.engine = create_engine(db_url, echo=False, future=True)
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)
        # create tables defined in Base
        Base.metadata.create_all(self.engine)
        # seed
        if seed_data:
            self._maybe_seed(seed_data)

    def _maybe_seed(self, seed_data: List[Dict[str, Any]]):
        try:
            with Session(self.engine) as ses:
                count = ses.query(Product).count()
                if count == 0:
                    for p in seed_data:
                        product_data = p.copy()
                        if 'features' in product_data and isinstance(product_data['features'], list):
                            product_data['features'] = json.dumps(product_data['features'])
                        
                        obj = Product(**product_data)
                        ses.add(obj)
                    ses.commit()
        except Exception:
            pass

    def list_products(self) -> List[Dict[str, Any]]:
        try:
            with Session(self.engine) as ses:
                products = ses.query(Product).all()
                return [self._model_to_dict(p) for p in products]
        except SQLAlchemyError:
            return []

    def get_product(self, pid: int) -> Optional[Dict[str, Any]]:
        try:
            with Session(self.engine) as ses:
                p = ses.get(Product, pid)
                return self._model_to_dict(p) if p else None
        except SQLAlchemyError:
            return None

    def place_order(self, user_id: str, pid: int, qty: int) -> Dict[str, Any]:
        """
        Place an order for user_id. Returns {"ok": True, "order": {...}} on success,
        or {"ok": False, "message": "..."} on failure.
        """
        try:
            with Session(self.engine) as ses:
                prod = ses.get(Product, pid)
                if not prod:
                    return {"ok": False, "message": "Product not found."}
                if getattr(prod, "stock", 0) < qty:
                    return {"ok": False, "message": f"Only {getattr(prod, 'stock', 0)} left."}

                if "user_id" not in Order.__table__.columns.keys():
                    return {"ok": False, "message": "Order model missing user_id column. Add user_id to Order model."}

                total = getattr(prod, "price", 0) * qty
                order = Order(user_id=user_id, product_id=pid, product=getattr(prod, "name", ""), quantity=qty, total_price=total)
                prod.stock = getattr(prod, "stock", 0) - qty

                ses.add(order)
                ses.add(prod)
                ses.commit()
                ses.refresh(order)
                return {"ok": True, "order": self._model_to_dict(order)}
        except SQLAlchemyError as e:
            return {"ok": False, "message": str(e)}

    def get_user_orders(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            with Session(self.engine) as ses:
                q = ses.query(Order).filter(getattr(Order, "user_id") == user_id).order_by(Order.id.desc()).limit(limit)
                return [self._model_to_dict(o) for o in q.all()]
        except SQLAlchemyError:
            return []

    def get_order(self, user_id: str, order_id: int) -> Dict[str, Any]:
        try:
            with Session(self.engine) as ses:
                order = ses.get(Order, order_id)
                if not order:
                    return {"ok": False, "message": "Order not found."}
                # ensure ownership
                if getattr(order, "user_id", None) != user_id:
                    return {"ok": False, "message": "Not your order."}
                return {"ok": True, "order": self._model_to_dict(order)}
        except SQLAlchemyError as e:
            return {"ok": False, "message": str(e)}

    def request_return(self, user_id: str, order_id: int, reason: Optional[str] = None) -> Dict[str, Any]:
        """
        Basic return flow placeholder. Adjust to match your Return model if present.
        Currently just checks ownership and increases stock.
        """
        try:
            with Session(self.engine) as ses:
                order = ses.get(Order, order_id)
                if not order:
                    return {"ok": False, "message": "Order not found."}
                if getattr(order, "user_id", None) != user_id:
                    return {"ok": False, "message": "Not your order."}

                prod = ses.get(Product, order.product_id)
                if prod:
                    prod.stock = getattr(prod, "stock", 0) + getattr(order, "quantity", 0)
                    ses.add(prod)

                if "status" in Order.__table__.columns.keys():
                    order.status = "returned"
                    ses.add(order)

                ses.commit()
                refund_amount = getattr(order, "total_price", 0)
                return {"ok": True, "return": {"order_id": order_id, "refund_amount": refund_amount}, "refund_amount": refund_amount}
        except SQLAlchemyError as e:
            return {"ok": False, "message": str(e)}

    def get_return_status(self, user_id: str, return_id: int) -> Dict[str, Any]:
        return {"ok": False, "message": "Return tracking not implemented."}

    def _model_to_dict(self, obj) -> Dict[str, Any]:
        if obj is None:
            return {}
        out = {}
        for col in obj.__table__.columns:
            val = getattr(obj, col.name)
            if isinstance(val, (list, dict)):
                out[col.name] = val
            else:
                out[col.name] = val
        if "features" in out and isinstance(out["features"], str):
            try:
                out["features"] = json.loads(out["features"])
            except Exception:
                pass
        return out


store = SQLProductStore(seed_data=SEED_PRODUCTS)






















# from typing import Dict, Any, List, Optional
# from baseClass import Base, Product, Order
# from sqlalchemy import create_engine
# from sqlalchemy.orm import Session, sessionmaker
# from sqlalchemy.exc import SQLAlchemyError
# import json

# SEED_PRODUCTS = [
#     {
#         "id": 1,
#         "name": "Nike Revolution 6",
#         "category": "running shoes",
#         "brand": "nike",
#         "price": 2799,
#         "color": "black",
#         "features": ["cushioned", "breathable", "lightweight", "durable"],
#         "rating": 4.5,
#         "stock": 12,
#         "image": "1.jpeg"
#     },
#     {
#         "id": 2,
#         "name": "Samsung Galaxy M14",
#         "category": "smartphones",
#         "brand": "samsung",
#         "price": 12999,
#         "color": "blue",
#         "features": ["battery", "camera", "display", "5g"],
#         "rating": 4.2,
#         "stock": 4,
#         "image": "2.jpeg"
#     },
#     {
#         "id": 3,
#         "name": "Adidas Ultraboost 22",
#         "category": "running shoes",
#         "brand": "adidas",
#         "price": 3999,
#         "color": "white",
#         "features": ["cushioned", "responsive", "energy-return", "breathable"],
#         "rating": 4.7,
#         "stock": 8,
#         "image": "3.jpeg"
#     },
#     {
#         "id": 4,
#         "name": "Apple AirPods Pro 2",
#         "category": "earphones",
#         "brand": "apple",
#         "price": 23999,
#         "color": "white",
#         "features": ["noise-cancelling", "transparency", "spatial audio"],
#         "rating": 4.8,
#         "stock": 15,
#         "image": "4.jpeg"
#     },
#     {
#         "id": 5,
#         "name": "Sony WH-1000XM4",
#         "category": "headphones",
#         "brand": "sony",
#         "price": 24990,
#         "color": "black",
#         "features": ["noise-cancelling", "wireless", "long battery"],
#         "rating": 4.7,
#         "stock": 6,
#         "image": "5.jpeg"
#     },
#     {
#         "id": 6,
#         "name": "Puma Velocity Nitro 2",
#         "category": "running shoes",
#         "brand": "puma",
#         "price": 3499,
#         "color": "red",
#         "features": ["lightweight", "stable", "breathable"],
#         "rating": 4.3,
#         "stock": 10,
#         "image": "6.jpeg"
#     },
#     {
#         "id": 7,
#         "name": "HP Pavilion 14",
#         "category": "laptops",
#         "brand": "hp",
#         "price": 52999,
#         "color": "silver",
#         "features": ["intel", "backlit keyboard", "thin", "portable"],
#         "rating": 4.4,
#         "stock": 5,
#         "image": "7.jpeg"
#     },
#     {
#         "id": 8,
#         "name": "Logitech MX Master 3S",
#         "category": "computer accessories",
#         "brand": "logitech",
#         "price": 9999,
#         "color": "graphite",
#         "features": ["ergonomic", "silent clicks", "bluetooth"],
#         "rating": 4.6,
#         "stock": 18,
#         "image": "8.jpeg"
#     },
#     {
#         "id": 9,
#         "name": "Asus ROG Strix G17",
#         "category": "laptops",
#         "brand": "asus",
#         "price": 89999,
#         "color": "black",
#         "features": ["gaming", "RGB", "165hz", "ryzen"],
#         "rating": 4.7,
#         "stock": 3,
#         "image": "9.jpeg"
#     },
#     {
#         "id": 10,
#         "name": "Boat Airdopes 141",
#         "category": "earphones",
#         "brand": "boat",
#         "price": 1299,
#         "color": "blue",
#         "features": ["deep bass", "bluetooth", "fast charging"],
#         "rating": 4.1,
#         "stock": 20,
#         "image": "10.jpeg"
#     },
#     {
#         "id": 11,
#         "name": "Samsung Galaxy Watch 5",
#         "category": "wearables",
#         "brand": "samsung",
#         "price": 24999,
#         "color": "graphite",
#         "features": ["amoled", "gps", "health tracking"],
#         "rating": 4.5,
#         "stock": 7,
#         "image": "11.jpeg"
#     },
#     {
#         "id": 12,
#         "name": "Lenovo Tab M10",
#         "category": "tablets",
#         "brand": "lenovo",
#         "price": 14999,
#         "color": "gray",
#         "features": ["full hd", "dolby audio", "kids mode"],
#         "rating": 4.2,
#         "stock": 11,
#         "image": "12.jpeg"
#     },
#     {
#         "id": 13,
#         "name": "Canon EOS 200D II",
#         "category": "cameras",
#         "brand": "canon",
#         "price": 61999,
#         "color": "black",
#         "features": ["dslr", "dual pixel af", "wifi"],
#         "rating": 4.8,
#         "stock": 4,
#         "image": "13.jpeg"
#     },
#     {
#         "id": 14,
#         "name": "Vivo T2 5G",
#         "category": "smartphones",
#         "brand": "vivo",
#         "price": 18999,
#         "color": "aqua",
#         "features": ["5g", "amoled", "fast charging"],
#         "rating": 4.4,
#         "stock": 9,
#         "image": "14.jpeg"
#     },
#     {
#         "id": 15,
#         "name": "Dell Inspiron 15",
#         "category": "laptops",
#         "brand": "dell",
#         "price": 45999,
#         "color": "black",
#         "features": ["ssd", "backlit keyboard", "lightweight"],
#         "rating": 4.3,
#         "stock": 8,
#         "image": "15.jpeg"
#     },
# ]



# class SQLProductStore:
#     def __init__(self, db_url: str = "sqlite:///shopgenie.db", seed_data: Optional[List[Dict[str, Any]]] = None):
#         self.engine = create_engine(db_url, echo=False, future=True)
#         self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)
#         # create tables defined in Base
#         Base.metadata.create_all(self.engine)
#         # seed
#         if seed_data:
#             self._maybe_seed(seed_data)

#     def _maybe_seed(self, seed_data: List[Dict[str, Any]]):
#         try:
#             with Session(self.engine) as ses:
#                 count = ses.query(Product).count()
#                 if count == 0:
#                     for p in seed_data:
#                         product_data = p.copy()
#                         if 'features' in product_data and isinstance(product_data['features'], list):
#                             product_data['features'] = json.dumps(product_data['features'])
                        
#                         obj = Product(**product_data)
#                         ses.add(obj)
#                     ses.commit()
#         except Exception as e:
#             print(f"Error seeding database: {e}")

#     def list_products(self) -> List[Dict[str, Any]]:
#         try:
#             with Session(self.engine) as ses:
#                 products = ses.query(Product).all()
#                 return [self._model_to_dict(p) for p in products]
#         except SQLAlchemyError:
#             return []

#     def get_product(self, pid: int) -> Optional[Dict[str, Any]]:
#         try:
#             with Session(self.engine) as ses:
#                 p = ses.get(Product, pid)
#                 return self._model_to_dict(p) if p else None
#         except SQLAlchemyError:
#             return None

#     def place_order(self, user_id: str, pid: int, qty: int) -> Dict[str, Any]:
#         """
#         Place an order for user_id. Returns {"ok": True, "order": {...}} on success,
#         or {"ok": False, "message": "..."} on failure.
#         """
#         try:
#             with Session(self.engine) as ses:
#                 prod = ses.get(Product, pid)
#                 if not prod:
#                     return {"ok": False, "message": "Product not found."}
#                 if getattr(prod, "stock", 0) < qty:
#                     return {"ok": False, "message": f"Only {getattr(prod, 'stock', 0)} left."}

#                 if "user_id" not in Order.__table__.columns.keys():
#                     return {"ok": False, "message": "Order model missing user_id column. Add user_id to Order model."}

#                 total = getattr(prod, "price", 0) * qty
#                 order = Order(user_id=user_id, product_id=pid, product=getattr(prod, "name", ""), quantity=qty, total_price=total)
#                 prod.stock = getattr(prod, "stock", 0) - qty

#                 ses.add(order)
#                 ses.add(prod)
#                 ses.commit()
#                 ses.refresh(order)
#                 return {"ok": True, "order": self._model_to_dict(order)}
#         except SQLAlchemyError as e:
#             return {"ok": False, "message": str(e)}

#     def get_user_orders(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
#         try:
#             with Session(self.engine) as ses:
#                 q = ses.query(Order).filter(getattr(Order, "user_id") == user_id).order_by(Order.id.desc()).limit(limit)
#                 return [self._model_to_dict(o) for o in q.all()]
#         except SQLAlchemyError:
#             return []

#     def get_order(self, user_id: str, order_id: int) -> Dict[str, Any]:
#         try:
#             with Session(self.engine) as ses:
#                 order = ses.get(Order, order_id)
#                 if not order:
#                     return {"ok": False, "message": "Order not found."}
#                 # ensure ownership
#                 if getattr(order, "user_id", None) != user_id:
#                     return {"ok": False, "message": "Not your order."}
#                 return {"ok": True, "order": self._model_to_dict(order)}
#         except SQLAlchemyError as e:
#             return {"ok": False, "message": str(e)}

#     def request_return(self, user_id: str, order_id: int, reason: Optional[str] = None) -> Dict[str, Any]:
#         """
#         Basic return flow placeholder. Adjust to match your Return model if present.
#         Currently just checks ownership and increases stock.
#         """
#         try:
#             with Session(self.engine) as ses:
#                 order = ses.get(Order, order_id)
#                 if not order:
#                     return {"ok": False, "message": "Order not found."}
#                 if getattr(order, "user_id", None) != user_id:
#                     return {"ok": False, "message": "Not your order."}

#                 prod = ses.get(Product, order.product_id)
#                 if prod:
#                     prod.stock = getattr(prod, "stock", 0) + getattr(order, "quantity", 0)
#                     ses.add(prod)

#                 if "status" in Order.__table__.columns.keys():
#                     order.status = "returned"
#                     ses.add(order)

#                 ses.commit()
#                 refund_amount = getattr(order, "total_price", 0)
#                 return {"ok": True, "return": {"order_id": order_id, "refund_amount": refund_amount}, "refund_amount": refund_amount}
#         except SQLAlchemyError as e:
#             return {"ok": False, "message": str(e)}

#     def get_return_status(self, user_id: str, return_id: int) -> Dict[str, Any]:
#         return {"ok": False, "message": "Return tracking not implemented."}

#     def _model_to_dict(self, obj) -> Dict[str, Any]:
#         if obj is None:
#             return {}
#         out = {}
#         for col in obj.__table__.columns:
#             val = getattr(obj, col.name)
#             if isinstance(val, (list, dict)):
#                 out[col.name] = val
#             else:
#                 out[col.name] = val
#         if "features" in out and isinstance(out["features"], str):
#             try:
#                 out["features"] = json.loads(out["features"])
#             except Exception:
#                 pass
#         return out


# store = SQLProductStore(seed_data=SEED_PRODUCTS)