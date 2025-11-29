import logging
import json
from datetime import datetime

# Configure logger
logger = logging.getLogger('trace_logger')
logger.setLevel(logging.INFO)

# Create a file handler to write to trace.log
handler = logging.FileHandler('trace.log')
handler.setLevel(logging.INFO)

# Create a JSON formatter
formatter = logging.Formatter('%(message)s')
handler.setFormatter(formatter)

# Add the handler to the logger, ensuring it's only added once
if not logger.handlers:
    logger.addHandler(handler)

def log_trace(session_id: str, prompt: str, response: str):
    """Logs a trace of the agent interaction to a file in JSON format."""
    trace_data = {
        "datetime": datetime.utcnow().isoformat(),
        "session_id": session_id,
        "prompt": prompt,
        "response": response
    }
    logger.info(json.dumps(trace_data))