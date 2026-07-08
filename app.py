from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import time

from src.agent import (
    Trace, plan, research, synthesize,
    generate_quiz, adapt
)
from src.llm import QuotaExceeded, LLMError
from src.pdf_utils import export_pdf, extract_text_from_pdf
from src.history import add_session, get_sessions

st.set_page_config(page_title="AI Study Agent", page_icon="📚", layout="wide")

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

* { font-family: 'Inter', sans-serif; color: #e2e8f0; }

html, body, [data-testid="stAppViewContainer"], .main, .stApp {
    background: #0b0e17 !important;
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
    color: #94a3b8;
    font-size: 1.05rem;
    font-weight: 300;
}

.glass-card {
    background: rgba(15, 23, 42, 0.6);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(99, 102, 241, 0.15);
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
    color: #e2e8f0;
    font-weight: 700;
}

.glass-card p, .glass-card li, .glass-card div {
    color: #cbd5e1;
}

.stTextInput>div>div>input {
    background: rgba(30, 41, 59, 0.8) !important;
    border: 1px solid rgba(99, 102, 241, 0.2) !important;
    color: #e2e8f0 !important;
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
    background: rgba(30, 41, 59, 0.8) !important;
    border: 1px solid rgba(99, 102, 241, 0.2) !important;
    color: #e2e8f0 !important;
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
    background: rgba(30, 41, 59, 0.8) !important;
    color: #94a3b8 !important;
    border: 1px solid rgba(99, 102, 241, 0.2) !important;
}

.stButton>button:not([kind="primary"]):hover {
    border-color: #818cf8 !important;
    color: #e2e8f0 !important;
}

.stButton>button:disabled {
    opacity: 0.4 !important;
}

.stRadio>div {
    background: rgba(30, 41, 59, 0.5) !important;
    border-radius: 12px !important;
    padding: 0.3rem;
}

.stRadio>div>label {
    background: transparent !important;
    color: #cbd5e1 !important;
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
    color: #e2e8f0 !important;
}

div[data-testid="stExpander"] {
    background: rgba(15, 23, 42, 0.6) !important;
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid rgba(99, 102, 241, 0.15) !important;
    border-radius: 16px !important;
    margin-bottom: 1rem;
    overflow: hidden;
}

div[data-testid="stExpander"] summary {
    color: #e2e8f0 !important;
    font-weight: 600;
    padding: 1rem 1.5rem !important;
}

div[data-testid="stExpander"] div[role="group"] {
    padding: 0 1.5rem 1rem !important;
}

div[data-testid="stStatusWidget"] {
    background: rgba(15, 23, 42, 0.8) !important;
    backdrop-filter: blur(20px);
    border: 1px solid rgba(99, 102, 241, 0.2) !important;
    border-radius: 16px !important;
    padding: 1rem !important;
}

.stProgress > div > div > div > div {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
}

div[data-testid="stSidebar"] {
    background: rgba(15, 23, 42, 0.85) !important;
    backdrop-filter: blur(24px);
    border-right: 1px solid rgba(99, 102, 241, 0.1);
}

div[data-testid="stSidebar"] p, div[data-testid="stSidebar"] span {
    color: #cbd5e1 !important;
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
    background: rgba(30, 41, 59, 0.5);
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
    color: #f1f5f9;
    font-size: 1.05rem;
    font-weight: 600;
    margin: 0.3rem 0 0.8rem;
}

.result-correct { color: #4ade80 !important; font-weight: 600; }
.result-wrong { color: #fb7185 !important; font-weight: 600; }

.trace-step {
    background: rgba(30, 41, 59, 0.5);
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
            f'<span style="color:#94a3b8;">{step["result"][:150]}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    if not trace_obj.steps:
        st.sidebar.markdown("*Agent reasoning will appear here...*")


trace = Trace()

# ─── Input Section ───
with st.container():
    st.markdown('<div class="glass-card animate-in">', unsafe_allow_html=True)
    topic = st.text_input("🎯 What do you want to learn?", placeholder="e.g., Photosynthesis, Neural Networks, World War II...")

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
        st.rerun()

    col1, col2 = st.columns([1, 1])
    with col1:
        start = st.button("🚀 Start Learning", type="primary", use_container_width=True, disabled=not topic.strip())
    with col2:
        if st.button("🔄 Reset", use_container_width=True):
            for k in ["quiz_state", "quiz_submitted", "study_data", "phase", "pdf_text"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ─── Session State ───
if "quiz_state" not in st.session_state:
    st.session_state.quiz_state = {}
if "quiz_submitted" not in st.session_state:
    st.session_state.quiz_submitted = False
if "study_data" not in st.session_state:
    st.session_state.study_data = None
if "phase" not in st.session_state:
    st.session_state.phase = "input"

# ─── Agent Execution ───
if start or st.session_state.phase == "running":
    st.session_state.phase = "running"

    error_placeholder = st.empty()
    with st.status("🤖 **Agent is working...**", expanded=True) as status:
        try:
            st.write("📋 **Planning** — Breaking topic into subtopics...")
            subtopics = plan(topic, notes, trace)
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
                "**Gemini API quota exceeded.** The free tier has limited requests per day. "
                "Try again later, or load sample data to see a demo."
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
        st.markdown(data["guide"])
        guide_text = data["guide"]
        st.download_button(
            "📥 Download Study Guide",
            guide_text,
            file_name=f"{topic.replace(' ', '_')}_study_guide.md",
            mime="text/markdown",
            use_container_width=True,
        )
        pdf_bytes = export_pdf(topic, guide_text).getvalue()
        st.download_button(
            "📄 Download PDF",
            pdf_bytes,
            file_name=f"{topic.replace(' ', '_')}_study_guide.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

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
            f'<div style="background:rgba(30,41,59,0.6);border:1px solid rgba(99,102,241,0.15);'
            f'border-radius:14px;padding:1rem;margin:1rem 0;text-align:center;">'
            f'<span style="font-size:1.3rem;font-weight:700;">'
            f'{"🎉" if pct >= 80 else "📖"} Score: {correct_count}/{total} ({pct}%)'
            f'</span></div>',
            unsafe_allow_html=True,
        )

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
                    new_questions = generate_quiz(topic, new_guide, count=5, trace=trace)

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
            add_session(topic, f"{correct_count}/{total_q}", len(data["guide"]), correct_count, total_q)
            st.rerun()
        else:
            add_session(topic, f"{len(questions)}/{len(questions)}", len(data["guide"]), len(questions), len(questions))
            st.markdown("---")
            st.markdown('<div class="balloon-container">', unsafe_allow_html=True)
            st.balloons()
            st.markdown("### 🎉 Perfect Score!")
            st.markdown("You answered all questions correctly. Great job!")
            st.markdown('</div>', unsafe_allow_html=True)

render_trace(trace)

# ─── History Sidebar ───
st.sidebar.markdown("---")
st.sidebar.markdown("### 📜 Study History")
sessions = get_sessions()
if sessions:
    for s in sessions[:10]:
        st.sidebar.markdown(
            f'<div style="background:rgba(30,41,59,0.4);border:1px solid rgba(99,102,241,0.1);'
            f'border-radius:8px;padding:0.4rem 0.6rem;margin-bottom:0.3rem;font-size:0.8rem;">'
            f'<span style="color:#818cf8;font-weight:600;">{s["topic"][:30]}</span><br>'
            f'<span style="color:#94a3b8;">{s["date"]} — Score: {s["score"]}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
else:
    st.sidebar.markdown("*No study sessions yet*")
if sessions and st.sidebar.button("🗑️ Clear History", use_container_width=True):
    from pathlib import Path
    Path("history.json").write_text("[]", encoding="utf-8")
    st.rerun()
