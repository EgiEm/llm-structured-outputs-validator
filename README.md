# Brigada Assignments: Week 4

This repository tracks assignments and daily challenges completed during Week 4 of the Brigada Developer Internship. The core focus of this week is structured LLM outputs, tool-calling integration, schema enforcement, and guided decoding.

## 📁 Repository Structure

The challenges are organized by day:
* `day 1/` - Tool-Calling with an LLM: Raw JSON outputs, regex parsing, and categorization of format failure modes ("format crimes").

---

## 📅 Daily Progress Log

### Day 1: Tool-Call Failure Catalog
* **Objective**: Evaluate formatting issues that arise when asking a raw LLM to output structured JSON without guided decoding constraints.
* **Deliverables**:
  * [run_challenge.py](day%201/run_challenge.py): A Python runner simulating unconstrained model outputs over 12 test utterances covering 6 intents.
  * [submission.md](day%201/submission.md): Analysis of the format crimes (code fences, preambles, and schema hallucinations) before and after using an extraction helper (`extract_json_block`).
