# ShopGenie 
### Capstone Submission for Kaggle Agents Intensive

## Project Overview
**ShopGenie** is an AI-driven shopping assistant built for the **Kaggle Agents Intensive – Capstone Project**. It demonstrates how agent-based reasoning can power a realistic e-commerce assistant that can search and filter a product catalog, maintain conversational state, simulate cart behavior, and persist session data using a lightweight database backend.

## Motivation
The Kaggle Agents Intensive encourages building **an agent that solves a real-world problem**. Retail is a natural fit: product search and filtering require reasoning, sessions require memory, and the entire system can scale to recommendations and vector search.  
**Goal:** Build a cohesive, modular, production-style prototype using cooperating agents to manage product lookup and user session flows.

## Key Features
- Agent-based interaction for interpreting user actions  
- Orchestrator logic combining search, filters, and session state  
- SQLite-backed product catalog  
- Persistent user sessions via `shopgenie_sessions.db`  
- Modular codebase designed for extension  
- Logging utilities for debugging agent behaviour  

## Architecture
See `arch_diag.png` for the full diagram.  
**Components:**
1. **Orchestrator Agent** – Parses user input, delegates tasks, assembles responses  
2. **ProductStore** – Loads catalog, handles search & filtering  
3. **Session Manager** – Maintains carts, viewed products, preferences; persists session info  
4. **SQLite Databases** – `shopgenie.db` (products) and `shopgenie_sessions.db` (sessions)  
5. **App Layer (`app.py`)** – Initializes everything and provides the interactive interface  

## Repository Structure
| File | Description |
|------|-------------|
| `app.py` | Main entry point |
| `agents.py` | Core agent + orchestrator logic |
| `baseClass.py` | Shared abstractions for agents |
| `productstore.py` | Catalog handling and search logic |
| `1_Full_Catalog.py` | Builds the product catalog |
| `utils.py` | Utility functions |
| `tools.py` | Helper tools |
| `file_logger.py` | Logging utilities |
| `shopgenie.db` | Product database |
| `shopgenie_sessions.db` | Session storage |
| `arch_diag.png` | Architecture diagram |
| `*_backup.py` | Stable/previous module versions |
| `requirements.txt` | Python dependencies |

## Installation & Setup
```bash
git clone https://github.com/AdithyaRajagopalan2024/ShopGenie
cd ShopGenie

# (Optional) create environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Build catalog (first time only)
python 1_Full_Catalog.py

# Run the app
python app.py
