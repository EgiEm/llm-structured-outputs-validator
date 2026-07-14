# 🛠️ Day 1 · Daily Challenge: Tool-Call Failure Catalog

This report documents the format failures ("crimes") committed by a raw, unconstrained Large Language Model (LLM) when prompted to output structured JSON tool-calls without any schema enforcement (guided decoding).

---

## 📋 The No-Schema System Prompt Used
```text
You are an AI routing assistant. You must receive user utterances and output a single JSON object.
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
}
```

---

## 📊 Evaluation & Crime Catalog Table

This table maps the 12 test utterances covering all 6 intents, German language inputs, and ambiguous requests, detailing the raw model output, its initial validation verdict, and the resulting state after running `extract_json_block()`.

| ID | User Utterance | Raw Output | Initial Verdict (Symptom) | Extracted Output | Post-Extraction Verdict (Symptom) |
| :-: | :--- | :--- | :--- | :--- | :--- |
| 1 | "Remind me to buy groceries tomorrow at 5 PM" | `\`\`\`json<br>{<br>  "intent": "create_task",<br>  "parameters": {<br>    "text": "buy groceries tomorrow at 5 PM"<br>  }<br>}<br>\`\`\`` | **unparseable**<br>(```json fence) | `{<br>  "intent": "create_task",<br>  "parameters": {<br>    "text": "buy groceries tomorrow at 5 PM"<br>  }<br>}` | **parseable-and-correct**<br>(none) |
| 2 | "Call Dr. Smith immediately" | `Sure, here is the routing information for your request:<br>{<br>  "intent": "place_call",<br>  "parameters": {<br>    "recipient": "Dr. Smith"<br>  }<br>}<br>Let me know if you need anything else!` | **unparseable**<br>(chatty preamble/trailing prose) | `{<br>  "intent": "place_call",<br>  "parameters": {<br>    "recipient": "Dr. Smith"<br>  }<br>}` | **parseable-but-wrong-keys**<br>(hallucinated/wrong keys) |
| 3 | "Set a timer for 45 minutes" | `{<br>  "intent": "set_timer",<br>  "parameters": {<br>    "duration_seconds": 2700<br>  }<br>}` | **parseable-and-correct**<br>(none) | `{<br>  "intent": "set_timer",<br>  "parameters": {<br>    "duration_seconds": 2700<br>  }<br>}` | **parseable-and-correct**<br>(none) |
| 4 | "What is the distance between the Earth and the Moon?" | `\`\`\`json<br>{<br>  "intent": "answer_question",<br>  "parameters": {<br>    "query": "What is the distance between the Earth and the Moon?"<br>  },<br>  "confidence": 0.98<br>}<br>\`\`\`` | **unparseable**<br>(```json fence) | `{<br>  "intent": "answer_question",<br>  "parameters": {<br>    "query": "What is the distance between the Earth and the Moon?"<br>  },<br>  "confidence": 0.98<br>}` | **parseable-but-wrong-keys**<br>(hallucinated/wrong keys) |
| 5 | "Remember that my sister's birthday is October 12th" | `{<br>  "intent": "save_memory",<br>  "parameters": {<br>    "memory_content": "sister's birthday is October 12` | **unparseable**<br>(chatty preamble/trailing prose, truncation) | `{<br>  "intent": "save_memory",<br>  "parameters": {<br>    "memory_content": "sister's birthday is October 12` | **unparseable**<br>(truncation) |
| 6 | "Can you generate a python script to sort a list?" | `I cannot help you write python scripts. I can only route task management, calling, and timer commands.` | **unparseable**<br>(chatty preamble/trailing prose) | `I cannot help you write python scripts. I can only route task management, calling, and timer commands.` | **unparseable**<br>(no json structure) |
| 7 | "Ruf Mama an" | `{<br>  "intent": "place_call",<br>  "parameters": {<br>    "target": "Mama"<br>  }<br>}` | **parseable-but-wrong-keys**<br>(hallucinated/wrong keys) | `{<br>  "intent": "place_call",<br>  "parameters": {<br>    "target": "Mama"<br>  }<br>}` | **parseable-but-wrong-keys**<br>(hallucinated/wrong keys) |
| 8 | "Erstelle eine Aufgabe zum Einkaufen" | `\`\`\`json<br>{<br>  "intent": "create_task",<br>  "parameters": {<br>    "aufgabe": "Einkaufen"<br>  }<br>}<br>\`\`\`` | **unparseable**<br>(```json fence) | `{<br>  "intent": "create_task",<br>  "parameters": {<br>    "aufgabe": "Einkaufen"<br>  }<br>}` | **parseable-but-wrong-keys**<br>(hallucinated/wrong keys) |
| 9 | "Can you call that task organizer?" | `\`\`\`json<br>{<br>  "intent": "place_call",<br>  "parameters": {<br>    "name": "task organizer"<br>  }<br>}<br>\`\`\`` | **unparseable**<br>(```json fence) | `{<br>  "intent": "place_call",<br>  "parameters": {<br>    "name": "task organizer"<br>  }<br>}` | **parseable-and-correct**<br>(none) |
| 10 | "Should I call John or set a reminder?" | `\`\`\`json<br>{<br>  "intent": "out_of_scope",<br>  "parameters": {<br>    "text": "Should I call John or set a reminder?"<br>  },<br>  "ambiguity": true<br>}<br>\`\`\`` | **unparseable**<br>(```json fence) | `{<br>  "intent": "out_of_scope",<br>  "parameters": {<br>    "text": "Should I call John or set a reminder?"<br>  },<br>  "ambiguity": true<br>}` | **parseable-but-wrong-keys**<br>(hallucinated/wrong keys) |
| 11 | "Remind me to call dad at 6pm" | `Here is the requested tool call structure:<br>\`\`\`json<br>{<br>  "intent": "create_task",<br>  "parameters": {<br>    "task_description": "call dad at 6pm"<br>  }<br>}<br>\`\`\`` | **unparseable**<br>(```json fence, chatty preamble/trailing prose) | `{<br>  "intent": "create_task",<br>  "parameters": {<br>    "task_description": "call dad at 6pm"<br>  }<br>}` | **parseable-but-wrong-keys**<br>(hallucinated/wrong keys) |
| 12 | "Set a timer for 10 minutes" | `{<br>  "intent": "set_timer",<br>  "parameters": {<br>    "duration": "10 minutes"<br>  }<br>}<br>Note that duration is parsed as a string.` | **unparseable**<br>(chatty preamble/trailing prose) | `{<br>  "intent": "set_timer",<br>  "parameters": {<br>    "duration": "10 minutes"<br>  }<br>}` | **parseable-but-wrong-keys**<br>(hallucinated/wrong keys) |

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
