# 🛠️ Structured LLM Outputs & Tool-Call Validator

This repository tracks assignments and daily challenges focusing on structured LLM outputs, tool-calling integration, schema enforcement, and guided decoding.

## 📁 Repository Structure

The challenges are organized by day:
* `day 1/` - Tool-Calling with an LLM: Raw JSON outputs, regex parsing, and categorization of format failure modes ("format crimes").
* `day 2/` - The Schema Gate: Implementation of a robust JSON-Schema tool-call validator and repair pipeline with strict nested type checking and failure path reporting.
* `day 3/` - Schema-Locked Classifier: Locked classifier behind JSON Schema using guided decoding, compared unguided vs guided performance, and documented semantic errors on ambiguous inputs.
* `day 4/` - The Dispatcher: Implementation of a deterministic dispatcher layer routing validated tool calls to stub handlers while enforcing slot contracts and gracefully trapping execution errors.
* `day 5/` - v3 Tool-Calling with an LLM: Multi-Intent & the Model Card: End-to-end multi-intent pipeline with array schema validation, repair policies, dispatch execution over 16 test utterances (including German and multi-intents), model card, and Week 5 handoff notes.

---

## 📅 Daily Progress Log

### Day 1: Tool-Call Failure Catalog
* **Objective**: Evaluate formatting issues that arise when asking a raw LLM to output structured JSON without guided decoding constraints.
* **Deliverables**:
  * [run_challenge.py](day%201/run_challenge.py): A Python runner simulating unconstrained model outputs over 12 test utterances covering 6 intents.
  * [submission.md](day%201/submission.md): Analysis of the format crimes (code fences, preambles, and schema hallucinations) before and after using an extraction helper (`extract_json_block`).

### Day 2: The Schema Gate — Validate & Repair Tool Calls
* **Objective**: Build a from-scratch JSON-Schema validator that reports the exact key path of every failure, handles nested slots typing, and integrates a deterministic repair pass to pre-clean LLM outputs.
* **Deliverables**:
  * [run_challenge.py](day%202/run_challenge.py): A hardened validator (`validate_tool_call`), a deterministic repair helper (`repair`), and a suite of 19 hand-crafted torture tests.
  * [submission.md](day%202/submission.md): A detailed report documenting the validator code, the repair policy table, the 19 torture tests, and the deterministic test run logs.

### Day 3: Schema-Locked Classifier — Before vs After
* **Objective**: Lock the classifier output format behind a JSON Schema, evaluate syntax/format compliance, and prove that guided decoding guarantees structure/shape but does not prevent semantic classification errors.
* **Deliverables**:
  * [run_challenge.py](day%203/run_challenge.py): Evaluation script comparing free generation vs guided decoding across 15 test utterances (including German and ambiguous queries).
  * [submission.md](day%203/submission.md): Comparison table (Parse % / Valid %), evaluation results, and analysis of 3 schema-valid but semantically incorrect cases.

### Day 4: The Dispatcher — From Validated Call to Real Action
* **Objective**: Build a robust, deterministic routing layer that processes validated calls, enforces slot-level contracts (required fields and unknown slots), resolves defaults, and traps runtime exceptions safely.
* **Deliverables**:
  * [run_challenge.py](day%204/run_challenge.py): Python evaluation runner mapping 17 test cases through a slot-contract argument validation engine to registered executable handlers.
  * [submission.md](day%204/submission.md): Comprehensive test log matrix showing successful execution paths and fallback payloads for all degradation triggers (unknown intents, missing slots, unknown keys, and code block crashes).

### Day 5: v3 Tool-Calling with an LLM — Multi-Intent & the Model Card
* **Objective**: Ship v3 — a multi-intent, schema-locked, dispatching LLM tool caller supporting multi-action single/compound queries, array validation, repair policies, comprehensive model card, and Week 5 handoff gaps.
* **Deliverables**:
  * [oxodin_tool_caller.py](day%205/oxodin_tool_caller.py): Reusable v3 pipeline module handling single and multi-intent array schemas, safety net validator, repair logic, and dispatcher.
  * [run_challenge.py](day%205/run_challenge.py): Python evaluation harness testing 16 utterances (including 5 multi-intent, 3 German utterances with glosses, single intents, and trapped error cases).
  * [submission.md](day%205/submission.md): Complete submission containing the v3 Model Card (Schema, Repair Policy, Dispatch Table, Latency, Known Failure Modes) and Week 5 Handoff Note.




