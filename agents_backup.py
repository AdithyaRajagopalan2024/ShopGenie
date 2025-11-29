from google.adk.agents import LlmAgent
from google.adk.tools import load_memory, AgentTool
from google.adk.models.google_llm import Gemini
from google.adk.apps.app import App
from google.adk.plugins import LoggingPlugin
from google.genai import types
from dotenv import load_dotenv
import os
from tools import retrieve_products, parse_intent, place_order_tool, return_order_tool, check_order_tool, get_orders_tool, check_return_tool

load_dotenv()
APP_NAME = os.getenv("APP_NAME")
MODEL_NAME = os.getenv("MODEL_NAME")
retry_config = types.HttpRetryOptions(
    attempts=5,
    exp_base=7,
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504]
)



product_agent = LlmAgent(
    model=Gemini(model=MODEL_NAME, retry_options=retry_config),
    name="product_agent",
    instruction="""You are a product search specialist.

When given a user query:
1. Call retrieve_products() with the appropriate parameters
2. Format the results in a clear, user-friendly way
3. Always provide a text response describing the products found

Return a helpful summary of the products, including:
- Product names
- Prices
- Key features
- Stock availability
""",
    tools=[retrieve_products]
)





service_agent = LlmAgent(
    model=Gemini(model=MODEL_NAME, retry_options=retry_config),
    name="service_agent",
    instruction="""You handle orders and customer service with full database integration.

Available actions:
- Place orders: Call place_order(product_id, quantity)
- View order history: Call get_my_orders(limit=5)
- Check order status: Call check_order_status(order_id)
- Request returns: Call return_order(order_id, reason="optional reason")
- Check return status: call check_return_status(return_id)

Important:
- Orders are linked to the current user's session
- Always confirm order details after placing
- For returns, explain the refund process
- Show order history when relevant
- Be helpful and clear about order statuses
""",
    tools=[
        place_order_tool,
        return_order_tool,
        check_order_tool,
        get_orders_tool,
        check_return_tool
    ]
)






orchestrator = LlmAgent(
    model=Gemini(model=MODEL_NAME, retry_options=retry_config),
    name="orchestrator",
    instruction="""You are the ShopGenie orchestrator.
Your primary role is to understand the user's intent and delegate tasks to the appropriate specialist agent.
Follow this workflow strictly:
1.  **Parse Intent**: Always start by calling `parse_intent()` to understand the user's goal (e.g., searching for products, placing an order, checking status).
2.  **Load Preferences**: Call `load_memory()` to retrieve any saved user preferences that might be relevant.
3.  **Delegate to Specialists**:
    *   **Product Search**: If the user wants to find, search for, or see products, delegate the task to `product_agent`.
    *   **Order & Service**: If the user wants to place an order, check an order's status, get their order history, or process a return, delegate the task to `service_agent`.
    *   **Ordering a specific product by name**: If the user says "order [product name]", first use `product_agent` to search for that product. Then, confirm with the user and use `service_agent` to place the order using the product ID from the search results. Do not assume a product ID.
4.  **User Context**: The `service_agent` automatically handles user identification from the session. You do not need to manage user IDs.
5.  **Respond to User**: Formulate a helpful, conversational response based on the results from the specialist agents. If an agent fails, do not just repeat the error. Try to understand the problem and find another way to help.
    
**Agent Capabilities:**
- `product_agent`: Searches the product catalog.
- `service_agent`: Manages orders, returns, and status checks for the current user.
- `parse_intent`: Extracts details like category, brand, and price from the user's query.
- `load_memory`: Retrieves the user's saved preferences.
""",
    tools=[
        parse_intent,
        AgentTool(agent=product_agent),
        AgentTool(agent=service_agent),
        load_memory
    ]
)

shopApp = App(
    name="agents",
    root_agent=orchestrator,
    plugins=[LoggingPlugin()]
)