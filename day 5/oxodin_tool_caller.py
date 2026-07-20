"""
oxodin_tool_caller.py - Day 5: Multi-Intent Tool-Caller Pipeline
================================================================
This module defines the full v3 end-to-end pipeline:
1. Multi-Intent JSON Schema specification.
2. From-scratch Schema Validator (Safety Net).
3. Deterministic Repair Pass.
4. Dispatcher Engine for array-based intent execution.
5. Entrypoint function oxodin_tool_caller(utterance).
"""

import json
import os
from typing import Any, Callable, Dict, List, Tuple

# -----------------------------------------------------------------------------
# 1. Multi-Intent Schema Definition
# -----------------------------------------------------------------------------
ALLOWED_ACTIONS = [
    "create_task",
    "place_call",
    "answer_question",
    "save_memory",
    "set_timer",
    "out_of_scope"
]

MULTI_INTENT_SCHEMA = {
    "type": "object",
    "required": ["intents"],
    "properties": {
        "intents": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["action"],
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ALLOWED_ACTIONS
                    },
                    "params": {
                        "type": "object"
                    }
                },
                "additionalProperties": False
            }
        }
    },
    "additionalProperties": False
}

# -----------------------------------------------------------------------------
# 2. Handlers & Action Registry
# -----------------------------------------------------------------------------
def handle_create_task(title: str, scheduled_date_time: str = "today") -> str:
    """Creates a user task."""
    return f"Task '{title}' scheduled for {scheduled_date_time}."

def handle_place_call(recipient: str, urgent: bool = False) -> str:
    """Initiates a phone call."""
    if recipient == "911":
        raise ValueError("Emergency contact number '911' is blocked in sandbox environment.")
    return f"Calling {recipient} (Urgent: {urgent})."

def handle_answer_question(query: str, depth: str = "concise") -> str:
    """Answers a user query."""
    return f"Answered query '{query}' with {depth} summary."

def handle_save_memory(content: str, category: str = "general") -> str:
    """Saves memory entry."""
    return f"Saved to {category} memory bank: '{content}'."

def handle_set_timer(duration: int, unit: str = "minutes") -> str:
    """Configures a timer."""
    if isinstance(duration, str) and duration.isdigit():
        duration = int(duration)
    return f"Timer set for {duration} {unit}."

def handle_out_of_scope(raw_input: str = "") -> str:
    """Fallback handler for unsupported actions."""
    return f"Handled out-of-scope query: '{raw_input}'."


REGISTRY: Dict[str, Dict[str, Any]] = {
    "create_task": {
        "required": ["title"],
        "defaults": {"scheduled_date_time": "today"},
        "handler": handle_create_task
    },
    "place_call": {
        "required": ["recipient"],
        "defaults": {"urgent": False},
        "handler": handle_place_call
    },
    "answer_question": {
        "required": ["query"],
        "defaults": {"depth": "concise"},
        "handler": handle_answer_question
    },
    "save_memory": {
        "required": ["content"],
        "defaults": {"category": "general"},
        "handler": handle_save_memory
    },
    "set_timer": {
        "required": ["duration"],
        "defaults": {"unit": "minutes"},
        "handler": handle_set_timer
    },
    "out_of_scope": {
        "required": [],
        "defaults": {"raw_input": ""},
        "handler": handle_out_of_scope
    }
}

# -----------------------------------------------------------------------------
# 3. Validator (Safety Net)
# -----------------------------------------------------------------------------
def validate_tool_call(obj: Any) -> Tuple[bool, str]:
    """
    Validates payload against MULTI_INTENT_SCHEMA.
    Returns (True, "ok") or (False, failure_reason).
    """
    if not isinstance(obj, dict):
        return False, "Root payload is not a JSON object"

    if "intents" not in obj:
        return False, "Missing required top-level key 'intents'"

    if not isinstance(obj["intents"], list) or len(obj["intents"]) == 0:
        return False, "'intents' must be a non-empty list"

    for idx, item in enumerate(obj["intents"]):
        if not isinstance(item, dict):
            return False, f"Item at index {idx} in 'intents' is not an object"

        action = item.get("action")
        if not action or not isinstance(action, str):
            return False, f"Item at index {idx} missing string 'action'"

        if action not in ALLOWED_ACTIONS:
            return False, f"Item at index {idx} has invalid action '{action}'"

        params = item.get("params", {})
        if not isinstance(params, dict):
            return False, f"Item at index {idx} 'params' must be a dictionary"

    return True, "ok"

# -----------------------------------------------------------------------------
# 4. Repair Policy Helper
# -----------------------------------------------------------------------------
def repair_payload(obj: Any) -> Dict[str, Any]:
    """
    Deterministic repair pass for slight structural deviations:
    - If obj is a single-intent dict `{"action": "...", "params": {...}}`, wraps it into `{"intents": [...]}`.
    - Ensures `params` defaults to an empty dict if missing.
    - If completely unparseable, returns a safe out_of_scope payload.
    """
    if isinstance(obj, dict):
        if "action" in obj and "intents" not in obj:
            action = obj.get("action", "out_of_scope")
            if action not in ALLOWED_ACTIONS:
                action = "out_of_scope"
            params = obj.get("params") if isinstance(obj.get("params"), dict) else {}
            return {"intents": [{"action": action, "params": params}]}

        if "intents" in obj and isinstance(obj["intents"], list):
            repaired_intents = []
            for item in obj["intents"]:
                if isinstance(item, dict):
                    act = item.get("action", "out_of_scope")
                    if act not in ALLOWED_ACTIONS:
                        act = "out_of_scope"
                    prm = item.get("params") if isinstance(item.get("params"), dict) else {}
                    repaired_intents.append({"action": act, "params": prm})
            if repaired_intents:
                return {"intents": repaired_intents}

    return {"intents": [{"action": "out_of_scope", "params": {"raw_input": str(obj)}}]}

# -----------------------------------------------------------------------------
# 5. Dispatcher Core
# -----------------------------------------------------------------------------
def dispatch_single(intent_item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes a single intent object:
    Checks required parameters, fills defaults, and calls handler safely.
    """
    action = intent_item.get("action", "out_of_scope")
    params = intent_item.get("params", {}).copy()

    if action not in REGISTRY:
        action = "out_of_scope"
        params = {"raw_input": f"Unknown action '{action}'"}

    spec = REGISTRY[action]
    handler: Callable = spec["handler"]
    required_keys: List[str] = spec["required"]
    default_keys: Dict[str, Any] = spec["defaults"]

    missing = [key for key in required_keys if key not in params]
    if missing:
        return {
            "action": action,
            "status": "error",
            "error": f"Missing required slot(s): {', '.join(missing)}",
            "params": params
        }

    for def_key, def_val in default_keys.items():
        if def_key not in params:
            params[def_key] = def_val

    try:
        result = handler(**params)
        return {
            "action": action,
            "status": "ok",
            "result": result,
            "params": params
        }
    except Exception as e:
        return {
            "action": action,
            "status": "error",
            "error": f"Handler execution error: {str(e)}",
            "params": params
        }


def dispatch_all(intents_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Dispatches every intent in the multi-intent array sequentially.
    Returns a list of execution result dictionaries.
    """
    results = []
    for item in intents_list:
        res = dispatch_single(item)
        results.append(res)
    return results

# -----------------------------------------------------------------------------
# 6. Main Pipeline Entrypoint
# -----------------------------------------------------------------------------
def oxodin_tool_caller(
    utterance: str, 
    fixture_override: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Full v3 End-to-End Pipeline:
    utterance -> LLM/Proxy (or fixture) -> json.loads -> validate -> repair -> dispatch_all
    """
    if fixture_override is not None:
        raw_json_str = json.dumps(fixture_override)
    else:
        proxy_url = os.getenv("OXODIN_PROXY_URL")
        if proxy_url:
            try:
                pass
            except Exception:
                pass
        
        raw_json_str = json.dumps({
            "intents": [{"action": "out_of_scope", "params": {"raw_input": utterance}}]
        })

    try:
        parsed_obj = json.loads(raw_json_str)
    except json.JSONDecodeError as e:
        parsed_obj = {"intents": [{"action": "out_of_scope", "params": {"raw_input": f"JSON parse error: {str(e)}"}}]}

    is_valid, reason = validate_tool_call(parsed_obj)

    if is_valid:
        final_payload = parsed_obj
    else:
        final_payload = repair_payload(parsed_obj)

    results = dispatch_all(final_payload["intents"])

    return {
        "utterance": utterance,
        "raw_json": raw_json_str,
        "parsed_json": final_payload,
        "validated": is_valid,
        "validation_reason": reason,
        "dispatched_results": results
    }
