"""Core study agent logic using Gemini with built-in Google Search grounding."""

from dataclasses import dataclass, field
from typing import Optional
import json
from . import llm


@dataclass
class Trace:
    steps: list = field(default_factory=list)

    def add(self, phase: str, prompt: str, result: str):
        self.steps.append({"phase": phase, "prompt": prompt[:200], "result": result[:500]})


def plan(topic: str, notes: str, trace: Trace) -> list[str]:
    prompt = f"""Break the topic "{topic}" into 3-5 ordered subtopics for study.
Additional context from user: {notes or "None provided"}

Return ONLY a JSON array of strings, e.g. ["Subtopic 1", "Subtopic 2", "Subtopic 3"]"""
    result = llm.call("You are a curriculum designer. Plan a study path.", prompt, temperature=0.5)
    trace.add("plan", prompt, result)

    # Clean and parse
    text = result.strip().removeprefix("```json").removesuffix("```").strip()
    try:
        subtopics = json.loads(text)
    except json.JSONDecodeError:
        lines = [l.strip().strip('"') for l in text.split("\n") if l.strip().startswith('"')]
        subtopics = lines if lines else [text.strip().strip("[]\"' ")]
    return subtopics if isinstance(subtopics, list) else [text]


def research(subtopic: str, trace: Trace) -> str:
    prompt = f"""Research the subtopic "{subtopic}" using Google Search. Provide a concise, well-structured summary covering:
1. Key concepts and definitions
2. Important details, examples, and facts
3. Any formulas, dates, or notable figures if relevant

Keep it to 3-5 paragraphs. Use clear headings."""
    result = llm.call(
        "You are a research assistant. Search the web and summarize information clearly.",
        prompt,
    )
    trace.add("research", prompt, result)
    return result


def synthesize(topic: str, subtopics: list[str], research_results: dict[str, str], trace: Trace) -> str:
    sections = "\n\n".join(
        f"## {st}\n{research_results[st]}" for st in subtopics
    )
    prompt = f"""Synthesize the following research on "{topic}" into a comprehensive, readable study guide.

Research sections:
{sections}

Write a cohesive study guide with:
1. A brief introduction
2. Each subtopic as a clear section with key takeaways
3. A summary/conclusion tying everything together

Use clear language suitable for a student."""
    result = llm.call(
        "You are an expert educator creating study materials.",
        prompt,
    )
    trace.add("synthesize", prompt, result)
    return result


def generate_quiz(topic: str, study_guide: str, count: int = 5, trace: Optional[Trace] = None) -> list[dict]:
    prompt = f"""Based on this study guide about "{topic}", generate {count} multiple-choice quiz questions.

Study guide:
{study_guide[:3000]}

Return ONLY a JSON array of objects with format:
[
  {{
    "question": "Question text?",
    "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
    "correct": 0,
    "explanation": "Why this answer is correct"
  }}
]

correct is the 0-based index of the right answer."""
    result = llm.call(
        "You are a quiz generator. Create fair, educational multiple-choice questions.",
        prompt,
        temperature=0.8,
    )
    if trace:
        trace.add("quiz", prompt, result)

    text = result.strip().removeprefix("```json").removesuffix("```").strip()
    try:
        questions = json.loads(text)
    except json.JSONDecodeError:
        questions = []
    return questions if isinstance(questions, list) else []


def adapt(wrong_answers: list[dict], study_guide: str, trace: Trace) -> str:
    questions_text = "\n".join(
        f"Q: {item['question']}\nCorrect: {item['correct_answer']}\nYour answer: {item['user_answer']}"
        for item in wrong_answers
    )
    prompt = f"""The student got these questions wrong:

{questions_text}

Based on the study guide below, create a focused re-study section that:
1. Re-explains the misunderstood concepts
2. Provides additional examples
3. Highlights the most important points the student missed

Study guide for reference:
{study_guide[:2000]}"""
    result = llm.call(
        "You are a tutor helping a student learn from their mistakes.",
        prompt,
        temperature=0.6,
    )
    trace.add("adapt", prompt, result)
    return result


def answer_question(question: str, guide: str, history: list[dict]) -> str:
    ctx = f"""You are a tutor. Answer the student's question based on this study guide.

Study guide:
{guide[:3000]}

Conversation so far:
{chr(10).join(f"Student: {m['q']}\nTutor: {m['a']}" for m in history[-4:])}

Student: {question}"""
    result = llm.call(
        "You are a helpful tutor. Answer concisely and reference the study guide.",
        ctx,
        temperature=0.4,
    )
    return result


def cheat_sheet(guide: str, topic: str) -> str:
    prompt = f"""Condense this study guide on "{topic}" into a one-page cheat sheet.

Include:
- 3-5 most important concepts (1 line each)
- Key formulas / definitions
- A quick reference table if applicable
- Top 3 takeaways

Keep it extremely concise — bullet points only. Aim for under 300 words.

Study guide:
{guide[:4000]}"""
    result = llm.call(
        "You are a summary expert. Extract only the most critical information.",
        prompt,
        temperature=0.3,
    )
    return result
