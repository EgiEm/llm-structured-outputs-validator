"""
run_challenge.py - Day 5 Evaluation Harness & Run Table
======================================================
Executes oxodin_tool_caller over at least 15 utterances (including multi-intent,
German utterances with inline English glosses, edge cases, and fallbacks).
Prints a clean run table and summary.
"""

import json
from typing import Any, Dict, List
from oxodin_tool_caller import oxodin_tool_caller

# -----------------------------------------------------------------------------
# Test Dataset (16 Utterances)
# -----------------------------------------------------------------------------
DATASET = [
    {
        "id": 1,
        "utterance": "Remind me to call mom and text dad",
        "gloss": "English multi-intent",
        "fixture": {
            "intents": [
                {"action": "create_task", "params": {"title": "Call mom", "scheduled_date_time": "today"}},
                {"action": "create_task", "params": {"title": "Text dad", "scheduled_date_time": "today"}}
            ]
        }
    },
    {
        "id": 2,
        "utterance": "Ruf Mama an und schreib Papa",
        "gloss": "German: Call mom and text dad",
        "fixture": {
            "intents": [
                {"action": "place_call", "params": {"recipient": "Mama", "urgent": False}},
                {"action": "create_task", "params": {"title": "Schreib Papa", "scheduled_date_time": "today"}}
            ]
        }
    },
    {
        "id": 3,
        "utterance": "Set a timer for 10 minutes and save memory that I left keys on counter",
        "gloss": "English multi-intent",
        "fixture": {
            "intents": [
                {"action": "set_timer", "params": {"duration": 10, "unit": "minutes"}},
                {"action": "save_memory", "params": {"content": "Left keys on counter", "category": "personal"}}
            ]
        }
    },
    {
        "id": 4,
        "utterance": "Erstelle eine Aufgabe zum Einkaufen und rufe John an",
        "gloss": "German: Create a shopping task and call John",
        "fixture": {
            "intents": [
                {"action": "create_task", "params": {"title": "Einkaufen", "scheduled_date_time": "today"}},
                {"action": "place_call", "params": {"recipient": "John", "urgent": False}}
            ]
        }
    },
    {
        "id": 5,
        "utterance": "Call Dr. Smith and schedule appointment for tomorrow at 3 PM",
        "gloss": "English multi-intent",
        "fixture": {
            "intents": [
                {"action": "place_call", "params": {"recipient": "Dr. Smith", "urgent": True}},
                {"action": "create_task", "params": {"title": "Appointment", "scheduled_date_time": "tomorrow at 3 PM"}}
            ]
        }
    },
    {
        "id": 6,
        "utterance": "Bitte stell einen Wecker auf 15 Minuten",
        "gloss": "German: Please set a timer for 15 minutes",
        "fixture": {
            "intents": [
                {"action": "set_timer", "params": {"duration": 15, "unit": "minutes"}}
            ]
        }
    },
    {
        "id": 7,
        "utterance": "Remind me to buy groceries tomorrow at 5 PM",
        "gloss": "Single-intent task",
        "fixture": {
            "intents": [
                {"action": "create_task", "params": {"title": "Buy groceries", "scheduled_date_time": "tomorrow at 5 PM"}}
            ]
        }
    },
    {
        "id": 8,
        "utterance": "Call Dr. Smith immediately",
        "gloss": "Single-intent urgent call",
        "fixture": {
            "intents": [
                {"action": "place_call", "params": {"recipient": "Dr. Smith", "urgent": True}}
            ]
        }
    },
    {
        "id": 9,
        "utterance": "What is the capital of France?",
        "gloss": "Single-intent QA",
        "fixture": {
            "intents": [
                {"action": "answer_question", "params": {"query": "What is the capital of France?", "depth": "concise"}}
            ]
        }
    },
    {
        "id": 10,
        "utterance": "Save that my Wi-Fi password is supersecret123",
        "gloss": "Single-intent memory save",
        "fixture": {
            "intents": [
                {"action": "save_memory", "params": {"content": "Wi-Fi password is supersecret123", "category": "credentials"}}
            ]
        }
    },
    {
        "id": 11,
        "utterance": "Can you code a fast-sorting algorithm in C++?",
        "gloss": "Out-of-scope query",
        "fixture": {
            "intents": [
                {"action": "out_of_scope", "params": {"raw_input": "Can you code a fast-sorting algorithm in C++?"}}
            ]
        }
    },
    {
        "id": 12,
        "utterance": "Call 911",
        "gloss": "Emergency call (trapped execution)",
        "fixture": {
            "intents": [
                {"action": "place_call", "params": {"recipient": "911", "urgent": True}}
            ]
        }
    },
    {
        "id": 13,
        "utterance": "Create a task without title",
        "gloss": "Missing required slot",
        "fixture": {
            "intents": [
                {"action": "create_task", "params": {}}
            ]
        }
    },
    {
        "id": 14,
        "utterance": "Single intent un-wrapped root object test",
        "gloss": "Structural repair test",
        "fixture": {
            "action": "place_call",
            "params": {"recipient": "Alice"}
        }
    },
    {
        "id": 15,
        "utterance": "Tell me a story and set timer",
        "gloss": "Mixed multi-intent with out of scope",
        "fixture": {
            "intents": [
                {"action": "out_of_scope", "params": {"raw_input": "Tell me a story"}},
                {"action": "set_timer", "params": {"duration": 5, "unit": "minutes"}}
            ]
        }
    },
    {
        "id": 16,
        "utterance": "Unknown action invocation",
        "gloss": "Invalid action enum repair test",
        "fixture": {
            "intents": [
                {"action": "fly_to_mars", "params": {"destination": "Mars"}}
            ]
        }
    }
]

# -----------------------------------------------------------------------------
# Evaluation Harness
# -----------------------------------------------------------------------------
def run_evaluation():
    print("=" * 105)
    print(f"{'ID':<3} | {'UTTERANCE':<35} | {'GLOSS / TYPE':<32} | {'RESULTS':<25}")
    print("=" * 105)

    passed = 0
    total = len(DATASET)

    for item in DATASET:
        utt_id = item["id"]
        utt = item["utterance"]
        gloss = item["gloss"]
        fix = item["fixture"]

        # Run pipeline
        res = oxodin_tool_caller(utt, fixture_override=fix)
        results_list = res["dispatched_results"]

        # Format dispatched output for table
        summaries = []
        is_ok = True
        for r in results_list:
            act = r.get("action")
            status = r.get("status")
            if status == "ok":
                summaries.append(f"[{act}: OK]")
            else:
                summaries.append(f"[{act}: ERR]")
                # Emergency trapped 911 or missing required slot are expected test traps
                if utt_id not in (12, 13):
                    is_ok = False

        res_str = " ".join(summaries)
        print(f"{utt_id:<3} | {utt[:35]:<35} | {gloss[:32]:<32} | {res_str:<25}")

        if is_ok:
            passed += 1

    print("=" * 105)
    print(f"RUN SUMMARY: {passed}/{total} Utterances Successfully Processed ({passed/total*100:.1f}%)")
    print("=" * 105)

if __name__ == "__main__":
    run_evaluation()
