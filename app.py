from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import time
import math
import html

from src.agent import (
    Trace, plan, research, synthesize,
    generate_quiz, adapt, answer_question, cheat_sheet
)
from src.llm import QuotaExceeded, LLMError
from src.pdf_utils import export_pdf, extract_text_from_pdf
from src.history import add_session, get_sessions

st.set_page_config(page_title="AI Study Agent", page_icon="📚", layout="wide")

# ─── Session State Init ───
for key, default in [
    ("quiz_state", {}), ("quiz_submitted", False), ("study_data", None),
    ("phase", "input"), ("pdf_text", None), ("current_topic", None),
    ("wrong", []), ("chat_history", []), ("flashcard_flipped", {}),
]:
    if key not in st.session_state:
        st.session_state[key] = default

if "theme" not in st.session_state:
    st.session_state.theme = "dark"

# ─── Theme toggle in sidebar ───
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    is_dark = st.session_state.theme == "dark"
    theme_toggle = st.toggle(
        "☀️ Light Mode" if is_dark else "🌙 Dark Mode",
        value=is_dark,
        key="sidebar_theme_toggle",
    )
    new_theme = "dark" if theme_toggle else "light"
    if new_theme != st.session_state.theme:
        st.session_state.theme = new_theme
        st.rerun()

    # ─── Theme CSS Variables ───
is_dark = st.session_state.theme == "dark"
bg_primary = "#0b0e17" if is_dark else "#f0f2f6"
bg_secondary = "rgba(15, 23, 42, 0.6)" if is_dark else "rgba(255, 255, 255, 0.6)"
text_primary = "#e2e8f0" if is_dark else "#1e293b"
text_secondary = "#cbd5e1" if is_dark else "#475569"
text_muted = "#94a3b8" if is_dark else "#64748b"
card_border = "rgba(99, 102, 241, 0.15)" if is_dark else "rgba(99, 102, 241, 0.2)"
input_bg = "rgba(30, 41, 59, 0.8)" if is_dark else "rgba(255, 255, 255, 0.8)"
sidebar_bg = "rgba(15, 23, 42, 0.85)" if is_dark else "rgba(255, 255, 255, 0.85)"
quiz_bg = "rgba(30, 41, 59, 0.5)" if is_dark else "rgba(255, 255, 255, 0.5)"

st.markdown(f"""
<style>
:root {{
    --bg-primary: {bg_primary};
    --bg-secondary: {bg_secondary};
    --text-primary: {text_primary};
    --text-secondary: {text_secondary};
    --text-muted: {text_muted};
    --card-border: {card_border};
    --input-bg: {input_bg};
    --sidebar-bg: {sidebar_bg};
    --quiz-bg: {quiz_bg};
}}

/* Force dark theme regardless of Streamlit's built-in theme */
.stApp, .main, .block-container, header, footer {{
    background: transparent !important;
}}
.stApp {{ background: var(--bg-primary) !important; }}
p, span, div, li, label, .stMarkdown, .stText {{
    color: var(--text-primary) !important;
}}
a {{ color: #818cf8 !important; }}
code {{ background: rgba(99,102,241,0.15) !important; color: #e2e8f0 !important; }}
</style>""", unsafe_allow_html=True)

# ─── Animated Background (CSS only) ───
st.markdown("""
<style>
@keyframes gradient-shift {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

@keyframes float-shape {
    0%, 100% { transform: translateY(0) rotate(0deg); }
    33% { transform: translateY(-20px) rotate(120deg); }
    66% { transform: translateY(10px) rotate(240deg); }
}

body::before {
    content: '';
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: radial-gradient(ellipse at 20% 50%, rgba(99,102,241,0.08) 0%, transparent 50%),
                radial-gradient(ellipse at 80% 50%, rgba(139,92,246,0.08) 0%, transparent 50%),
                radial-gradient(ellipse at 50% 0%, rgba(129,140,248,0.06) 0%, transparent 50%);
    background-size: 200% 200%;
    animation: gradient-shift 15s ease infinite;
    z-index: 0;
    pointer-events: none;
}

.floating-shapes {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    z-index: 0;
    pointer-events: none;
    overflow: hidden;
}

.floating-shapes .shape {
    position: absolute;
    border-radius: 50%;
    opacity: 0.08;
    animation: float-shape 20s ease-in-out infinite;
}

.floating-shapes .shape:nth-child(1) { width: 300px; height: 300px; background: radial-gradient(circle, #6366f1, transparent); top: 10%; left: -5%; animation-delay: 0s; }
.floating-shapes .shape:nth-child(2) { width: 200px; height: 200px; background: radial-gradient(circle, #8b5cf6, transparent); top: 60%; right: -3%; animation-delay: -5s; }
.floating-shapes .shape:nth-child(3) { width: 250px; height: 250px; background: radial-gradient(circle, #a78bfa, transparent); bottom: 5%; left: 30%; animation-delay: -10s; }
.floating-shapes .shape:nth-child(4) { width: 150px; height: 150px; background: radial-gradient(circle, #818cf8, transparent); top: 30%; right: 20%; animation-delay: -15s; }

@keyframes shimmer {
    0% { background-position: -200% center; }
    100% { background-position: 200% center; }
}
</style>
<div class="floating-shapes">
    <div class="shape"></div>
    <div class="shape"></div>
    <div class="shape"></div>
    <div class="shape"></div>
</div>
""", unsafe_allow_html=True)

# ─── UI CSS ───
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');

* { font-family: 'Inter', sans-serif; }

html, body, [data-testid="stAppViewContainer"], .main, .stApp {
    background: var(--bg-primary) !important;
}

.stApp {
    background: transparent !important;
}

.main-header {
    text-align: center;
    padding: 2rem 0 0.5rem;
    position: relative;
    z-index: 1;
}

.main-header h1 {
    font-size: 3rem;
    font-weight: 800;
    background: linear-gradient(135deg, #818cf8, #c084fc, #f472b6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 0.3rem;
    letter-spacing: -0.02em;
}

.main-header p {
    color: var(--text-muted);
    font-size: 1.05rem;
    font-weight: 300;
}

.glass-card {
    background: var(--bg-secondary);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid var(--card-border);
    border-radius: 16px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    position: relative;
    z-index: 1;
    transition: all 0.3s ease;
}

.glass-card:hover {
    border-color: rgba(99, 102, 241, 0.3);
    box-shadow: 0 8px 32px rgba(99, 102, 241, 0.1);
}

.glass-card h2, .glass-card h3 {
    color: var(--text-primary);
    font-weight: 700;
}

.glass-card p, .glass-card li, .glass-card div {
    color: var(--text-secondary);
}

.stTextInput>div>div>input {
    background: var(--input-bg) !important;
    border: 1px solid var(--card-border) !important;
    color: var(--text-primary) !important;
    border-radius: 12px !important;
    padding: 0.75rem 1rem !important;
    font-size: 1rem !important;
    transition: all 0.3s ease;
}

.stTextInput>div>div>input:focus {
    border-color: #818cf8 !important;
    box-shadow: 0 0 0 3px rgba(129, 140, 248, 0.15) !important;
}

.stTextArea>div>div>textarea {
    background: var(--input-bg) !important;
    border: 1px solid var(--card-border) !important;
    color: var(--text-primary) !important;
    border-radius: 12px !important;
    transition: all 0.3s ease;
}

.stTextArea>div>div>textarea:focus {
    border-color: #818cf8 !important;
    box-shadow: 0 0 0 3px rgba(129, 140, 248, 0.15) !important;
}

.stButton>button {
    border-radius: 12px !important;
    font-weight: 600 !important;
    padding: 0.6rem 1.5rem !important;
    transition: all 0.3s ease !important;
    border: none !important;
}

.stButton>button[kind="primary"] {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    color: white !important;
    box-shadow: 0 4px 15px rgba(99, 102, 241, 0.3) !important;
}

.stButton>button[kind="primary"]:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 6px 25px rgba(99, 102, 241, 0.4) !important;
}

.stButton>button:not([kind="primary"]) {
    background: var(--input-bg) !important;
    color: var(--text-muted) !important;
    border: 1px solid var(--card-border) !important;
}

.stButton>button:not([kind="primary"]):hover {
    border-color: #818cf8 !important;
    color: var(--text-primary) !important;
}

.stButton>button:disabled {
    opacity: 0.4 !important;
}

.stRadio>div {
    background: var(--quiz-bg) !important;
    border-radius: 12px !important;
    padding: 0.3rem;
}

.stRadio>div>label {
    background: transparent !important;
    color: var(--text-secondary) !important;
    border: 1px solid transparent !important;
    border-radius: 8px !important;
    padding: 0.5rem 1rem !important;
    transition: all 0.2s ease;
}

.stRadio>div>label:hover {
    background: rgba(99, 102, 241, 0.1) !important;
    border-color: rgba(99, 102, 241, 0.3) !important;
}

.stRadio>div>label[data-checked="true"] {
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(139, 92, 246, 0.2)) !important;
    border-color: #818cf8 !important;
    color: var(--text-primary) !important;
}

div[data-testid="stExpander"] {
    background: var(--bg-secondary) !important;
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid var(--card-border) !important;
    border-radius: 16px !important;
    margin-bottom: 1rem;
    overflow: hidden;
}

div[data-testid="stExpander"] summary {
    color: var(--text-primary) !important;
    font-weight: 600;
    padding: 1rem 1.5rem !important;
}

div[data-testid="stExpander"] div[role="group"] {
    padding: 0 1.5rem 1rem !important;
}

div[data-testid="stStatusWidget"] {
    background: var(--bg-secondary) !important;
    backdrop-filter: blur(20px);
    border: 1px solid var(--card-border) !important;
    border-radius: 16px !important;
    padding: 1rem !important;
}

.stProgress > div > div > div > div {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
}

div[data-testid="stSidebar"] {
    background: var(--sidebar-bg) !important;
    backdrop-filter: blur(24px);
    border-right: 1px solid rgba(99, 102, 241, 0.1);
}

div[data-testid="stSidebar"] p, div[data-testid="stSidebar"] span {
    color: var(--text-secondary) !important;
}

@keyframes float {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-6px); }
}

@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}

.animate-in {
    animation: fadeInUp 0.5s ease forwards;
}

.quiz-question {
    background: var(--quiz-bg);
    border: 1px solid rgba(99, 102, 241, 0.12);
    border-radius: 14px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 1rem;
    animation: fadeInUp 0.4s ease forwards;
    opacity: 0;
}

.quiz-question:nth-child(1) { animation-delay: 0.05s; }
.quiz-question:nth-child(2) { animation-delay: 0.1s; }
.quiz-question:nth-child(3) { animation-delay: 0.15s; }
.quiz-question:nth-child(4) { animation-delay: 0.2s; }
.quiz-question:nth-child(5) { animation-delay: 0.25s; }

.quiz-question .q-number {
    color: #818cf8;
    font-weight: 700;
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.quiz-question .q-text {
    color: var(--text-primary);
    font-size: 1.05rem;
    font-weight: 600;
    margin: 0.3rem 0 0.8rem;
}

.result-correct { color: #4ade80 !important; font-weight: 600; }
.result-wrong { color: #fb7185 !important; font-weight: 600; }

.trace-step {
    background: var(--quiz-bg);
    border: 1px solid rgba(99, 102, 241, 0.1);
    border-radius: 10px;
    padding: 0.6rem 0.8rem;
    margin-bottom: 0.4rem;
    font-size: 0.85rem;
}

.trace-step .phase-label {
    font-weight: 600;
}

.balloon-container {
    text-align: center;
    padding: 2rem;
}

.stMarkdown {
    position: relative;
    z-index: 1;
}

/* ─── Flashcard CSS ─── */
.flashcard-container {
    perspective: 1000px;
    margin-bottom: 1rem;
}

.flashcard {
    position: relative;
    width: 100%;
    min-height: 160px;
    cursor: pointer;
    transition: transform 0.6s;
    transform-style: preserve-3d;
}

.flashcard.flipped {
    transform: rotateY(180deg);
}

.flashcard-front, .flashcard-back {
    position: absolute;
    width: 100%;
    min-height: 160px;
    backface-visibility: hidden;
    -webkit-backface-visibility: hidden;
    border-radius: 14px;
    padding: 1.2rem 1.5rem;
    display: flex;
    flex-direction: column;
    justify-content: center;
}

.flashcard-front {
    background: var(--bg-secondary);
    border: 1px solid var(--card-border);
}

.flashcard-back {
    background: var(--bg-secondary);
    border: 1px solid var(--card-border);
    transform: rotateY(180deg);
}

.flashcard-front .card-label {
    color: #818cf8;
    font-weight: 700;
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.5rem;
}

.flashcard-front .card-question {
    color: var(--text-primary);
    font-size: 1rem;
    font-weight: 600;
}

.flashcard-back .card-answer {
    color: #4ade80;
    font-weight: 700;
    font-size: 1rem;
    margin-bottom: 0.5rem;
}

.flashcard-back .card-explanation {
    color: var(--text-secondary);
    font-size: 0.9rem;
}
</style>
""", unsafe_allow_html=True)

# ─── Header ───
st.markdown("""
<div class="main-header">
    <h1>📚 AI Study Agent</h1>
    <p>Learn any topic with AI-powered research, study guides, and adaptive quizzes</p>
</div>
""", unsafe_allow_html=True)


def render_trace(trace_obj):
    st.sidebar.markdown("### 🧠 Reasoning Trace")
    st.sidebar.markdown("---")
    icons = {"plan": "📋", "research": "🔍", "synthesize": "📝", "quiz": "❓", "adapt": "🔄"}
    for step in trace_obj.steps:
        icon = icons.get(step["phase"], "⚡")
        st.sidebar.markdown(
            f'<div class="trace-step">'
            f'<span class="phase-label" style="color:#818cf8;">{icon} {step["phase"].upper()}</span><br>'
            f'<span style="color:var(--text-muted);">{step["result"][:150]}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    if not trace_obj.steps:
        st.sidebar.markdown("*Agent reasoning will appear here...*")


trace = Trace()

# ─── Input Section ───
with st.container():
    st.markdown('<div class="glass-card animate-in">', unsafe_allow_html=True)
    col_topic, col_diff = st.columns([3, 1])
    with col_topic:
        topic = st.text_input("🎯 What do you want to learn?", placeholder="e.g., Photosynthesis, Neural Networks, World War II...")
    with col_diff:
        difficulty = st.radio("📊 Difficulty", ["Beginner", "Intermediate", "Advanced"], index=1, horizontal=True)

    with st.expander("📄 Add context (optional)"):
        notes = st.text_area("Paste notes, background knowledge, or upload text", placeholder="Anything you already know...", height=100)
        uploaded_pdf = st.file_uploader("Or upload a PDF for context", type="pdf")
        if uploaded_pdf:
            pdf_text = extract_text_from_pdf(uploaded_pdf.read())
            st.session_state.pdf_text = pdf_text
            st.success(f"Extracted {len(pdf_text)} characters from PDF")
        if st.session_state.get("pdf_text"):
            notes = notes + "\n\n--- From PDF ---\n" + st.session_state.pdf_text if notes else st.session_state.pdf_text

    if st.button("📂 Load Sample Data", use_container_width=True):
        st.session_state.current_topic = "Quantum Computing"
        subtopics = ["Introduction & Basics", "Key Mechanisms", "Applications & Impact"]
        research_results = {
            "Introduction & Basics": "**Quantum computing** leverages quantum mechanical phenomena like superposition and entanglement to process information in fundamentally new ways. Unlike classical bits (0 or 1), quantum bits (qubits) can exist in multiple states simultaneously.\n\n**Key concepts:**\n- Superposition: Qubits can be 0, 1, or both\n- Entanglement: Linked qubits share states instantly\n- Quantum gates: Operations that manipulate qubits",
            "Key Mechanisms": "**Quantum supremacy** occurs when quantum computers solve problems classical computers cannot. IBM, Google, and Rigetti have demonstrated 50+ qubit systems.\n\n**Major approaches:**\n- Superconducting qubits (Google, IBM)\n- Trapped ions (IonQ, Honeywell)\n- Topological qubits (Microsoft)\n- Photonic systems (PsiQuantum)",
            "Applications & Impact": "**Applications:**\n1. Drug discovery & molecular simulation\n2. Cryptography & cybersecurity\n3. Financial modeling & optimization\n4. Climate change & material science\n\n**Current state:** NISQ (Noisy Intermediate-Scale Quantum) era. Error correction is the main challenge."
        }
        guide = """## Quantum Computing Study Guide

### 1. Introduction & Basics
Quantum computing harnesses quantum mechanics to process information. **Qubits** (quantum bits) differ from classical bits by existing in superposition—both 0 and 1 simultaneously until measured. This enables exponential parallelism.

**Superposition** allows a quantum computer to explore multiple solutions at once. **Entanglement** creates correlations between qubits that persist even when separated, enabling powerful computational capabilities.

### 2. Key Mechanisms
Several physical implementations exist:
- **Superconducting circuits**: Operate at near absolute zero; used by Google and IBM
- **Trapped ions**: Use electromagnetic fields to trap individual ions; highly precise
- **Photonic systems**: Use photons as qubits; operate at room temperature

**Quantum gates** (Hadamard, CNOT, Toffoli) manipulate qubits, forming quantum circuits analogous to classical logic gates.

### 3. Applications & Impact
Near-term applications include quantum-enhanced machine learning, optimization problems in logistics, and simulating chemical reactions for drug discovery. Long-term, quantum computers may break current encryption standards (RSA, ECC) via Shor's algorithm.

**Challenges:** Decoherence, error rates, qubit connectivity, and scaling to fault-tolerant systems.
"""
        questions = [
            {"question": "What property allows a qubit to be in multiple states at once?", "options": ["A) Entanglement", "B) Superposition", "C) Interference", "D) Collapse"], "correct": 1, "explanation": "Superposition allows qubits to exist in a combination of 0 and 1 states simultaneously."},
            {"question": "Which company demonstrated 50+ qubit quantum supremacy?", "options": ["A) Microsoft", "B) IBM", "C) Google", "D) All of the above"], "correct": 2, "explanation": "Google claimed quantum supremacy in 2019 with their Sycamore processor."},
            {"question": "What is the main challenge in current quantum computing?", "options": ["A) Too many qubits", "B) Error correction & decoherence", "C) Software availability", "D) High temperature operation"], "correct": 1, "explanation": "Error correction and decoherence are the primary challenges in the NISQ era."},
            {"question": "What algorithm threatens current RSA encryption?", "options": ["A) Grover's", "B) Shor's", "C) Deutsch-Jozsa", "D) Simon's"], "correct": 1, "explanation": "Shor's algorithm can factor large numbers exponentially faster than classical algorithms."},
            {"question": "Which qubit implementation operates at room temperature?", "options": ["A) Superconducting", "B) Trapped ion", "C) Photonic", "D) Topological"], "correct": 2, "explanation": "Photonic quantum computers use photons as qubits and can operate at room temperature."},
        ]
        sample_trace = Trace()
        sample_trace.add("plan", "Plan quantum computing", "3 subtopics planned")
        sample_trace.add("research", "Research introduction", "Basic concepts researched")
        sample_trace.add("synthesize", "Synthesize guide", "Guide created")
        sample_trace.add("quiz", "Generate quiz", "5 questions generated")
        st.session_state.study_data = {
            "subtopics": subtopics,
            "research": research_results,
            "guide": guide,
            "questions": questions,
            "trace": sample_trace,
        }
        st.session_state.phase = "review"
        st.session_state.quiz_state = {}
        st.session_state.quiz_submitted = False
        st.session_state.chat_history = []
        st.session_state.cheat_sheet_text = None
        st.rerun()

    col1, col2 = st.columns([1, 1])
    with col1:
        start = st.button("🚀 Start Learning", type="primary", use_container_width=True, disabled=not topic.strip())
    with col2:
        if st.button("🔄 Reset", use_container_width=True):
            for k in ["quiz_state", "quiz_submitted", "study_data", "phase", "pdf_text", "chat_history", "cheat_sheet_text"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


# ─── Agent Execution ───
if start or st.session_state.phase == "running":
    st.session_state.current_topic = topic
    st.session_state.phase = "running"

    # Difficulty-aware context passed to plan()
    diff_notes = f"{notes}\n\n[Difficulty: {difficulty}]" if notes else f"[Difficulty: {difficulty}]"

    error_placeholder = st.empty()
    with st.status("🤖 **Agent is working...**", expanded=True) as status:
        try:
            st.write("📋 **Planning** — Breaking topic into subtopics...")
            subtopics = plan(topic, diff_notes, trace)
            st.write(f"✅ Plan complete: **{len(subtopics)}** subtopics identified")

            st.write("🔍 **Researching** — Searching the web for each subtopic...")
            research_results = {}
            progress = st.progress(0, text="Researching...")
            for i, sub in enumerate(subtopics):
                progress.progress(i / len(subtopics), text=f"Researching: **{sub}**")
                summary = research(sub, trace)
                research_results[sub] = summary
            progress.progress(1.0, text="✅ Research complete!")
            st.write(f"✅ Researched **{len(subtopics)}** subtopics")

            st.write("📝 **Synthesizing** — Creating study guide...")
            guide = synthesize(topic, subtopics, research_results, trace)
            st.write("✅ Study guide created")

            st.write("❓ **Generating Quiz** — Creating test questions...")
            questions = generate_quiz(topic, guide, trace=trace)
            st.write(f"✅ Generated **{len(questions)}** questions")

            status.update(label="✅ Agent complete!", state="complete")
        except QuotaExceeded:
            status.update(label="⚠️ API quota exceeded", state="error")
            error_placeholder.error(
                "**Gemini API quota exceeded.** The free tier is limited. "
                "Get a fresh key at https://aistudio.google.com/apikey"
                " and paste it in the sidebar."
            )
            st.stop()
        except LLMError as e:
            status.update(label="⚠️ LLM error", state="error")
            error_placeholder.error(f"**Error:** {e}")
            st.stop()
        except Exception as e:
            status.update(label="⚠️ Unexpected error", state="error")
            error_placeholder.error(f"**Unexpected error:** {e}")
            st.stop()

    st.session_state.study_data = {
        "subtopics": subtopics,
        "research": research_results,
        "guide": guide,
        "questions": questions,
        "trace": trace,
    }
    st.session_state.phase = "review"
    st.rerun()


# ─── Review Phase ───
if st.session_state.phase == "review" and st.session_state.study_data:
    data = st.session_state.study_data
    trace = data["trace"]

    with st.expander("📋 Study Plan", expanded=False):
        for i, sub in enumerate(data["subtopics"], 1):
            st.markdown(f"**{i}.** {sub}")

    with st.expander("📖 Study Guide", expanded=True):
        tab1, tab2, tab3, tab4 = st.tabs(["📖 Guide", "🧠 Mind Map", "📋 Cheat Sheet", "💬 AI Chat"])

        with tab1:
            word_count = len(data["guide"].split())
            reading_time = max(1, round(word_count / 200))
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.5rem;">'
                f'<span style="color:var(--text-muted);font-size:0.85rem;">⏱️ ~{reading_time} min read ({word_count} words)</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
            guide_text = data["guide"]
            st.markdown(guide_text)
            st.download_button(
                "📥 Download Study Guide",
                guide_text,
                file_name=f"{st.session_state.get('current_topic', topic).replace(' ', '_')}_study_guide.md",
                mime="text/markdown",
                use_container_width=True,
            )
            try:
                pdf_bytes = export_pdf(topic if 'topic' in dir() else st.session_state.get('current_topic', ''), guide_text).getvalue()
                st.download_button(
                    "📄 Download PDF",
                    pdf_bytes,
                    file_name=f"{st.session_state.get('current_topic', topic).replace(' ', '_')}_study_guide.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            except Exception as e:
                st.warning(f"⚠️ PDF generation failed: {e}")

        with tab2:
            st.markdown("### 🧠 Topic Mind Map")
            subtopics_list = data.get("subtopics", [])
            if subtopics_list:
                topic_name = html.escape(st.session_state.get("current_topic", topic))
                angles = [0, 72, 144, 216, 288]
                colors = ["#818cf8", "#4ade80", "#f472b6", "#fbbf24", "#34d399"]
                svg_parts = [
                    f'<svg width="100%" height="100%" viewBox="0 0 800 400" xmlns="http://www.w3.org/2000/svg">'
                    f'<defs><filter id="g"><feGaussianBlur stdDeviation="3" result="b"/><feMerge>'
                    f'<feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>'
                    f'<circle cx="400" cy="200" r="50" fill="rgba(99,102,241,0.15)" stroke="#818cf8" stroke-width="2"/>'
                    f'<text x="400" y="198" text-anchor="middle" fill="#e2e8f0" font-size="12" font-weight="700">{topic_name[:30]}</text>'
                    f'<text x="400" y="212" text-anchor="middle" fill="#818cf8" font-size="9">{topic_name[30:]}</text>'
                ]
                for i, sub in enumerate(subtopics_list[:5]):
                    sub_escaped = html.escape(sub)
                    angle = angles[i]
                    rad = angle * 3.14159 / 180
                    x2 = 400 + 180 * math.cos(rad)
                    y2 = 200 + 180 * math.sin(rad)
                    svg_parts.append(
                        f'<line x1="400" y1="200" x2="{x2:.0f}" y2="{y2:.0f}" stroke="{colors[i]}" stroke-width="1.5" opacity="0.4"/>'
                        f'<circle cx="{x2:.0f}" cy="{y2:.0f}" r="30" fill="{colors[i]}22" stroke="{colors[i]}" stroke-width="1.5"/>'
                        f'<text x="{x2:.0f}" y="{y2:.0f}" text-anchor="middle" fill="#e2e8f0" font-size="8" font-weight="600">'
                        f'<tspan x="{x2:.0f}" dy="-3">{sub_escaped[:12]}</tspan>'
                        f'<tspan x="{x2:.0f}" dy="10">{sub_escaped[12:24]}</tspan>'
                        f'</text>'
                    )
                svg_parts.append('</svg>')
                mind_map_html = (
                    '<div style="width:100%;height:400px;position:relative;overflow:hidden;'
                    'border-radius:12px;background:radial-gradient(circle at center, '
                    'rgba(99,102,241,0.05) 0%, transparent 70%);">'
                    + "".join(svg_parts)
                    + "</div>"
                )
                st.markdown(mind_map_html, unsafe_allow_html=True)
                st.caption("Visual overview of topic structure")
            else:
                st.info("Generate a study guide first to see the mind map.")

        with tab3:
            st.markdown("### 📋 Cheat Sheet")
            if "cheat_sheet_text" not in st.session_state:
                if st.button("✨ Generate Cheat Sheet", use_container_width=True):
                    with st.spinner("Generating condensed summary..."):
                        try:
                            cs = cheat_sheet(data["guide"], st.session_state.get("current_topic", topic))
                            st.session_state.cheat_sheet_text = cs
                        except QuotaExceeded:
                            st.error("API quota exceeded. Get a fresh key at https://aistudio.google.com/apikey")
                        except Exception as e:
                            st.error(f"Error: {e}")
            if "cheat_sheet_text" in st.session_state and st.session_state.cheat_sheet_text is not None:
                if st.session_state.cheat_sheet_text:
                    st.markdown(st.session_state.cheat_sheet_text)
                else:
                    st.info("Cheat sheet was empty. Try generating again.")
                st.download_button(
                    "📥 Download Cheat Sheet",
                    st.session_state.cheat_sheet_text,
                    file_name=f"{st.session_state.get('current_topic', topic).replace(' ', '_')}_cheatsheet.md",
                    mime="text/markdown",
                    use_container_width=True,
                )

        with tab4:
            st.markdown("Ask questions about the study guide.")
            for msg in st.session_state.chat_history:
                st.markdown(
                    f'<div style="background:var(--quiz-bg);border-radius:10px;padding:0.5rem 0.8rem;margin-bottom:0.4rem;">'
                    f'<span style="color:#818cf8;font-weight:600;">You:</span> {msg["q"]}</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<div style="background:var(--bg-secondary);border:1px solid var(--card-border);border-radius:10px;padding:0.5rem 0.8rem;margin-bottom:0.8rem;">'
                    f'<span style="color:#4ade80;font-weight:600;">Tutor:</span> {msg["a"]}</div>',
                    unsafe_allow_html=True,
                )

            chat_input = st.text_input("💬 Ask a question...", key="chat_question", placeholder="e.g., Can you explain superposition?")
            col_send, col_clear = st.columns([1, 1])
            with col_send:
                if st.button("Send", type="primary", key="chat_send", use_container_width=True) and chat_input:
                    with st.spinner("Thinking..."):
                        try:
                            answer = answer_question(chat_input, data["guide"], st.session_state.chat_history)
                            st.session_state.chat_history.append({"q": chat_input, "a": answer})
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
            with col_clear:
                if st.session_state.chat_history and st.button("🗑️ Clear Chat", key="clear_chat", use_container_width=True):
                    st.session_state.chat_history = []
                    st.rerun()

    st.markdown("---")
    st.markdown("### ✍️ Quiz")
    st.markdown("Answer all questions, then submit to check your understanding.")

    questions = data["questions"]
    for i, q in enumerate(questions):
        st.markdown(f'<div class="quiz-question">', unsafe_allow_html=True)
        st.markdown(f'<span class="q-number">Question {i+1}</span>', unsafe_allow_html=True)
        st.markdown(f'<div class="q-text">{q["question"]}</div>', unsafe_allow_html=True)

        key = f"quiz_{i}"

        if st.session_state.quiz_submitted:
            ua = st.session_state.quiz_state.get(key, "")
            correct = q["options"][q["correct"]] == ua if ua else False
            icon = "✅" if correct else "❌"
            cls = "result-correct" if correct else "result-wrong"
            st.markdown(f'<span class="{cls}">{icon} Your answer: **{ua}**</span>', unsafe_allow_html=True)
            if not correct:
                st.markdown(f'✔️ Correct: **{q["options"][q["correct"]]}**')
                if q.get("explanation"):
                    st.markdown(f'💡 *{q["explanation"]}*')
        else:
            selected = st.radio("", q["options"], key=key, index=None, label_visibility="collapsed")
            if selected:
                st.session_state.quiz_state[key] = selected

        st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.quiz_submitted:
        wrong = st.session_state.get("wrong", [])
        total = len(questions)
        correct_count = total - len(wrong)
        pct = int(correct_count / total * 100)
        st.markdown(
            f'<div style="background:var(--bg-secondary);border:1px solid var(--card-border);'
            f'border-radius:14px;padding:1rem;margin:1rem 0;text-align:center;">'
            f'<span style="font-size:1.3rem;font-weight:700;color:var(--text-primary);">'
            f'{"🎉" if pct >= 80 else "📖"} Score: {correct_count}/{total} ({pct}%)'
            f'</span></div>',
            unsafe_allow_html=True,
        )

        # ─── Flashcards Section ───
        st.markdown("---")
        st.markdown("### 🃏 Flashcards")
        st.markdown("Click **Flip** to reveal the answer.")
        for i, q in enumerate(questions):
            card_key = f"fc_{i}"
            flipped = st.session_state.flashcard_flipped.get(card_key, False)
            card_html = f'''
            <div class="flashcard-container">
                <div class="flashcard {"flipped" if flipped else ""}">
                    <div class="flashcard-front">
                        <div class="card-label">Question {i+1}</div>
                        <div class="card-question">{q["question"]}</div>
                    </div>
                    <div class="flashcard-back">
                        <div class="card-answer">✅ {q["options"][q["correct"]]}</div>
                        <div class="card-explanation">{q.get("explanation", "")}</div>
                    </div>
                </div>
            </div>
            '''
            st.markdown(card_html, unsafe_allow_html=True)
            if st.button(f"🔄 Flip Card {i+1}", key=f"flip_btn_{i}", use_container_width=True):
                st.session_state.flashcard_flipped[card_key] = not flipped
                st.rerun()

    if not st.session_state.quiz_submitted:
        disabled = len(st.session_state.quiz_state) != len(questions)
        if st.button("📤 Submit Answers", type="primary", disabled=disabled):
            wrong = []
            for i, q in enumerate(questions):
                ua = st.session_state.quiz_state.get(f"quiz_{i}", "")
                correct_answer = q["options"][q["correct"]]
                if ua != correct_answer:
                    wrong.append({
                        "question": q["question"],
                        "user_answer": ua,
                        "correct_answer": correct_answer,
                        "explanation": q.get("explanation", ""),
                    })
            st.session_state.wrong = wrong
            st.session_state.quiz_submitted = True
            st.rerun()

    if st.session_state.quiz_submitted:
        wrong = st.session_state.get("wrong", [])
        if wrong:
            st.markdown("---")
            st.markdown("### 🔄 Adaptive Re-Study")
            st.markdown(f"You missed **{len(wrong)}/{len(questions)}** questions. Let me create a focused plan.")

            with st.status("🤖 **Adapting study plan...**", expanded=True) as status:
                try:
                    st.write("📋 Analyzing weak areas and creating focused review...")
                    adapt_text = adapt(wrong, data["guide"], trace)
                    st.write("✅ Focused review created")

                    st.write("❓ Generating new quiz...")
                    new_guide = data["guide"] + "\n\n## Focused Review\n" + adapt_text
                    new_questions = generate_quiz(topic if 'topic' in dir() else st.session_state.get('current_topic', ''), new_guide, count=5, trace=trace)

                    status.update(label="✅ Adaptive plan ready!", state="complete")
                except QuotaExceeded:
                    status.update(label="⚠️ API quota exceeded", state="error")
                    st.error(
                        "**Gemini API quota exceeded.** Try again later or load sample data."
                    )
                    st.stop()
                except LLMError as e:
                    status.update(label="⚠️ LLM error", state="error")
                    st.error(f"**Error:** {e}")
                    st.stop()

            st.markdown("**📖 Focused Review**")
            st.markdown(adapt_text)

            st.session_state.study_data = {
                "subtopics": data["subtopics"],
                "research": data["research"],
                "guide": new_guide,
                "questions": new_questions,
                "trace": trace,
            }
            st.session_state.quiz_state = {}
            st.session_state.quiz_submitted = False
            st.session_state.wrong = []
            total_q = len(data["questions"])
            correct_count = total_q - len(wrong)
            add_session(
                st.session_state.get("current_topic", topic if 'topic' in dir() else ""),
                f"{correct_count}/{total_q}",
                len(data["guide"]),
                correct_count,
                total_q,
            )
            st.rerun()
        else:
            add_session(
                st.session_state.get("current_topic", topic if 'topic' in dir() else ""),
                f"{len(questions)}/{len(questions)}",
                len(data["guide"]),
                len(questions),
                len(questions),
            )
            st.markdown("---")
            st.markdown('<div class="balloon-container">', unsafe_allow_html=True)
            st.balloons()
            st.markdown("### 🎉 Perfect Score!")
            st.markdown("You answered all questions correctly. Great job!")
            st.markdown('</div>', unsafe_allow_html=True)

    render_trace(trace)

# ─── History Sidebar ───
st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 Progress")
sessions = get_sessions()
if sessions:
    scores = [s["correct"] / max(s["total"], 1) * 100 for s in sessions[-20:]]
    avg = sum(scores) / len(scores)
    st.sidebar.markdown(f"**Average score:** {avg:.0f}%")
    st.sidebar.markdown(f"**Sessions:** {len(sessions)}")
    st.sidebar.markdown(f"**Topics studied:** {len(set(s['topic'] for s in sessions))}")
    chart_data = {"Score": scores}
    st.sidebar.line_chart(chart_data, height=120)
st.sidebar.markdown("---")
st.sidebar.markdown("### 📜 Study History")
if sessions:
    for s in sessions[:10]:
        st.sidebar.markdown(
            f'<div style="background:var(--quiz-bg);border:1px solid var(--card-border);'
            f'border-radius:8px;padding:0.4rem 0.6rem;margin-bottom:0.3rem;font-size:0.8rem;">'
            f'<span style="color:#818cf8;font-weight:600;">{s["topic"][:30]}</span><br>'
            f'<span style="color:var(--text-muted);">{s["date"]} — Score: {s["score"]}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
else:
    st.sidebar.markdown("*No study sessions yet*")
if sessions and st.sidebar.button("🗑️ Clear History", use_container_width=True):
    from src.history import HISTORY_FILE
    HISTORY_FILE.write_text("[]", encoding="utf-8")
    st.rerun()
