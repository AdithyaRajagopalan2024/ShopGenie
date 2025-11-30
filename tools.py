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
from rapidfuzz import fuzz
# from fuzzywuzzy import process

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

        # Fuzzy search for name
        if name:
            name_lower = name.lower()
            filtered_products = []
            for p in products:
                product_name = p.get("name", "").lower()
                # Use fuzzy matching with threshold of 60
                similarity = fuzz.partial_ratio(name_lower, product_name)
                if similarity >= 60:
                    p["_name_similarity"] = similarity
                    filtered_products.append(p)
            products = filtered_products
        
        # Fuzzy search for category
        if category:
            category_lower = category.lower()
            filtered_products = []
            for p in products:
                product_category = p.get("category", "").lower()
                similarity = fuzz.ratio(category_lower, product_category)
                if similarity >= 70:
                    p["_category_similarity"] = similarity
                    filtered_products.append(p)
            products = filtered_products
        
        # Exact filters for price, brand, color
        if max_price:
            products = [p for p in products if p["price"] <= max_price]
        
        # Fuzzy search for brand
        if brand:
            brand_lower = brand.lower()
            filtered_products = []
            for p in products:
                product_brand = p.get("brand", "").lower()
                similarity = fuzz.ratio(brand_lower, product_brand)
                if similarity >= 70:
                    p["_brand_similarity"] = similarity
                    filtered_products.append(p)
            products = filtered_products
        
        # Fuzzy search for color
        if color:
            color_lower = color.lower()
            filtered_products = []
            for p in products:
                product_color = p.get("color", "").lower()
                similarity = fuzz.ratio(color_lower, product_color)
                if similarity >= 70:
                    p["_color_similarity"] = similarity
                    filtered_products.append(p)
            products = filtered_products
        
        # Features matching (keep as is, since features are tags)
        if features:
            products = [p for p in products if any(f in p["features"] for f in features)]

        # Scoring system
        for p in products:
            score = p["rating"] * 20
            
            # Add fuzzy match bonuses
            score += p.get("_name_similarity", 0) * 0.5
            score += p.get("_category_similarity", 0) * 0.3
            score += p.get("_brand_similarity", 0) * 0.2
            score += p.get("_color_similarity", 0) * 0.1
            
            score += sum(10 for f in features if f in p["features"])
            if p["stock"] == 0:
                score -= 50
            elif p["stock"] < 3:
                score -= 20
            p["_score"] = score

        products.sort(key=lambda x: x["_score"], reverse=True)
        
        # Format prices with Rs. prefix
        for p in products:
            p["price_formatted"] = f"Rs. {p['price']}"

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

        # Fuzzy matching for common categories
        categories_map = {
            "running shoes": ["shoe", "shoes", "sneaker", "sneakers", "footwear"],
            "smartphones": ["phone", "smartphone", "mobile", "cell"],
            "laptops": ["laptop", "notebook", "computer"],
            "earphones": ["earphone", "earbud", "earbuds", "headset"],
            "headphones": ["headphone", "headphones"],
            "tablets": ["tablet", "ipad"],
            "cameras": ["camera", "dslr"],
            "wearables": ["watch", "smartwatch", "wearable"]
        }
        
        for category, keywords in categories_map.items():
            for keyword in keywords:
                if keyword in q:
                    intent["category"] = category
                    break
            if intent["category"]:
                break

        m = re.search(r"under (\d+)", q)
        if m:
            intent["max_price"] = int(m.group(1))

        # Fuzzy color matching
        colors = ["black", "white", "blue", "red", "silver", "graphite", "gray", "aqua"]
        for c in colors:
            if c in q:
                intent["color"] = c
                break

        # Fuzzy brand matching
        brands = ["nike", "adidas", "samsung", "apple", "sony", "puma", "hp", "logitech", 
                  "asus", "boat", "lenovo", "canon", "vivo", "dell"]
        for b in brands:
            if b in q:
                intent["brand"] = b
                break

        # Feature extraction
        features_keywords = ["cushioned", "lightweight", "battery", "camera", "noise-cancelling",
                            "wireless", "gaming", "5g", "amoled", "fast charging"]
        for f in features_keywords:
            if f in q or f.replace("-", " ") in q:
                intent["features"].append(f)

        return {"status": "success", "data": {"intent": intent}}

    except Exception as e:
        return {"status": "error", "error_message": str(e)}

def get_product_id_by_name(product_name: str) -> Dict[str, Any]:
    """Get product ID by searching for product name using fuzzy matching."""
    try:
        products = store.list_products()
        
        if not products:
            return {"status": "error", "error_message": "No products found in catalog."}
        
        # Use fuzzy matching to find the best match
        name_lower = product_name.lower()
        best_match = None
        best_score = 0
        
        for p in products:
            product_name_lower = p.get("name", "").lower()
            similarity = fuzz.partial_ratio(name_lower, product_name_lower)
            
            if similarity > best_score:
                best_score = similarity
                best_match = p
        
        # Require at least 60% similarity
        if best_match and best_score >= 60:
            return {
                "status": "success",
                "data": {
                    "product_id": best_match["id"],
                    "product_name": best_match["name"],
                    "price": best_match["price"],
                    "price_formatted": f"Rs. {best_match['price']}",
                    "stock": best_match["stock"],
                    "similarity_score": best_score
                }
            }
        
        return {"status": "error", "error_message": f"No product found matching '{product_name}'."}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}


# def place_order(self, user_id: str, pid: int, qty: int) -> Dict[str, Any]:
#     """
#     Place an order for user_id. Returns {"ok": True, "order": {...}} on success,
#     or {"ok": False, "message": "..."} on failure.
#     """
#     try:
#         with Session(self.engine) as ses:
#             prod = ses.get(Product, pid)
#             if not prod:
#                 return {"ok": False, "message": "Product not found."}
#             if getattr(prod, "stock", 0) < qty:
#                 return {"ok": False, "message": f"Only {getattr(prod, 'stock', 0)} left."}

#             if "user_id" not in Order.__table__.columns.keys():
#                 return {"ok": False, "message": "Order model missing user_id column. Add user_id to Order model."}

#             order = Order(user_id=user_id, product_id=pid, quantity=qty, total_price=prod.price * qty)
#             prod.stock = getattr(prod, "stock", 0) - qty

#             ses.add(order)
#             ses.add(prod)
#             ses.commit()
#             ses.refresh(order)
            
#             # Format order with Rs. prefix
#             order_dict = self._model_to_dict(order)
#             order_dict["total_price_formatted"] = f"Rs. {order_dict['total_price']}"
            
#             return {"ok": True, "order": order_dict}
#     except SQLAlchemyError as e:
#         return {"ok": False, "message": str(e)}
def place_order_with_user(product_name: str, quantity: int = 1) -> Dict[str, Any]:
    """Place an order for a product by name."""
    user_id = "admin"  # Hardcoded user_id from session
    
    try:
        # First, get the product ID by name
        product_result = get_product_id_by_name(product_name)
        
        if product_result["status"] == "error":
            return product_result
        
        product_id = product_result["data"]["product_id"]
        product_info = product_result["data"]
        
        # Check if sufficient stock
        if product_info["stock"] < quantity:
            return {
                "status": "error", 
                "error_message": f"Insufficient stock. Only {product_info['stock']} units available for {product_info['product_name']}."
            }
        
        # Place the order
        result = store.place_order(user_id, product_id, quantity)
        if result["ok"]:
            order = result["order"]
            order["total_price_formatted"] = f"Rs. {order.get('total_price', 0)}"
            order["product_name"] = product_info["product_name"]
            return {"status": "success", "data": {"order": order}}
        return {"status": "error", "error_message": result["message"]}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}

def return_order(order_id: int, reason: str = None) -> Dict[str, Any]:
    """Request a return for an order."""
    user_id = "admin"  # Hardcoded user_id
    try:
        result = store.request_return(user_id, order_id, reason)
        if result["ok"]:
            refund_amount = result["refund_amount"]
            return {
                "status": "success", 
                "data": {
                    "return": result["return"],
                    "refund_amount": refund_amount,
                    "refund_amount_formatted": f"Rs. {refund_amount}"
                }
            }
        return {"status": "error", "error_message": result["message"]}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}

def check_order_status(order_id: int) -> Dict[str, Any]:
    """Check the status of a specific order."""
    user_id = "admin"  # Hardcoded user_id
    try:
        result = store.get_order(user_id, order_id)
        if result["ok"]:
            order = result["order"]
            order["total_price_formatted"] = f"Rs. {order.get('total_price', 0)}"
            return {"status": "success", "data": {"order": order}}
        return {"status": "error", "error_message": result["message"]}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}

def get_my_orders(limit: int = 5) -> Dict[str, Any]:
    """Get recent orders for the current user."""
    user_id = "admin"  # Hardcoded user_id
    try:
        orders = store.get_user_orders(user_id, limit)
        for order in orders:
            order["total_price_formatted"] = f"Rs. {order.get('total_price', 0)}"
        return {"status": "success", "data": {"orders": orders, "count": len(orders)}}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}

def check_return_status(return_id: int) -> Dict[str, Any]:
    """Check the status of a return request."""
    user_id = "admin"  # Hardcoded user_id
    try:
        result = store.get_return_status(user_id, return_id)
        if result["ok"]:
            return_data = result["return"]
            if "refund_amount" in return_data:
                return_data["refund_amount_formatted"] = f"Rs. {return_data['refund_amount']}"
            return {"status": "success", "data": {"return": return_data}}
        return {"status": "error", "error_message": result["message"]}
    except Exception as e:
        return {"status": "error", "error_message": str(e)}

# from google.adk.tools import BaseTool
# from google.adk.tools.tool_context import ToolContext

# class UserContextTool(BaseTool):
#     """Base tool that automatically injects user_id from session context"""
    
#     def __init__(self, func, name=None, description=None):
#         self._func = func
#         self._name = name or func.__name__
#         self._description = description or func.__doc__
#         super().__init__(name=self._name, description=self._description)
    
#     async def run(self, context: ToolContext, **kwargs):
#         # Inject user_id from session
#         user_id = context.session.user_id if context.session else "anonymous"
#         return self._func(user_id=user_id, **kwargs)

# # Create wrapped tools
# place_order_tool = UserContextTool(place_order_with_user, "place_order", 
#     "Place an order for a product. Args: product_id (int), quantity (int)")

# return_order_tool = UserContextTool(return_order, "return_order",
#     "Request a return for an order. Args: order_id (int), reason (str, optional)")

# check_order_tool = UserContextTool(check_order_status, "check_order_status",
#     "Check status of an order. Args: order_id (int)")

# get_orders_tool = UserContextTool(get_my_orders, "get_my_orders",
#     "Get your recent orders. Args: limit (int, optional, default 5)")

# check_return_tool = UserContextTool(check_return_status, "check_return_status",
#     "Check status of a return request. Args: return_id (int)")