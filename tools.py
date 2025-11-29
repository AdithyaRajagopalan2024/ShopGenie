import asyncio
from typing import Dict, Any, List, Optional
from productstore import store
import re
from google.adk.tools import BaseTool
from google.adk.tools.tool_context import ToolContext
import os
import base64
from productstore import Session, Product, Order
from sqlalchemy.exc import SQLAlchemyError

def retrieve_products(
    name: str = None,
    category: str = None,
    max_price: int = None,
    brand: str = None,
    color: str = None,
    features: list = None
) -> Dict[str, Any]:
    try:
        if features is None:
            features = []

        products = store.list_products()

        if name:
            products = [p for p in products if p.get("name") and name.lower() in p.get("name").lower()]
        if category:
            products = [p for p in products if p.get("category") and p.get("category").lower() == category.lower()]
        if max_price:
            products = [p for p in products if p["price"] <= max_price]
        if brand:
            products = [p for p in products if p.get("brand") and p.get("brand").lower() == brand.lower()]
        if color:
            products = [p for p in products if p.get("color") and color.lower() in p.get("color").lower()]
        if features:
            products = [p for p in products if any(f in p["features"] for f in features)]

        # scoring
        for p in products:
            score = p["rating"] * 20
            score += sum(10 for f in features if f in p["features"])
            if p["stock"] == 0:
                score -= 50
            elif p["stock"] < 3:
                score -= 20
            p["_score"] = score

        products.sort(key=lambda x: x["_score"], reverse=True)

        return {
            "status": "success",
            "data": {
                "products": products,
                "total_found": len(products)
            }
        }

    except Exception as e:
        return {"status": "error", "error_message": str(e)}

def parse_intent(query: str) -> Dict[str, Any]:
    try:
        q = query.lower()
        intent = {"category": None, "max_price": None, "brand": None,
                  "color": None, "features": []}

        if "shoe" in q:
            intent["category"] = "running shoes"
        if "phone" in q:
            intent["category"] = "smartphones"

        m = re.search(r"under (\d+)", q)
        if m:
            intent["max_price"] = int(m.group(1))

        for c in ["black", "white", "blue", "red"]:
            if c in q:
                intent["color"] = c

        for b in ["nike", "adidas", "samsung"]:
            if b in q:
                intent["brand"] = b

        for f in ["cushioned", "lightweight", "battery", "camera"]:
            if f in q:
                intent["features"].append(f)

        return {"status": "success", "data": {"intent": intent}}

    except Exception as e:
        return {"status": "error", "error_message": str(e)}

# def place_order(product_id: int, quantity: int) -> Dict[str, Any]:
#     """Place an order for a product. Requires user context from session."""
#     try:
#         # This will be called with tool_context which has user_id
#         # For now, we'll need to pass user_id through the agent
#         return {"status": "error", "error_message": "User ID required. Please use place_order_with_user instead."}
#     except Exception as e:
#         return {"status": "error", "error_message": str(e)}

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

            order = Order(user_id=user_id, product_id=pid, quantity=qty, total_price=prod.price * qty)
            prod.stock = getattr(prod, "stock", 0) - qty

            ses.add(order)
            ses.add(prod)
            ses.commit()
            ses.refresh(order)
            return {"ok": True, "order": self._model_to_dict(order)}
    except SQLAlchemyError as e:
        return {"ok": False, "message": str(e)}


def place_order_with_user(user_id: str, product_id: int, quantity: int) -> Dict[str, Any]:
    """Place an order for a specific user."""
    try:
        result = store.place_order(user_id, product_id, quantity)
        if result["ok"]:
            return {"status": "success", "data": {"order": result["order"]}}
        return {"status": "error", "error_message": result["message"]}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}

def return_order(user_id: str, order_id: int, reason: str = None) -> Dict[str, Any]:
    """Request a return for an order."""
    try:
        result = store.request_return(user_id, order_id, reason)
        if result["ok"]:
            return {
                "status": "success", 
                "data": {
                    "return": result["return"],
                    "refund_amount": result["refund_amount"]
                }
            }
        return {"status": "error", "error_message": result["message"]}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}

def check_order_status(user_id: str, order_id: int) -> Dict[str, Any]:
    """Check the status of a specific order."""
    try:
        result = store.get_order(user_id, order_id)
        if result["ok"]:
            return {"status": "success", "data": {"order": result["order"]}}
        return {"status": "error", "error_message": result["message"]}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}

def get_my_orders(user_id: str, limit: int = 5) -> Dict[str, Any]:
    """Get recent orders for the current user."""
    try:
        orders = store.get_user_orders(user_id, limit)
        return {"status": "success", "data": {"orders": orders, "count": len(orders)}}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}

def check_return_status(user_id: str, return_id: int) -> Dict[str, Any]:
    """Check the status of a return request."""
    try:
        result = store.get_return_status(user_id, return_id)
        if result["ok"]:
            return {"status": "success", "data": {"return": result["return"]}}
        return {"status": "error", "error_message": result["message"]}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}
    





from google.adk.tools import BaseTool
from google.adk.tools.tool_context import ToolContext

class UserContextTool(BaseTool):
    """Base tool that automatically injects user_id from session context"""
    
    def __init__(self, func, name=None, description=None):
        self._func = func
        self._name = name or func.__name__
        self._description = description or func.__doc__
        super().__init__(name=self._name, description=self._description)
    
    async def run(self, context: ToolContext, **kwargs):
        # Inject user_id from session
        user_id = context.session.user_id if context.session else "anonymous"
        return self._func(user_id=user_id, **kwargs)

# Create wrapped tools
place_order_tool = UserContextTool(place_order_with_user, "place_order", 
    "Place an order for a product. Args: product_id (int), quantity (int)")

return_order_tool = UserContextTool(return_order, "return_order",
    "Request a return for an order. Args: order_id (int), reason (str, optional)")

check_order_tool = UserContextTool(check_order_status, "check_order_status",
    "Check status of an order. Args: order_id (int)")

get_orders_tool = UserContextTool(get_my_orders, "get_my_orders",
    "Get your recent orders. Args: limit (int, optional, default 5)")

check_return_tool = UserContextTool(check_return_status, "check_return_status",
    "Check status of a return request. Args: return_id (int)")