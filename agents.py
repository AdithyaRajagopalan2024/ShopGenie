from google.adk.agents import LlmAgent
from google.adk.tools import load_memory, AgentTool
from google.adk.models.google_llm import Gemini
from google.adk.apps.app import App
from google.adk.plugins import LoggingPlugin
from google.genai import types
from dotenv import load_dotenv
import os
from tools import retrieve_products, parse_intent, return_order, check_order_status, get_my_orders, check_return_status, place_order_with_user, flag_return_for_review, get_user_return_history

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

Your goal is to help users find products.
1.  Use the `retrieve_products` tool to search the catalog.
2.  Unless the user asks for a specific number, **always show at least 15 products** if available.
3.  Present the results clearly to the user.
4.  If no products are found, say so.
5.  **IMPORTANT: Always display prices with "Rs." prefix. Use the price_formatted field from the tool output.**
6.  Include product names, formatted prices (Rs. X), and stock availability in your summary.
7.  **Crucially, you must report the stock status exactly as provided by the tool. Do not add any extra information or make assumptions about availability.**
8.  **When you list products, format each product name as a Markdown link like this: `Product Name`.**
8.  If the user asks why a product is a good pick or asks about its features, summarize the features from the tool output in a helpful way.
9.  The search now uses fuzzy matching, so products will be found even if the search terms don't match exactly.
""",
    tools=[retrieve_products]
)





service_agent = LlmAgent(
    model=Gemini(model=MODEL_NAME, retry_options=retry_config),
    name="service_agent",
    instruction="""You handle orders and customer service.
Your tasks include placing orders, checking order status, and handling returns with an intelligent validation process.

**Advanced Return Validation Workflow:**
When a user requests a return, follow these steps to validate it:

1.  **Find the Order**: If the user doesn't provide an order ID, use `get_my_orders` to help them find it. Once you have the `order_id`, use `check_order_status` to get the order details, especially the `created_at` date.

2.  **Check Return Window**: The return policy is **14 days**. Compare the order's `created_at` date with the current date. If it's outside the 14-day window, politely inform the user that the item is no longer returnable and **stop the process**.

3.  **Assess User's Return History**: Use the `get_user_return_history` tool. If the user has made **3 or more returns** in the past, this is a potential red flag.

4.  **Analyze the Reason**: Ask the user for the reason for the return. Analyze their response semantically.
    *   **Legitimate Reasons**: Issues like "item is damaged", "defective product", "wrong size received", or "doesn't fit" are usually legitimate.
    *   **Suspicious Reasons**: Reasons like "changed my mind", "don't want it anymore", "found it cheaper elsewhere", or very brief/vague answers are more suspicious.

5.  **Make a Decision**:
    *   **Automatic Return (`return_order`)**: If the return is within the 14-day window, the user has fewer than 3 past returns, AND the reason is legitimate, process the return automatically.
    *   **Flag for Review (`flag_return_for_review`)**: If the return is outside the 14-day window, OR the user has 3 or more past returns, OR the reason seems suspicious, you **MUST** flag the return for manual review. Do not process it automatically.

6.  **Communicate Clearly**: Inform the user of the outcome. If approved, confirm the refund details. If flagged, explain that it needs a quick review from a support agent.

**Tool Usage:**
- To place an order: `place_order_with_user(product_name, quantity)`
- To check order status: `check_order_status(order_id)`
- To get order history: `get_my_orders(limit)`
- For a valid return: `return_order(order_id, reason)`
- For a suspicious return: `flag_return_for_review(order_id, reason)`
- To check return status: `check_return_status(return_id)`
- To check user's return history: `get_user_return_history()`
**General Rules:**
- Always confirm order details after placing.
- **ALWAYS display prices with "Rs." prefix.** Use formatted price fields like `total_price_formatted` and `refund_amount_formatted` from tool outputs.
- For standard returns, explain the refund process and show the refund amount with "Rs." prefix.
- Be helpful and clear in all your communications.
""",
    tools=[
        place_order_with_user,
        return_order,
        check_order_status,
        get_my_orders,
        check_return_status,
        flag_return_for_review
    ]
)

# Available actions:
# - Place orders: Call place_order(id, quantity)
# - View order history: Call get_my_orders(limit=5)
# - Check order status: Call check_order_status(order_id)
# - Request returns: Call return_order(order_id, reason="optional reason")
# - Check return status: call check_return_status(return_id)






orchestrator = LlmAgent(
    model=Gemini(model=MODEL_NAME, retry_options=retry_config),
    name="orchestrator",
    instruction="""You are the ShopGenie orchestrator.
Your primary role is to understand the user's intent and delegate tasks to the appropriate specialist agent.
Follow this workflow strictly:
1.  **Parse Intent**: Always start by calling `parse_intent()` to understand the user's goal (e.g., searching for products, placing an order, checking status).
2.  **Load Preferences**: Call `load_memory()` to retrieve any saved user preferences that might be relevant.
3.  Use product_agent and service_agent based on the user's intent:
    *   **product_agent**: If the user wants to find, search for, or see products, use the subagent `product_agent`.
    *   **service_agent**: If the user wants to place an order, check an order's status, get their order history, or process a return, delegate the task to subagent `service_agent`. If the user says "order [product name]", first use subagent `product_agent` to search for that product. Then, confirm with the user and use subagent `service_agent` to place the order using the product ID from the search results. Do not assume a product ID.
4.  User Context: The SubAgent `service_agent` automatically handles user identification from the session. You do not need to manage user IDs.
5.  **Price Formatting**: Ensure all prices are displayed with "Rs." prefix in your responses.
6.  Respond to User: Formulate a helpful, conversational response based on the results from the specialist agents. If an agent fails, do not just repeat the error. Try to understand the problem and find another way to help.
    
**SubAgent Capabilities:**
- `product_agent`: Searches the product catalog using fuzzy matching (finds products even with approximate search terms).
- `service_agent`: Manages orders, returns, and status checks for the current user.
- `parse_intent`: Extracts details like category, brand, and price from the user's query using fuzzy matching.
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