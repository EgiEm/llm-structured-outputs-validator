import json
import re

# 1. Define the concrete JSON Schema for tool calls
SCHEMA = {
    "type": "object",
    "required": ["intent", "slots"],
    "properties": {
        "intent": {
            "enum": ["create_task", "place_call", "answer_question",
                     "save_memory", "set_timer", "out_of_scope"]
        },
        "slots": { "type": "object" }
    },
    "additionalProperties": False
}

# 2. Extract JSON block helper
def extract_json_block(text: str) -> str:
    """
    Strips markdown code fences and extraneous prose to extract raw JSON block.
    """
    # Look for triple backticks with optional 'json' tag
    match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    
    # If no backticks, try to find the outer-most curly braces
    match_curly = re.search(r'(\{.*\})', text, re.DOTALL)
    if match_curly:
        return match_curly.group(1).strip()
        
    return text.strip()

# 3. Hardened Validator (validate_tool_call)
def validate_tool_call(obj, schema=SCHEMA) -> tuple[bool, list[str]]:
    """
    Checks obj against schema and returns (ok: bool, errors: list[str]).
    Each error message includes the specific key path of the failure.
    """
    errors = []
    
    # Rule 1: Top-level type
    if not isinstance(obj, dict):
        return False, ["(root): must be an object"]
        
    # Rule 2: Required keys present
    required = schema.get("required", [])
    for key in required:
        if key not in obj:
            errors.append(f"(root): missing required key {key}")
            
    # Rule 3: intent is in the enum
    if "intent" in obj:
        intent_val = obj["intent"]
        enum_vals = schema["properties"]["intent"].get("enum", [])
        if intent_val not in enum_vals:
            errors.append(f"intent: not in enum: {intent_val}")
            
    # Rule 4: additionalProperties is false
    if not schema.get("additionalProperties", True):
        allowed_keys = schema.get("properties", {}).keys()
        for key in obj.keys():
            if key not in allowed_keys:
                errors.append(f"{key}: extra key not allowed")
                
    # Rule 5: slots is an object, and nested slots typing check
    if "slots" in obj:
        slots_val = obj["slots"]
        if not isinstance(slots_val, dict):
            errors.append("slots: must be an object")
        else:
            for k, v in slots_val.items():
                # Reject lists and dicts
                if isinstance(v, (dict, list)):
                    errors.append(f"slots.{k}: wrong type")
                # Reject other non-primitive values that are not string or number (like bool, None)
                elif not isinstance(v, (str, int, float)) or isinstance(v, bool):
                    errors.append(f"slots.{k}: wrong type")
                    
    return len(errors) == 0, errors

# 4. Repair Pass (repair)
def repair(raw) -> dict:
    """
    Deterministic repair pass that cleans cheap formatting crimes.
    - If raw is a string, strip code fences/preamble and parse as JSON.
    - If parsing fails, propagates ValueError.
    - If intent is capitalized, lowercases it.
    - If slots is missing, defaults it to {}.
    - If there are unknown keys, drops them.
    
    Fatal errors (invalid intents, wrong types) are left to fail validation.
    """
    if isinstance(raw, str):
        cleaned = extract_json_block(raw)
        try:
            obj = json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {str(e)}")
    elif isinstance(raw, dict):
        obj = dict(raw)
    else:
        raise ValueError("Top-level is not an object or a parseable string")
        
    if not isinstance(obj, dict):
        return obj

    # 1. Lowercase capitalized intent
    if "intent" in obj and isinstance(obj["intent"], str):
        obj["intent"] = obj["intent"].lower()
        
    # 2. Drop unknown keys (additionalProperties: false)
    allowed_keys = set(SCHEMA["properties"].keys())
    for key in list(obj.keys()):
        if key not in allowed_keys:
            obj.pop(key)
            
    # 3. Default missing slots to {}
    if "slots" not in obj:
        obj["slots"] = {}
        
    return obj

# 5. Combined Pipeline (repair_then_validate)
def repair_then_validate(raw) -> tuple[bool, list[str], str]:
    """
    Runs repair on raw input and validates the result.
    Returns (ok, errors, status_message)
    """
    try:
        repaired = repair(raw)
    except Exception as e:
        return False, [f"(root): {str(e)}"], f"unrepairable: {str(e)}"
        
    ok, errors = validate_tool_call(repaired)
    if ok:
        return True, [], "repaired & valid"
    else:
        first_error = errors[0] if errors else "unknown error"
        return False, errors, f"unrepairable: {first_error}"

# 6. Define the Torture-Test Suite (19 items, at least 2 per failure mode + 3 clean)
TORTURE_TESTS = [
    # --- Mode 1: missing key ---
    {
        "id": 1,
        "mode": "missing key",
        "description": "Missing intent key",
        "input": {"slots": {"query": "what is this"}},
        "expected_val": (False, ["(root): missing required key intent"]),
        "expected_pipeline": (False, ["(root): missing required key intent"])
    },
    {
        "id": 2,
        "mode": "missing key",
        "description": "Missing slots key (repaired in pipeline)",
        "input": {"intent": "set_timer"},
        "expected_val": (False, ["(root): missing required key slots"]),
        "expected_pipeline": (True, [])
    },
    {
        "id": 3,
        "mode": "missing key",
        "description": "Missing both intent and slots keys",
        "input": {},
        "expected_val": (False, ["(root): missing required key intent", "(root): missing required key slots"]),
        "expected_pipeline": (False, ["(root): missing required key intent"])
    },
    
    # --- Mode 2: bad enum ---
    {
        "id": 4,
        "mode": "bad enum",
        "description": "Hallucinated intent 'call_mom'",
        "input": {"intent": "call_mom", "slots": {}},
        "expected_val": (False, ["intent: not in enum: call_mom"]),
        "expected_pipeline": (False, ["intent: not in enum: call_mom"])
    },
    {
        "id": 5,
        "mode": "bad enum",
        "description": "Hallucinated intent 'order_pizza'",
        "input": {"intent": "order_pizza", "slots": {"to": "123 Main St"}},
        "expected_val": (False, ["intent: not in enum: order_pizza"]),
        "expected_pipeline": (False, ["intent: not in enum: order_pizza"])
    },
    
    # --- Mode 3: extra key ---
    {
        "id": 6,
        "mode": "extra key",
        "description": "Undeclared key 'confidence' (dropped in pipeline)",
        "input": {"intent": "set_timer", "slots": {"minutes": 5}, "confidence": 0.95},
        "expected_val": (False, ["confidence: extra key not allowed"]),
        "expected_pipeline": (True, [])
    },
    {
        "id": 7,
        "mode": "extra key",
        "description": "Undeclared key 'vibe' (dropped in pipeline)",
        "input": {"intent": "answer_question", "slots": {"query": "who is egi"}, "vibe": "chill"},
        "expected_val": (False, ["vibe: extra key not allowed"]),
        "expected_pipeline": (True, [])
    },
    {
        "id": 8,
        "mode": "extra key",
        "description": "Multiple undeclared keys 'reasoning' and 'confidence' (dropped in pipeline)",
        "input": {"intent": "save_memory", "slots": {"note": "test"}, "reasoning": "thought details", "confidence": 0.99},
        "expected_val": (False, ["reasoning: extra key not allowed", "confidence: extra key not allowed"]),
        "expected_pipeline": (True, [])
    },
    
    # --- Mode 4: wrong type ---
    {
        "id": 9,
        "mode": "wrong type",
        "description": "slots is a string instead of an object",
        "input": {"intent": "set_timer", "slots": "10 minutes"},
        "expected_val": (False, ["slots: must be an object"]),
        "expected_pipeline": (False, ["slots: must be an object"])
    },
    {
        "id": 10,
        "mode": "wrong type",
        "description": "nested slots value is a list (nested slots typing)",
        "input": {"intent": "create_task", "slots": {"text": ["buy groceries", "wash car"]}},
        "expected_val": (False, ["slots.text: wrong type"]),
        "expected_pipeline": (False, ["slots.text: wrong type"])
    },
    {
        "id": 11,
        "mode": "wrong type",
        "description": "nested slots value is a dictionary (nested slots typing)",
        "input": {"intent": "place_call", "slots": {"who": {"name": "John", "relation": "friend"}}},
        "expected_val": (False, ["slots.who: wrong type"]),
        "expected_pipeline": (False, ["slots.who: wrong type"])
    },
    {
        "id": 12,
        "mode": "wrong type",
        "description": "intent is a number instead of string",
        "input": {"intent": 123, "slots": {}},
        "expected_val": (False, ["intent: not in enum: 123"]),
        "expected_pipeline": (False, ["intent: not in enum: 123"])
    },
    {
        "id": 13,
        "mode": "wrong type",
        "description": "nested slots value is boolean (nested slots typing)",
        "input": {"intent": "set_timer", "slots": {"minutes": True}},
        "expected_val": (False, ["slots.minutes: wrong type"]),
        "expected_pipeline": (False, ["slots.minutes: wrong type"])
    },
    
    # --- Mode 5: prose-not-object ---
    {
        "id": 14,
        "mode": "prose-not-object",
        "description": "Plain conversational text refusal",
        "input": "I cannot help you write python scripts. I can only route task management, calling, and timer commands.",
        "expected_val": (False, ["(root): must be an object"]),
        "expected_pipeline": (False, ["(root): Invalid JSON format: Expecting value: line 1 column 1 (char 0)"])
    },
    {
        "id": 15,
        "mode": "prose-not-object",
        "description": "Fenced JSON with syntax error (trailing comma)",
        "input": "```json\n{\n  \"intent\": \"create_task\",\n  \"slots\": {\n    \"text\": \"grocery list\"\n  },\n}\n```",
        "expected_val": (False, ["(root): must be an object"]),
        "expected_pipeline": (False, ["(root): Invalid JSON format: Expecting property name enclosed in double quotes: line 6 column 1 (char 64)"])
    },
    
    # --- Clean Cases ---
    {
        "id": 16,
        "mode": "clean",
        "description": "Standard clean valid object",
        "input": {"intent": "set_timer", "slots": {"minutes": 10}},
        "expected_val": (True, []),
        "expected_pipeline": (True, [])
    },
    {
        "id": 17,
        "mode": "clean",
        "description": "German call mom utterance (enumplace_call matches place_call)",
        "input": {"intent": "place_call", "slots": {"who": "Mama"}},  # = call mom
        "expected_val": (True, []),
        "expected_pipeline": (True, [])
    },
    {
        "id": 18,
        "mode": "clean",
        "description": "German answer question with inline gloss",
        "input": {"intent": "answer_question", "slots": {"query": "Was ist die Hauptstadt von Kosovo?"}},  # = What is the capital of Kosovo?
        "expected_val": (True, []),
        "expected_pipeline": (True, [])
    },
    {
        "id": 19,
        "mode": "clean",
        "description": "Surrounding fences, capitalized intent and extra key (fully repaired and validated)",
        "input": "```json\n{\n  \"intent\": \"Create_Task\",\n  \"slots\": {\n    \"text\": \"Buy milk\"\n  },\n  \"confidence\": 0.99\n}\n```",
        "expected_val": (False, ["(root): must be an object"]),
        "expected_pipeline": (True, [])
    }
]

def run_tests():
    print("=" * 80)
    print("RUNNING DAY 2 STRUCTURAL VALIDATION & REPAIR TORTURE TESTS")
    print("=" * 80)
    
    all_passed = True
    
    for test in TORTURE_TESTS:
        tid = test["id"]
        mode = test["mode"]
        desc = test["description"]
        raw = test["input"]
        
        # 1. Run Pure Validation (No Repair)
        val_ok, val_errs = validate_tool_call(raw)
        expected_val_ok, expected_val_errs = test["expected_val"]
        
        val_passed = (val_ok == expected_val_ok)
        if val_passed and not val_ok:
            for e_err in expected_val_errs:
                if not any(e_err in a_err for a_err in val_errs):
                    val_passed = False
                    break
        
        # 2. Run Repair Then Validate Pipeline
        pip_ok, pip_errs, status_msg = repair_then_validate(raw)
        expected_pip_ok, expected_pip_errs = test["expected_pipeline"]
        
        pip_passed = (pip_ok == expected_pip_ok)
        if pip_passed and not pip_ok:
            for e_err in expected_pip_errs:
                if "Invalid JSON format" in e_err:
                    if not any("Invalid JSON format" in a_err for a_err in pip_errs):
                        pip_passed = False
                        break
                elif not any(e_err in a_err for a_err in pip_errs):
                    pip_passed = False
                    break
                    
        test_passed = val_passed and pip_passed
        if not test_passed:
            all_passed = False
            
        status_str = "PASS" if test_passed else "FAIL"
        
        print(f"[{status_str}] Test #{tid} | Mode: {mode}")
        print(f"      Description: {desc}")
        print(f"      Raw Input:   {raw}")
        print(f"      [Pure Validation]")
        print(f"         Expected: {expected_val_ok}, {expected_val_errs}")
        print(f"         Actual:   {val_ok}, {val_errs} (Passed: {val_passed})")
        print(f"      [Pipeline (Repair -> Validate)]")
        print(f"         Expected: {expected_pip_ok}, {expected_pip_errs}")
        print(f"         Actual:   {pip_ok}, {pip_errs} | Status: '{status_msg}' (Passed: {pip_passed})")
        print("-" * 80)
        
    print("=" * 80)
    if all_passed:
        print("ALL TESTS PASSED SUCCESSFULLY!")
    else:
        print("SOME TESTS FAILED. PLEASE DEBUG.")
    print("=" * 80)
    
    return all_passed

if __name__ == "__main__":
    run_tests()
