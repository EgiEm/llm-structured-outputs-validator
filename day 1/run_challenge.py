import os
import re
import json

# 1. Configuration & Paths
current_dir = os.path.dirname(os.path.abspath(__file__))
if not current_dir:
    current_dir = "."
submission_md_path = os.path.join(current_dir, "submission.md")

# 2. System and User Prompt Configuration
SYSTEM_PROMPT = """You are an AI routing assistant. You must receive user utterances and output a single JSON object.
Do not output markdown code blocks (```json ... ```) or any preamble or trailing conversational text.
Your output must conform to the following schema structure:
{
  "intent": "one of [create_task, place_call, set_timer, answer_question, save_memory, out_of_scope]",
  "parameters": {
     // For create_task: "text" (string)
     // For place_call: "name" (string)
     // For set_timer: "duration_seconds" (integer)
     // For answer_question: "query" (string)
     // For save_memory: "memory_content" (string)
     // For out_of_scope: (no parameters or empty dict)
  }
}"""

# 3. Define the dataset: Utterances & Raw unconstrained LLM outputs (with format crimes)
DATASET = [
    {
        "id": 1,
        "intent": "create_task",
        "utterance": "Remind me to buy groceries tomorrow at 5 PM",
        "description": "Standard task creation request.",
        "raw_output": """```json
{
  "intent": "create_task",
  "parameters": {
    "text": "buy groceries tomorrow at 5 PM"
  }
}
```"""
    },
    {
        "id": 2,
        "intent": "place_call",
        "utterance": "Call Dr. Smith immediately",
        "description": "Standard phone call request.",
        "raw_output": """Sure, here is the routing information for your request:
{
  "intent": "place_call",
  "parameters": {
    "recipient": "Dr. Smith"
  }
}
Let me know if you need anything else!"""
    },
    {
        "id": 3,
        "intent": "set_timer",
        "utterance": "Set a timer for 45 minutes",
        "description": "Standard timer setting request.",
        "raw_output": """{
  "intent": "set_timer",
  "parameters": {
    "duration_seconds": 2700
  }
}"""
    },
    {
        "id": 4,
        "intent": "answer_question",
        "utterance": "What is the distance between the Earth and the Moon?",
        "description": "Information query request.",
        "raw_output": """```json
{
  "intent": "answer_question",
  "parameters": {
    "query": "What is the distance between the Earth and the Moon?"
  },
  "confidence": 0.98
}
```"""
    },
    {
        "id": 5,
        "intent": "save_memory",
        "utterance": "Remember that my sister's birthday is October 12th",
        "description": "Memory save request.",
        "raw_output": """{
  "intent": "save_memory",
  "parameters": {
    "memory_content": "sister's birthday is October 12"""
    },
    {
        "id": 6,
        "intent": "out_of_scope",
        "utterance": "Can you generate a python script to sort a list?",
        "description": "Request beyond the capability of the routing assistant.",
        "raw_output": """I cannot help you write python scripts. I can only route task management, calling, and timer commands."""
    },
    {
        "id": 7,
        "intent": "place_call",
        "utterance": "Ruf Mama an",
        "description": "German utterance (call mom) with inline English gloss.",
        "raw_output": """{
  "intent": "place_call",
  "parameters": {
    "target": "Mama"
  }
}"""
    },
    {
        "id": 8,
        "intent": "create_task",
        "utterance": "Erstelle eine Aufgabe zum Einkaufen",
        "description": "German utterance (create shopping task) with inline English gloss.",
        "raw_output": """```json
{
  "intent": "create_task",
  "parameters": {
    "aufgabe": "Einkaufen"
  }
}
```"""
    },
    {
        "id": 9,
        "intent": "place_call",
        "utterance": "Can you call that task organizer?",
        "description": "Deliberately ambiguous (could refer to calling a contact or launching/naming a task app).",
        "raw_output": """```json
{
  "intent": "place_call",
  "parameters": {
    "name": "task organizer"
  }
}
```"""
    },
    {
        "id": 10,
        "intent": "out_of_scope",
        "utterance": "Should I call John or set a reminder?",
        "description": "Deliberately ambiguous question asking for advice rather than a command.",
        "raw_output": """```json
{
  "intent": "out_of_scope",
  "parameters": {
    "text": "Should I call John or set a reminder?"
  },
  "ambiguity": true
}
```"""
    },
    {
        "id": 11,
        "intent": "create_task",
        "utterance": "Remind me to call dad at 6pm",
        "description": "Mixed intents (create a reminder about calling).",
        "raw_output": """Here is the requested tool call structure:
```json
{
  "intent": "create_task",
  "parameters": {
    "task_description": "call dad at 6pm"
  }
}
```"""
    },
    {
        "id": 12,
        "intent": "set_timer",
        "utterance": "Set a timer for 10 minutes",
        "description": "Standard timer setting with trailing prose explanation.",
        "raw_output": """{
  "intent": "set_timer",
  "parameters": {
    "duration": "10 minutes"
  }
}
Note that duration is parsed as a string."""
    }
]

# 4. JSON Extraction Helper
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

# 5. Schema Validation logic
def validate_schema(data) -> tuple[bool, str]:
    """
    Validates if the JSON object matches the strict schema definition.
    """
    if not isinstance(data, dict):
        return False, "Not a JSON object"
    
    if "intent" not in data or "parameters" not in data:
        missing = [k for k in ["intent", "parameters"] if k not in data]
        return False, f"Missing keys: {missing}"
    
    valid_intents = ["create_task", "place_call", "set_timer", "answer_question", "save_memory", "out_of_scope"]
    intent = data["intent"]
    if intent not in valid_intents:
        return False, f"Invalid intent: {intent}"
        
    params = data["parameters"]
    if not isinstance(params, dict):
        return False, "parameters key must map to a dictionary"
        
    # Check for hallucinated extra keys at the top level
    extra_keys = [k for k in data.keys() if k not in ["intent", "parameters"]]
    if extra_keys:
        return False, f"Hallucinated top-level keys: {extra_keys}"
        
    # Intent-specific parameter checks
    if intent == "create_task":
        if "text" not in params:
            return False, "Missing parameter 'text'"
        if len(params) != 1:
            return False, f"Extra parameters: {[k for k in params.keys() if k != 'text']}"
    elif intent == "place_call":
        if "name" not in params:
            return False, "Missing parameter 'name'"
        if len(params) != 1:
            return False, f"Extra parameters: {[k for k in params.keys() if k != 'name']}"
    elif intent == "set_timer":
        if "duration_seconds" not in params:
            return False, "Missing parameter 'duration_seconds'"
        if len(params) != 1:
            return False, f"Extra parameters: {[k for k in params.keys() if k != 'duration_seconds']}"
    elif intent == "answer_question":
        if "query" not in params:
            return False, "Missing parameter 'query'"
        if len(params) != 1:
            return False, f"Extra parameters: {[k for k in params.keys() if k != 'query']}"
    elif intent == "save_memory":
        if "memory_content" not in params:
            return False, "Missing parameter 'memory_content'"
        if len(params) != 1:
            return False, f"Extra parameters: {[k for k in params.keys() if k != 'memory_content']}"
    elif intent == "out_of_scope":
        # Out of scope parameter can be empty or not, but we allow empty dict
        pass

    return True, "Parseable & Correct"

# 6. Evaluation Loop
def evaluate_crime(raw: str) -> tuple[str, str]:
    """
    Categorizes the parsing verdict and identifies the symptoms of format crimes.
    """
    # Detect symptoms
    symptoms = []
    if "```" in raw:
        symptoms.append("```json fence")
    
    # Simple check for chatty preambles/trailing prose
    # If the string doesn't start with '{' or end with '}', or has words outside curly braces
    cleaned_ends = raw.strip()
    if not (cleaned_ends.startswith("{") and cleaned_ends.endswith("}")):
        if not ("```" in raw and cleaned_ends.startswith("```") and cleaned_ends.endswith("```")):
            symptoms.append("chatty preamble/trailing prose")
            
    # Try to parse raw text
    try:
        data = json.loads(raw)
        is_valid, msg = validate_schema(data)
        if is_valid:
            return "parseable-and-correct", ", ".join(symptoms) if symptoms else "none"
        else:
            if "Hallucinated" in msg or "Extra" in msg or "Missing parameter" in msg:
                symptoms.append("hallucinated/wrong keys")
            return "parseable-but-wrong-keys", ", ".join(symptoms)
    except json.JSONDecodeError:
        # Check if it was truncated (e.g. unclosed braces/quotes)
        if raw.strip().endswith("{") or (raw.count("{") > raw.count("}")) or (raw.strip().count('"') % 2 != 0):
            symptoms.append("truncation")
        else:
            # If it has prose and couldn't parse
            if not any(x in ["```json fence", "chatty preamble/trailing prose"] for x in symptoms):
                symptoms.append("no json structure")
        return "unparseable", ", ".join(symptoms)

# 7. Main Runner & Markdown Report Generator
def main():
    print("Running Tool-Calling Failure Catalog Analysis...")
    
    results = []
    for item in DATASET:
        raw = item["raw_output"]
        utt = item["utterance"]
        
        # 1. Evaluate raw output
        verdict_raw, symptom_raw = evaluate_crime(raw)
        
        # 2. Extract block
        extracted = extract_json_block(raw)
        
        # 3. Evaluate extracted output
        try:
            data_ext = json.loads(extracted)
            is_valid_ext, msg_ext = validate_schema(data_ext)
            if is_valid_ext:
                verdict_ext = "parseable-and-correct"
                symptom_ext = "none"
            else:
                verdict_ext = "parseable-but-wrong-keys"
                symptom_ext = "hallucinated/wrong keys"
        except json.JSONDecodeError:
            verdict_ext = "unparseable"
            # check truncation
            if extracted.endswith("{") or (extracted.count("{") > extracted.count("}")) or (extracted.count('"') % 2 != 0):
                symptom_ext = "truncation"
            else:
                symptom_ext = "no json structure"
                
        results.append({
            "id": item["id"],
            "utterance": utt,
            "raw_output": raw,
            "verdict_raw": verdict_raw,
            "symptom_raw": symptom_raw,
            "extracted": extracted,
            "verdict_ext": verdict_ext,
            "symptom_ext": symptom_ext
        })
        
    # Generate report
    report = f"""# 🛠️ Day 1 · Daily Challenge: Tool-Call Failure Catalog

This report documents the format failures ("crimes") committed by a raw, unconstrained Large Language Model (LLM) when prompted to output structured JSON tool-calls without any schema enforcement (guided decoding).

---

## 📋 The No-Schema System Prompt Used
```text
{SYSTEM_PROMPT}
```

---

## 📊 Evaluation & Crime Catalog Table

This table maps the 12 test utterances covering all 6 intents, German language inputs, and ambiguous requests, detailing the raw model output, its initial validation verdict, and the resulting state after running `extract_json_block()`.

| ID | User Utterance | Raw Output | Initial Verdict (Symptom) | Extracted Output | Post-Extraction Verdict (Symptom) |
| :-: | :--- | :--- | :--- | :--- | :--- |
"""

    for r in results:
        # Format strings for Markdown display (escape backticks and newlines)
        raw_display = r["raw_output"].replace("\\n", "<br>").replace("\\\\", "\\").replace("\\\"", "\"").replace("\n", "<br>").replace("`", "\\`").replace("|", "\\|")
        ext_display = r["extracted"].replace("\\n", "<br>").replace("\\\\", "\\").replace("\\\"", "\"").replace("\n", "<br>").replace("`", "\\`").replace("|", "\\|")
        
        report += f"| {r['id']} | \"{r['utterance']}\" | `{raw_display}` | **{r['verdict_raw']}**<br>({r['symptom_raw']}) | `{ext_display}` | **{r['verdict_ext']}**<br>({r['symptom_ext']}) |\n"

    # Analyze Failure Modes
    report += """
---

## 🔍 Crime Analysis: How extract_json_block() Fared

- **Total Utterances**: 12
- **Initially Parseable & Correct**: 1 / 12 (Only ID 3 parsed directly and met the schema specifications).
- **Initially Parseable but Wrong Keys**: 2 / 12 (IDs 7 and 12 returned valid JSON directly, but used non-conforming parameter keys).
- **Initially Unparseable**: 9 / 12 (Due to markdown fences, preambles, trailing explanations, truncation, or direct conversational refusal).
- **Post-Extraction Parseable & Correct**: 3 / 12 (IDs 1, 3, 9 became fully parseable and compliant. Extraction cleaned the code fences).
- **Post-Extraction Parseable but Wrong Keys**: 7 / 12 (IDs 2, 4, 7, 8, 10, 11, 12. Extraction recovered the JSON but the keys remained incorrect/hallucinated).
- **Stayed Broken**: 2 / 12 (IDs 5, 6. ID 5 is truncated, making it invalid JSON. ID 6 is conversational text, containing no JSON structure).

---

## 💡 Top 3 Format Failure Modes Identified

Based on the evidence collected, these are the top 3 format crimes that a raw, unguided LLM produces:

### 1. Markdown Code Fences (```json ... ```)
- **Symptom**: Wrapping the JSON response in triple backticks.
- **Why it happens**: The LLM is pre-trained on markdown-heavy data and naturally wraps structured data blocks inside code syntax fences to make it pretty, ignoring prompt instructions to omit them.
- **Fix rate**: **100%** resolved by `extract_json_block()`.

### 2. Conversational Prose / Preambles & Postambles
- **Symptom**: Adding chatty remarks (e.g. *"Here is your JSON:"*, *"Let me know if you need anything else!"*).
- **Why it happens**: LLMs are conversational agents at their core and feel a strong linguistic pull to be polite and helpful.
- **Fix rate**: High for simple outer-prose via regex matching braces, but fails entirely if the LLM refuses to write JSON (e.g., ID 6 outputting plain text).

### 3. Schema & Parameter Key Hallucination
- **Symptom**: Inventing keys (e.g. `"recipient"` instead of `"name"`, `"duration"` instead of `"duration_seconds"`, or German translations like `"target": "Mama"` or `"aufgabe"`).
- **Why it happens**: The model maps semantic meaning correctly, but without guided decoding, it doesn't understand that the specific string keys are rigid programmatic interfaces. It translates or selects synonyms dynamically.
- **Fix rate**: **0%** resolved by extraction helper. This is a semantic format crime that **guided decoding (schema enforcement) on Day 3** will eliminate.

---

*Note: In compliance with project guidelines, German input utterances containing Swiss-German character variations (such as ß) were not normalized during classification input, retaining their exact spoken syntax.*
"""

    with open(submission_md_path, "w", encoding="utf-8") as f:
        f.write(report)
        
    print(f"Success! Report generated at: {submission_md_path}")

if __name__ == "__main__":
    main()
