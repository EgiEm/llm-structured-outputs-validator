# 🛠️ Day 2 · Daily Challenge: Build Your Validator + a Torture-Test Suite

This document outlines the final implementation of the hardened JSON-Schema tool-call validator and repair pipeline. By combining deterministic repairs with strict schema rules and recursive value validation, this system forms a reliable safety net for unconstrained LLM outputs.

---

## 💻 Finalised Validation & Repair Code

The source file is located at [run_challenge.py](file:///c:/Users/beKs/Desktop/Brigada/llm-structured-outputs-validator/day%202/run_challenge.py). Below are the core functions implementing the schema gate:

### 1. The Hardened Validator
The validator enforces:
- Object structure at the root level.
- Presence of required keys (`intent`, `slots`).
- Exact enum compliance for `intent`.
- Zero tolerance for undeclared top-level properties (`additionalProperties: false`).
- Nested typing constraints: `slots` must be a dictionary, and slot values can only be primitive strings or numbers (no dicts, lists, booleans, or nulls). Every failure reports its precise key path (e.g., `slots.minutes: wrong type`).

```python
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
```

### 2. The Repair Pass
The repair function acts as a clean-up layer. It resolves non-destructive formatting anomalies where the underlying semantics are unambiguous. It does not guess meaning.

```python
def repair(raw) -> dict:
    """
    Deterministic repair pass that cleans cheap formatting crimes.
    - If raw is a string, strip code fences/preamble and parse as JSON.
    - If parsing fails, propagates ValueError.
    - If intent is capitalized, lowercases it.
    - If slots is missing, defaults it to {}.
    - If there are unknown keys, drops them.
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
```

---

## 📋 The Repair Policy Doc

This policy defines which format anomalies can be safely corrected programmatically and which constitute fatal structural/semantic contract breaches.

| Crime | Repair or Reject | Why |
| :--- | :--- | :--- |
| **Markdown code fence** | **Repair** (Strip it) | Fences are visual wrappers added by standard chat interfaces. The underlying text remains valid JSON structure, which can be extracted safely without modifying semantic content. |
| **Capitalised intent** | **Repair** (Lowercase it) | Casing differences (e.g. `Set_Timer` vs `set_timer`) represent mechanical capitalization. Normalizing to lower case does not affect semantic meaning. |
| **Missing `slots`** | **Repair** (Default to `{}`) | If the model selects a valid intent but forgets the `slots` key, it is safe to supply an empty parameters object `{}` rather than rejecting the call, since many intents do not require parameters. |
| **Unknown key** (e.g., `confidence`, `reasoning`) | **Repair** (Drop it) | The model often adds side-channel reasoning or confidence scores. Dropping them preserves the requested properties and prevents dispatcher crashes from unexpected arguments. |
| **Intent not in the enum** | **Reject** (Fatal) | A key path failure here (e.g., `intent: call_mom`) cannot be repaired because the assistant has no way of safely selecting which of the 6 allowed intents was intended. Guessing changes program behavior. |
| **Wrong-typed `slots`** | **Reject** (Fatal) | If `slots` is a string or contains complex nested dictionaries/lists, the data contract is fundamentally broken. Coercing or parsing nested structures risks introducing silent corruption. |

### ⚠️ Ordering Rule: Repair THEN Validate, Never Reverse

> [!IMPORTANT]
> The order of operations must strictly be **repair-then-validate**.
> 
> If we validate first, a fenced-but-otherwise-perfect JSON block gets rejected immediately for not being a structured dictionary. Since it was rejected, we lose the opportunity to strip the markdown fence and run the tool. Pre-cleaning removes the superficial "cheap crimes" of the LLM before we judge its underlying structural adherence.

---

## 🧪 Torture-Test Suite (19 Test Cases)

To stress-test our validation gate, we designed a suite of **19 hand-crafted test cases**, including 2+ cases per failure mode, 3 clean passing cases, and language-independent German inputs.

| ID | Failure Mode | Input Description | Raw Input Structure | Expected Pure Validation | Expected Pipeline | Actual Pipeline Status |
| :-: | :--- | :--- | :--- | :-: | :-: | :--- |
| **1** | missing key | Missing intent key | `{"slots": {"query": "what is this"}}` | FAIL | FAIL | unrepairable: (root): missing required key intent |
| **2** | missing key | Missing slots key (repaired) | `{"intent": "set_timer"}` | FAIL | **PASS** | repaired & valid |
| **3** | missing key | Missing both keys | `{}` | FAIL | FAIL | unrepairable: (root): missing required key intent |
| **4** | bad enum | Hallucinated intent | `{"intent": "call_mom", "slots": {}}` | FAIL | FAIL | unrepairable: intent: not in enum: call_mom |
| **5** | bad enum | Hallucinated intent | `{"intent": "order_pizza", "slots": {...}}` | FAIL | FAIL | unrepairable: intent: not in enum: order_pizza |
| **6** | extra key | Undeclared key `confidence` | `{"intent": "set_timer", "slots": {...}, "confidence": 0.95}` | FAIL | **PASS** | repaired & valid |
| **7** | extra key | Undeclared key `vibe` | `{"intent": "answer_question", "slots": {...}, "vibe": "chill"}` | FAIL | **PASS** | repaired & valid |
| **8** | extra key | Multiple undeclared keys | `{"intent": "save_memory", "slots": {...}, "reasoning": "...", "confidence": 0.99}` | FAIL | **PASS** | repaired & valid |
| **9** | wrong type | `slots` is a string | `{"intent": "set_timer", "slots": "10 minutes"}` | FAIL | FAIL | unrepairable: slots: must be an object |
| **10** | wrong type | nested slot value is a list | `{"intent": "create_task", "slots": {"text": ["buy groceries", "wash car"]}}` | FAIL | FAIL | unrepairable: slots.text: wrong type |
| **11** | wrong type | nested slot value is a dict | `{"intent": "place_call", "slots": {"who": {"name": "John"}}}` | FAIL | FAIL | unrepairable: slots.who: wrong type |
| **12** | wrong type | `intent` is a number | `{"intent": 123, "slots": {}}` | FAIL | FAIL | unrepairable: intent: not in enum: 123 |
| **13** | wrong type | nested slot value is boolean | `{"intent": "set_timer", "slots": {"minutes": True}}` | FAIL | FAIL | unrepairable: slots.minutes: wrong type |
| **14** | prose-not-object | Plain text conversational refusal | `"I cannot help you write python scripts..."` | FAIL | FAIL | unrepairable: Invalid JSON format |
| **15** | prose-not-object | Fenced JSON with syntax error | `"```json\n{\n  \"intent\": \"create_task\",\n  \"slots\": {\n    \"text\": \"grocery list\"\n  },\n}\n```"` | FAIL | FAIL | unrepairable: Invalid JSON format |
| **16** | clean | Standard clean valid object | `{"intent": "set_timer", "slots": {"minutes": 10}}` | **PASS** | **PASS** | repaired & valid |
| **17** | clean | German call mom (place_call) | `{"intent": "place_call", "slots": {"who": "Mama"}}` | **PASS** | **PASS** | repaired & valid |
| **18** | clean | German answer question | `{"intent": "answer_question", "slots": {"query": "Was ist die Hauptstadt..."}}` | **PASS** | **PASS** | repaired & valid |
| **19** | clean | Fenced + capitalized + extra key | `"```json\n{\n  \"intent\": \"Create_Task\",\n  \"slots\": {\n    \"text\": \"Buy milk\"\n  },\n  \"confidence\": 0.99\n}\n```"` | FAIL | **PASS** | repaired & valid |

---

## 📊 Deterministic Run Output

The execution of [run_challenge.py](file:///c:/Users/beKs/Desktop/Brigada/llm-structured-outputs-validator/day%202/run_challenge.py) produced the following complete log output:

```text
================================================================================
RUNNING DAY 2 STRUCTURAL VALIDATION & REPAIR TORTURE TESTS
================================================================================
[PASS] Test #1 | Mode: missing key
      Description: Missing intent key
      Raw Input:   {'slots': {'query': 'what is this'}}
      [Pure Validation]
         Expected: False, ['(root): missing required key intent']
         Actual:   False, ['(root): missing required key intent'] (Passed: True)
      [Pipeline (Repair -> Validate)]
         Expected: False, ['(root): missing required key intent']
         Actual:   False, ['(root): missing required key intent'] | Status: 'unrepairable: (root): missing required key intent' (Passed: True)
--------------------------------------------------------------------------------
[PASS] Test #2 | Mode: missing key
      Description: Missing slots key (repaired in pipeline)
      Raw Input:   {'intent': 'set_timer'}
      [Pure Validation]
         Expected: False, ['(root): missing required key slots']
         Actual:   False, ['(root): missing required key slots'] (Passed: True)
      [Pipeline (Repair -> Validate)]
         Expected: True, []
         Actual:   True, [] | Status: 'repaired & valid' (Passed: True)
--------------------------------------------------------------------------------
[PASS] Test #3 | Mode: missing key
      Description: Missing both intent and slots keys
      Raw Input:   {}
      [Pure Validation]
         Expected: False, ['(root): missing required key intent', '(root): missing required key slots']
         Actual:   False, ['(root): missing required key intent', '(root): missing required key slots'] (Passed: True)
      [Pipeline (Repair -> Validate)]
         Expected: False, ['(root): missing required key intent']
         Actual:   False, ['(root): missing required key intent'] | Status: 'unrepairable: (root): missing required key intent' (Passed: True)
--------------------------------------------------------------------------------
[PASS] Test #4 | Mode: bad enum
      Description: Hallucinated intent 'call_mom'
      Raw Input:   {'intent': 'call_mom', 'slots': {}}
      [Pure Validation]
         Expected: False, ['intent: not in enum: call_mom']
         Actual:   False, ['intent: not in enum: call_mom'] (Passed: True)
      [Pipeline (Repair -> Validate)]
         Expected: False, ['intent: not in enum: call_mom']
         Actual:   False, ['intent: not in enum: call_mom'] | Status: 'unrepairable: intent: not in enum: call_mom' (Passed: True)
--------------------------------------------------------------------------------
[PASS] Test #5 | Mode: bad enum
      Description: Hallucinated intent 'order_pizza'
      Raw Input:   {'intent': 'order_pizza', 'slots': {'to': '123 Main St'}}
      [Pure Validation]
         Expected: False, ['intent: not in enum: order_pizza']
         Actual:   False, ['intent: not in enum: order_pizza'] (Passed: True)
      [Pipeline (Repair -> Validate)]
         Expected: False, ['intent: not in enum: order_pizza']
         Actual:   False, ['intent: not in enum: order_pizza'] | Status: 'unrepairable: intent: not in enum: order_pizza' (Passed: True)
--------------------------------------------------------------------------------
[PASS] Test #6 | Mode: extra key
      Description: Undeclared key 'confidence' (dropped in pipeline)
      Raw Input:   {'intent': 'set_timer', 'slots': {'minutes': 5}, 'confidence': 0.95}
      [Pure Validation]
         Expected: False, ['confidence: extra key not allowed']
         Actual:   False, ['confidence: extra key not allowed'] (Passed: True)
      [Pipeline (Repair -> Validate)]
         Expected: True, []
         Actual:   True, [] | Status: 'repaired & valid' (Passed: True)
--------------------------------------------------------------------------------
[PASS] Test #7 | Mode: extra key
      Description: Undeclared key 'vibe' (dropped in pipeline)
      Raw Input:   {'intent': 'answer_question', 'slots': {'query': 'who is egi'}, 'vibe': 'chill'}
      [Pure Validation]
         Expected: False, ['vibe: extra key not allowed']
         Actual:   False, ['vibe: extra key not allowed'] (Passed: True)
      [Pipeline (Repair -> Validate)]
         Expected: True, []
         Actual:   True, [] | Status: 'repaired & valid' (Passed: True)
--------------------------------------------------------------------------------
[PASS] Test #8 | Mode: extra key
      Description: Multiple undeclared keys 'reasoning' and 'confidence' (dropped in pipeline)
      Raw Input:   {'intent': 'save_memory', 'slots': {'note': 'test'}, 'reasoning': 'thought details', 'confidence': 0.99}
      [Pure Validation]
         Expected: False, ['reasoning: extra key not allowed', 'confidence: extra key not allowed']
         Actual:   False, ['reasoning: extra key not allowed', 'confidence: extra key not allowed'] (Passed: True)
      [Pipeline (Repair -> Validate)]
         Expected: True, []
         Actual:   True, [] | Status: 'repaired & valid' (Passed: True)
--------------------------------------------------------------------------------
[PASS] Test #9 | Mode: wrong type
      Description: slots is a string instead of an object
      Raw Input:   {'intent': 'set_timer', 'slots': '10 minutes'}
      [Pure Validation]
         Expected: False, ['slots: must be an object']
         Actual:   False, ['slots: must be an object'] (Passed: True)
      [Pipeline (Repair -> Validate)]
         Expected: False, ['slots: must be an object']
         Actual:   False, ['slots: must be an object'] | Status: 'unrepairable: slots: must be an object' (Passed: True)
--------------------------------------------------------------------------------
[PASS] Test #10 | Mode: wrong type
      Description: nested slots value is a list (nested slots typing)
      Raw Input:   {'intent': 'create_task', 'slots': {'text': ['buy groceries', 'wash car']}}
      [Pure Validation]
         Expected: False, ['slots.text: wrong type']
         Actual:   False, ['slots.text: wrong type'] (Passed: True)
      [Pipeline (Repair -> Validate)]
         Expected: False, ['slots.text: wrong type']
         Actual:   False, ['slots.text: wrong type'] | Status: 'unrepairable: slots.text: wrong type' (Passed: True)
--------------------------------------------------------------------------------
[PASS] Test #11 | Mode: wrong type
      Description: nested slots value is a dictionary (nested slots typing)
      Raw Input:   {'intent': 'place_call', 'slots': {'who': {'name': 'John', 'relation': 'friend'}}}
      [Pure Validation]
         Expected: False, ['slots.who: wrong type']
         Actual:   False, ['slots.who: wrong type'] (Passed: True)
      [Pipeline (Repair -> Validate)]
         Expected: False, ['slots.who: wrong type']
         Actual:   False, ['slots.who: wrong type'] | Status: 'unrepairable: slots.who: wrong type' (Passed: True)
--------------------------------------------------------------------------------
[PASS] Test #12 | Mode: wrong type
      Description: intent is a number instead of string
      Raw Input:   {'intent': 123, 'slots': {}}
      [Pure Validation]
         Expected: False, ['intent: not in enum: 123']
         Actual:   False, ['intent: not in enum: 123'] (Passed: True)
      [Pipeline (Repair -> Validate)]
         Expected: False, ['intent: not in enum: 123']
         Actual:   False, ['intent: not in enum: 123'] | Status: 'unrepairable: intent: not in enum: 123' (Passed: True)
--------------------------------------------------------------------------------
[PASS] Test #13 | Mode: wrong type
      Description: nested slots value is boolean (nested slots typing)
      Raw Input:   {'intent': 'set_timer', 'slots': {'minutes': True}}
      [Pure Validation]
         Expected: False, ['slots.minutes: wrong type']
         Actual:   False, ['slots.minutes: wrong type'] (Passed: True)
      [Pipeline (Repair -> Validate)]
         Expected: False, ['slots.minutes: wrong type']
         Actual:   False, ['slots.minutes: wrong type'] | Status: 'unrepairable: slots.minutes: wrong type' (Passed: True)
--------------------------------------------------------------------------------
[PASS] Test #14 | Mode: prose-not-object
      Description: Plain conversational text refusal
      Raw Input:   I cannot help you write python scripts. I can only route task management, calling, and timer commands.
      [Pure Validation]
         Expected: False, ['(root): must be an object']
         Actual:   False, ['(root): must be an object'] (Passed: True)
      [Pipeline (Repair -> Validate)]
         Expected: False, ['(root): Invalid JSON format: Expecting value: line 1 column 1 (char 0)']
         Actual:   False, ['(root): Invalid JSON format: Expecting value: line 1 column 1 (char 0)'] | Status: 'unrepairable: Invalid JSON format: Expecting value: line 1 column 1 (char 0)' (Passed: True)
--------------------------------------------------------------------------------
[PASS] Test #15 | Mode: prose-not-object
      Description: Fenced JSON with syntax error (trailing comma)
      Raw Input:   ```json
{
  "intent": "create_task",
  "slots": {
    "text": "grocery list"
  },
}
```
      [Pure Validation]
         Expected: False, ['(root): must be an object']
         Actual:   False, ['(root): must be an object'] (Passed: True)
      [Pipeline (Repair -> Validate)]
         Expected: False, ['(root): Invalid JSON format: Expecting property name enclosed in double quotes: line 6 column 1 (char 64)']
         Actual:   False, ['(root): Invalid JSON format: Expecting property name enclosed in double quotes: line 6 column 1 (char 74)'] | Status: 'unrepairable: Invalid JSON format: Expecting property name enclosed in double quotes: line 6 column 1 (char 74)' (Passed: True)
--------------------------------------------------------------------------------
[PASS] Test #16 | Mode: clean
      Description: Standard clean valid object
      Raw Input:   {'intent': 'set_timer', 'slots': {'minutes': 10}}
      [Pure Validation]
         Expected: True, []
         Actual:   True, [] (Passed: True)
      [Pipeline (Repair -> Validate)]
         Expected: True, []
         Actual:   True, [] | Status: 'repaired & valid' (Passed: True)
--------------------------------------------------------------------------------
[PASS] Test #17 | Mode: clean
      Description: German call mom utterance (enumplace_call matches place_call)
      Raw Input:   {'intent': 'place_call', 'slots': {'who': 'Mama'}}
      [Pure Validation]
         Expected: True, []
         Actual:   True, [] (Passed: True)
      [Pipeline (Repair -> Validate)]
         Expected: True, []
         Actual:   True, [] | Status: 'repaired & valid' (Passed: True)
--------------------------------------------------------------------------------
[PASS] Test #18 | Mode: clean
      Description: German answer question with inline gloss
      Raw Input:   {'intent': 'answer_question', 'slots': {'query': 'Was ist die Hauptstadt von Kosovo?'}}
      [Pure Validation]
         Expected: True, []
         Actual:   True, [] (Passed: True)
      [Pipeline (Repair -> Validate)]
         Expected: True, []
         Actual:   True, [] | Status: 'repaired & valid' (Passed: True)
--------------------------------------------------------------------------------
[PASS] Test #19 | Mode: clean
      Description: Surrounding fences, capitalized intent and extra key (fully repaired and validated)
      Raw Input:   ```json
{
  "intent": "Create_Task",
  "slots": {
    "text": "Buy milk"
  },
  "confidence": 0.99
}
```
      [Pure Validation]
         Expected: False, ['(root): must be an object']
         Actual:   False, ['(root): must be an object'] (Passed: True)
      [Pipeline (Repair -> Validate)]
         Expected: True, []
         Actual:   True, [] | Status: 'repaired & valid' (Passed: True)
--------------------------------------------------------------------------------
================================================================================
ALL TESTS PASSED SUCCESSFULLY!
================================================================================
```

---

## 📈 Learnings & Reflection

1. **Precision in Paths**: Standard validators usually return error paths as structured lists or tuples. In this hands-on exercise, mapping paths explicitly as strings (e.g. `slots.minutes: wrong type`) provides high transparency for both automated retry loops and humans debugging LLM output.
2. **Defensive Programming**: While tomorrow's **guided decoding** will ensure that the model physically cannot emit strings outside our intent enum or include keys that are not allowed by the schema, this Python gate remains crucial as a fast, zero-dependency second line of defense against future model changes or schema drift.
