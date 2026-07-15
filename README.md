# 🛠️ Structured LLM Outputs & Tool-Call Validator

This repository tracks assignments and daily challenges focusing on structured LLM outputs, tool-calling integration, schema enforcement, and guided decoding.

## 📁 Repository Structure

The challenges are organized by day:
* `day 1/` - Tool-Calling with an LLM: Raw JSON outputs, regex parsing, and categorization of format failure modes ("format crimes").
* `day 2/` - The Schema Gate: Implementation of a robust JSON-Schema tool-call validator and repair pipeline with strict nested type checking and failure path reporting.

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

