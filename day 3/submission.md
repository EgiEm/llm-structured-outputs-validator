# 🛠️ Day 3 · Daily Challenge: Schema-Locked Classifier — Before vs After

This report documents the difference between unguided free generation and JSON Schema-locked guided decoding. It proves how guided decoding guarantees structural shape, while clarifying why it does not guarantee semantic truth.

---

## 💻 Day 3 JSON Schema Specification

The model's output is locked behind this strict schema:
```json
{
  "type": "object",
  "required": ["intent", "confidence"],
  "properties": {
    "intent": {
      "type": "string",
      "enum": ["create_task", "place_call", "answer_question", "save_memory", "set_timer", "out_of_scope"]
    },
    "confidence": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0
    }
  },
  "additionalProperties": false
}
```

---

## 📊 Before vs After Comparison Table

Below is the comparison of parsing success and validation pass rates across the 15 test utterances.

| Mode | Parse Success Rate (%) | Validator Pass Rate (%) |
| :--- | :---: | :---: |
| **No Schema (Free Generation)** | 53.3% | 26.7% |
| **Guided Decoding (Schema-Locked)** | 100.0% | 100.0% |

### Verdict & Discussion
Guided decoding achieves a **100% schema-valid rate**. Invalid formats, markdown fences, conversational preambles, and parameter/enum hallucinations are mathematically eliminated at the generation level.

---

## 🧪 Detailed Evaluation Table (15 Utterances)

| ID | User Utterance | Unguided Output (Free) | Unguided Valid | Guided Output | Guided Valid |
| :-: | :--- | :--- | :-: | :--- | :-: |
| 1 | "Remind me to buy groceries tomorrow at 5 PM" | `{"intent": "create_task", "confidence": 0.95}` | **PASS** | `{"intent": "create_task", "confidence": 0.95}` | **PASS** |
| 2 | "Call Dr. Smith immediately" | `Sure, here is the result: {"intent": "place_call", "confidence": 0.98}` | **FAIL** | `{"intent": "place_call", "confidence": 0.98}` | **PASS** |
| 3 | "Set a timer for 45 minutes" | `\`\`\`json {"intent": "set_timer", "confidence": 0.90} \`\`\`` | **FAIL** | `{"intent": "set_timer", "confidence": 0.90}` | **PASS** |
| 4 | "What is the distance between the Earth and the Moon?" | `\`\`\`json {"intent": "answer_question", "confidence": 0.95} \`\`\`` | **FAIL** | `{"intent": "answer_question", "confidence": 0.95}` | **PASS** |
| 5 | "Remember that my sister's birthday is October 12th" | `{"intent": "save_memory", "confidence": "high"}` | **FAIL** | `{"intent": "save_memory", "confidence": 0.88}` | **PASS** |
| 6 | "Can you generate a python script to sort a list?" | `I cannot help you write python scripts.` | **FAIL** | `{"intent": "out_of_scope", "confidence": 0.99}` | **PASS** |
| 7 | "Ruf Mama an" | `{"intent": "place_call", "confidence": 0.90}` | **PASS** | `{"intent": "place_call", "confidence": 0.90}` | **PASS** |
| 8 | "Erstelle eine Aufgabe zum Einkaufen" | `{"intent": "erstellen_aufgabe", "confidence": 0.85}` | **FAIL** | `{"intent": "create_task", "confidence": 0.85}` | **PASS** |
| 9 | "Bitte stell einen Wecker auf 10 Minuten" | `Stelle Wecker ein: {"intent": "set_timer", "confidence": 0.90}` | **FAIL** | `{"intent": "set_timer", "confidence": 0.90}` | **PASS** |
| 10 | "Can you call that task organizer?" | `\`\`\`json {"intent": "place_call", "confidence": 0.75} \`\`\`` | **FAIL** | `{"intent": "place_call", "confidence": 0.78}` | **PASS** |
| 11 | "Should I call John or set a reminder?" | `{"intent": "out_of_scope", "confidence": 0.65}` | **PASS** | `{"intent": "place_call", "confidence": 0.92}` | **PASS** |
| 12 | "Set something up for mom" | `{"intent": "setup_for_mom", "confidence": 0.80}` | **FAIL** | `{"intent": "create_task", "confidence": 0.85}` | **PASS** |
| 13 | "Tell me a joke" | `I cannot do that.` | **FAIL** | `{"intent": "out_of_scope", "confidence": 0.90}` | **PASS** |
| 14 | "Save that we need to buy milk tomorrow" | `{"intent": "save_memory", "confidence": 0.90}` | **PASS** | `{"intent": "save_memory", "confidence": 0.90}` | **PASS** |
| 15 | "Call 911" | `{"intent": "make_call", "confidence": 0.99}` | **FAIL** | `{"intent": "place_call", "confidence": 0.99}` | **PASS** |

---

## 🔍 Finding the Gap: Schema-Valid but Semantically Wrong Cases

Guided decoding enforces the **shape/syntax** of the contract, but it does **not** guarantee **semantic truth** or correct classification. When presented with ambiguous inputs, the model is forced to choose one of the enum values, resulting in valid JSON for the wrong intent.

### Case 1: ID 10
* **Utterance**: `"Can you call that task organizer?"`
* **Guided Output**: `{"intent": "place_call", "confidence": 0.78}`
* **Semantic Error**: The user wanted to open or launch their "Task Organizer" software/app, which should be `out_of_scope` (or trigger an app launcher). Because the utterance contains the verb "call", the model falsely routed it to the phone call intent (`place_call`).
* **Fix**: Provide few-shot examples in the prompt to show that references to software/applications map to `out_of_scope`, even if active verbs like "call" or "run" are present.

### Case 2: ID 11
* **Utterance**: `"Should I call John or set a reminder?"`
* **Guided Output**: `{"intent": "place_call", "confidence": 0.92}`
* **Semantic Error**: The user was asking a conversational question for advice or options (which is `out_of_scope`), not commanding the system to initiate an action. Because the model was locked into selecting an intent, it picked `place_call` because of the words "call John".
* **Fix**: Include few-shot examples in the system instructions illustrating that advice-seeking, multi-choice queries, or conversational check-ins are categorized as `out_of_scope`.

### Case 3: ID 12
* **Utterance**: `"Set something up for mom"`
* **Guided Output**: `{"intent": "create_task", "confidence": 0.85}`
* **Semantic Error**: The request is extremely vague and ambiguous. It could refer to creating a reminder, scheduling a calendar task, or calling mom. The model was forced to guess and picked `create_task`, which could be wrong if the user intended to call.
* **Fix**: Implement a confidence-threshold check in the orchestrator: if confidence is below a certain margin, or if the model output indicates ambiguity, trigger a follow-up clarification question rather than executing the guess.

---

### Conclusion
Guided decoding **guarantees syntax, not correctness**. It guarantees that the JSON structure can be programmatically parsed and validated safely, but the validation of semantic intent must still be handled via system prompts, few-shot examples, and application-level business logic.
