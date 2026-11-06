#!/usr/bin/env python3
"""Reference deterministic oracle for wizard-bench.

This oracle reads scenario.json and questions, answering each question
with the answer of hidden requirements whose keywords overlap the question
(stopword-filtered token overlap above threshold), else out_of_scope_answer.

NOTE: This is a deterministic, low-fidelity stand-in for testing and CI.
An LLM oracle (ReqElicitGym style) is recommended in real benchmark runs
via --oracle-command.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import sys
from typing import Any

STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both",
    "but", "by", "can", "could", "did", "do", "does", "doing", "down", "during", "each", "few",
    "for", "from", "further", "had", "has", "have", "having", "he", "her", "here", "hers", "him",
    "his", "how", "i", "if", "in", "into", "is", "it", "its", "me", "more", "most", "my", "no",
    "nor", "not", "of", "off", "on", "once", "only", "or", "other", "our", "out", "over", "own",
    "same", "she", "should", "so", "some", "such", "than", "that", "the", "their", "them", "then",
    "there", "these", "they", "this", "those", "through", "to", "too", "under", "until", "up",
    "very", "was", "we", "were", "what", "when", "where", "which", "while", "who", "whom", "why",
    "with", "would", "you", "your", "tell", "please", "want", "like", "need", "specify", "question",
    "questions"
}


def tokenize(text: str) -> set[str]:
    words = re.findall(r"[a-zA-Z0-9_]+", text.lower())
    return {w for w in words if len(w) > 1 and w not in STOPWORDS}


def token_match(t1: str, t2: str) -> bool:
    if t1 == t2:
        return True
    if len(t1) >= 4 and len(t2) >= 4:
        if t1.startswith(t2) or t2.startswith(t1):
            return True
        stem1 = t1.rstrip("s").rstrip("es").rstrip("ed").rstrip("ing")
        stem2 = t2.rstrip("s").rstrip("es").rstrip("ed").rstrip("ing")
        if len(stem1) >= 3 and stem1 == stem2:
            return True
    return False


def extract_questions(content: str) -> list[str]:
    lines = content.splitlines()
    questions: list[str] = []
    current_q: list[str] = []

    for line in lines:
        stripped = line.strip()
        m = re.match(r"^(?:\d+[\.\)]|[-*])\s+(.*)", stripped)
        if m:
            if current_q:
                questions.append(" ".join(current_q))
                current_q = []
            text = m.group(1).strip()
            if text:
                current_q.append(text)
        elif current_q and stripped and not stripped.startswith("#"):
            current_q.append(stripped)

    if current_q:
        questions.append(" ".join(current_q))

    if not questions:
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                questions.append(stripped)

    return questions if questions else [content.strip()] if content.strip() else []


def answer_single_question(question: str, scenario: dict[str, Any], threshold: int = 1) -> str:
    """Pick the requirement sharing the most distinctive tokens with the question.

    Tokens are weighted by inverse requirement frequency, so words present in every
    requirement (e.g. the product noun) cannot decide the match on their own.
    """
    q_tokens = tokenize(question)
    requirements = scenario.get("hidden_requirements", [])
    req_tokens = [tokenize(" ".join([req.get("text", ""), *req.get("keywords", [])])) for req in requirements]
    count = len(requirements)
    best_req = None
    best_score = 0.0
    best_hits = 0
    for req, tokens in zip(requirements, req_tokens):
        score = 0.0
        hits = 0
        for qt in q_tokens:
            matched = {rt for rt in tokens if token_match(qt, rt)}
            if not matched:
                continue
            frequency = sum(1 for other in req_tokens if any(token_match(qt, rt) for rt in other))
            if frequency >= count > 1:
                continue
            hits += 1
            score += math.log((count + 1) / frequency)
        if score > best_score:
            best_score, best_req, best_hits = score, req, hits
    if best_hits >= threshold and best_req is not None:
        return str(best_req.get("answer", ""))
    return str(scenario.get("out_of_scope_answer", "Out of scope."))


def answer_questions(content: str, scenario: dict[str, Any], threshold: int = 1) -> str:
    questions = extract_questions(content)
    if not questions:
        return str(scenario.get("out_of_scope_answer", "Out of scope."))
    answers = [answer_single_question(q, scenario, threshold=threshold) for q in questions]
    if len(answers) == 1:
        return answers[0]
    return "\n\n".join(f"{i}. {ans}" for i, ans in enumerate(answers, 1))


def main() -> int:
    parser = argparse.ArgumentParser(description="Deterministic reference oracle for wizard-bench")
    parser.add_argument("positional_args", nargs="*", help="[scenario_file] [questions_file] [transcript_file]")
    parser.add_argument("--scenario", "-s", help="Path to scenario.json")
    parser.add_argument("--questions", "-q", help="Path to questions.md")
    parser.add_argument("--transcript", "-t", help="Path to transcript.md")
    parser.add_argument("--threshold", type=int, default=1, help="Keyword overlap threshold (default: 1)")

    args = parser.parse_args()

    scenario_path = args.scenario
    questions_path = args.questions

    pos = args.positional_args
    # Detect scenario file among positional arguments if not explicitly passed
    if not scenario_path and pos:
        for p_str in pos:
            p = Path(p_str)
            if p.is_file():
                try:
                    data = json.loads(p.read_text(encoding="utf-8"))
                    if isinstance(data, dict) and "hidden_requirements" in data:
                        scenario_path = p_str
                        break
                except Exception:
                    pass
        if not scenario_path:
            scenario_path = pos[0]

    if not questions_path and pos:
        for p_str in pos:
            if p_str != scenario_path:
                questions_path = p_str
                break

    if not scenario_path:
        sys.stderr.write("Error: scenario file is required (via positional or --scenario)\n")
        return 1

    try:
        scenario_data = json.loads(Path(scenario_path).read_text(encoding="utf-8"))
    except OSError as exc:
        sys.stderr.write(f"Error reading scenario file: {exc}\n")
        return 1
    except json.JSONDecodeError as exc:
        sys.stderr.write(f"Error parsing scenario JSON: {exc}\n")
        return 1

    content = ""
    if questions_path and questions_path != "-":
        p = Path(questions_path)
        if p.is_file():
            content = p.read_text(encoding="utf-8")
    if not content and not sys.stdin.isatty():
        content = sys.stdin.read()

    output = answer_questions(content, scenario_data, threshold=args.threshold)
    sys.stdout.write(output + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
