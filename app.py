import os
import shutil

for p in [
    r"C:\Users\priya\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin",
    r"C:\Program Files\ffmpeg\bin",
    r"C:\ffmpeg\bin",
]:
    if os.path.exists(p) and p not in os.environ.get("PATH", ""):
        os.environ["PATH"] = p + os.pathsep + os.environ.get("PATH", "")
        break

import streamlit as st
import time
from dotenv import load_dotenv
from utils.audio_processor import process_input, fetch_youtube_transcript
from core.transcriber import transcribe_all
from core.summarizer import summarize, generate_title
from core.extractor import extract_action_items, extract_key_decisions, extract_questions
from core.rag_engine import build_rag_chain, ask_question, stream_question
from concurrent.futures import ThreadPoolExecutor

load_dotenv()

# Sync Streamlit Cloud secrets to environment variables if deployed
try:
    if hasattr(st, "secrets"):
        for k, v in st.secrets.items():
            if isinstance(v, str) and k not in os.environ:
                os.environ[k] = v
except Exception:
    pass

# ─── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Video Assistant",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=JetBrains+Mono:wght@300;400;500&display=swap');

/* ── Root Variables: Modern Clean Light Blue Theme ── */
:root {
    --bg: #edf5fd;
    --surface: #ffffff;
    --surface-2: #f4f8fe;
    --border: #cfe2f7;
    --accent: #1d68ed;
    --accent-glow: #3b82f6;
    --accent-2: #0284c7;
    --text: #0f172a;
    --text-muted: #64748b;
    --success: #10b981;
    --warning: #f59e0b;
    --danger: #ef4444;
}

/* ── Global Reset ── */
html, body, [class*="css"] {
    font-family: 'JetBrains Mono', monospace;
    background-color: var(--bg) !important;
    background-image: none !important;
    color: var(--text) !important;
}

html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"], .main, section.main, .block-container {
    background-color: var(--bg) !important;
    background-image: none !important;
}

/* Explicitly eliminate all grid textures, box lines, and pseudo-elements */
.stApp::before,
.stApp::after,
[data-testid="stAppViewContainer"]::before,
[data-testid="stAppViewContainer"]::after,
[data-testid="stHeader"]::before,
[data-testid="stHeader"]::after,
.main::before,
.main::after,
section.main::before,
section.main::after {
    display: none !important;
    content: none !important;
    background: none !important;
    background-image: none !important;
    width: 0 !important;
    height: 0 !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #f4f8fe !important;
    border-right: 1px solid var(--border) !important;
}

[data-testid="stSidebar"] * {
    color: var(--text) !important;
}

/* ── Headings ── */
h1, h2, h3, h4, h5, h6 {
    font-family: 'Syne', sans-serif !important;
    color: #0f172a !important;
}

/* ── Hero Title ── */
.hero-title {
    font-family: 'Syne', sans-serif;
    font-size: clamp(2rem, 5vw, 3.5rem);
    font-weight: 800;
    line-height: 1.1;
    margin: 0;
    background: linear-gradient(135deg, #0f172a 0%, #1d68ed 50%, #0284c7 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.hero-sub {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8rem;
    color: #475569;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    margin-top: 0.5rem;
}

/* ── Cards ── */
.card {
    background: #ffffff;
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    position: relative;
    overflow: hidden;
    box-shadow: 0 4px 16px rgba(29, 104, 237, 0.05);
    transition: all 0.25s ease;
}

.card:hover {
    border-color: var(--accent);
    box-shadow: 0 8px 24px rgba(29, 104, 237, 0.12);
}

.card::before {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 4px; height: 100%;
    background: linear-gradient(180deg, var(--accent), var(--accent-2));
}

.card-title {
    font-family: 'Syne', sans-serif;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: #475569;
    margin-bottom: 0.75rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.card-content {
    font-size: 0.875rem;
    line-height: 1.7;
    color: #1e293b;
}

/* ── Accent Badges ── */
.badge {
    display: inline-block;
    padding: 0.25rem 0.65rem;
    border-radius: 6px;
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

.badge-purple { background: #dbeafe; color: #1d4ed8; border: 1px solid #bfdbfe; }
.badge-cyan   { background: #e0f2fe; color: #0284c7; border: 1px solid #bae6fd; }
.badge-green  { background: #dcfce7; color: #15803d; border: 1px solid #bbf7d0; }

/* ── Input & Buttons ── */
.stTextInput > div > div > input,
.stSelectbox > div > div {
    background: #ffffff !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: #0f172a !important;
    font-family: 'JetBrains Mono', monospace !important;
}

.stTextInput > div > div > input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 2px rgba(29, 104, 237, 0.2) !important;
}

.stButton > button {
    background: linear-gradient(135deg, #1d68ed 0%, #0284c7 100%) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 800 !important;
    font-size: 0.875rem !important;
    letter-spacing: 0.05em !important;
    padding: 0.6rem 1.5rem !important;
    transition: all 0.2s !important;
    text-transform: uppercase !important;
    box-shadow: 0 4px 14px rgba(29, 104, 237, 0.25) !important;
}

.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 8px 25px rgba(29, 104, 237, 0.4) !important;
    background: linear-gradient(135deg, #2563eb 0%, #0369a1 100%) !important;
}

/* Secondary button */
.stButton > button[kind="secondary"] {
    background: #ffffff !important;
    color: #475569 !important;
    border: 1px solid var(--border) !important;
}

/* ── Progress / Status ── */
.status-bar {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem 1rem;
    background: #ffffff;
    border-radius: 8px;
    margin: 0.4rem 0;
    border: 1px solid var(--border);
    font-size: 0.8rem;
    color: #1e293b;
    box-shadow: 0 2px 6px rgba(29, 104, 237, 0.04);
}

.status-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
}

.dot-active   { background: var(--accent); box-shadow: 0 0 8px var(--accent); animation: pulse 1.5s infinite; }
.dot-done     { background: var(--success); }
.dot-pending  { background: #94a3b8; }

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.4; }
}

/* ── Chat ── */
.chat-container {
    background: #ffffff;
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.25rem;
    max-height: 420px;
    overflow-y: auto;
    margin-bottom: 1rem;
    box-shadow: 0 4px 16px rgba(29, 104, 237, 0.05);
}

.chat-msg {
    margin-bottom: 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
}

.chat-label {
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.15em;
    text-transform: uppercase;
}

.chat-bubble {
    display: inline-block;
    padding: 0.65rem 1.1rem;
    border-radius: 10px;
    font-size: 0.85rem;
    line-height: 1.6;
    max-width: 90%;
}

.user-label  { color: #1d4ed8; }
.bot-label   { color: #0284c7; }

.user-bubble { background: #dbeafe; border: 1px solid #bfdbfe; color: #0f172a; align-self: flex-end; }
.bot-bubble  { background: #f8fafc; border: 1px solid #e2e8f0; color: #0f172a; align-self: flex-start; box-shadow: 0 2px 6px rgba(0,0,0,0.03); }

/* ── Divider ── */
hr {
    border: none !important;
    border-top: 1px solid var(--border) !important;
    margin: 1.5rem 0 !important;
}

/* ── Transcript box ── */
.transcript-box {
    background: #ffffff;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.25rem;
    font-size: 0.82rem;
    line-height: 1.8;
    max-height: 300px;
    overflow-y: auto;
    color: #334155;
    white-space: pre-wrap;
    word-break: break-word;
}

/* ── Stale Streamlit elements ── */
.stProgress > div > div > div { background: var(--accent) !important; }
.stSpinner > div { border-top-color: var(--accent) !important; }
[data-testid="stMarkdownContainer"] p { color: #0f172a !important; }
label { color: #475569 !important; font-size: 0.8rem !important; }

/* ── Hide "Press Enter to apply" instructions ── */
[data-testid="InputInstructions"],
div[data-testid="InputInstructions"],
.stInputInstructions {
    display: none !important;
    visibility: hidden !important;
    height: 0 !important;
    padding: 0 !important;
    margin: 0 !important;
}

/* scrollbar */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: #edf5fd; }
::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #94a3b8; }
</style>
""", unsafe_allow_html=True)

# ─── Session State Init ──────────────────────────────────────────────────────────
for key, default in {
    "result": None,
    "chat_history": [],
    "processing": False,
    "pipeline_done": False,
    "pipeline_steps": {},
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ─── Helpers ────────────────────────────────────────────────────────────────────
def step_status(steps: dict, key: str) -> str:
    s = steps.get(key, "pending")
    if s == "active":  return "dot-active"
    if s == "done":    return "dot-done"
    return "dot-pending"

def render_step_bar(label: str, key: str, icon: str):
    css = step_status(st.session_state.pipeline_steps, key)
    st.markdown(f"""
    <div class="status-bar">
        <div class="status-dot {css}"></div>
        <span>{icon} {label}</span>
    </div>""", unsafe_allow_html=True)

# ─── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="hero-title" style="font-size:1.6rem">🎬 AI<br>Video</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">Meeting Intelligence</div>', unsafe_allow_html=True)
    st.markdown("---")

    st.markdown('<span class="badge badge-purple">Input Source</span>', unsafe_allow_html=True)
    input_mode = st.radio("Choose Input Mode", ["URL / Local Path", "Upload File"], horizontal=True, label_visibility="collapsed")

    source = ""
    if input_mode == "Upload File":
        uploaded_file = st.file_uploader("Upload audio/video file", type=["mp4", "mp3", "wav", "m4a", "webm", "mkv"])
        if uploaded_file is not None:
            os.makedirs("uploaded_files", exist_ok=True)
            saved_file_path = os.path.join("uploaded_files", uploaded_file.name)
            with open(saved_file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            source = saved_file_path
            st.success(f"Uploaded: {uploaded_file.name}")
    else:
        source = st.text_input("YouTube URL or File Path", placeholder="https://youtube.com/watch?v=... or path/to/file.mp4")
        st.caption("💡 *Cloud note: If YouTube blocks direct download on this server, switch to 'Upload File'.*")

    language = st.selectbox("Language", ["english", "hinglish"], index=0)

    has_sarvam = bool(os.getenv("SARVAM_API_KEY"))
    has_mistral = bool(os.getenv("MISTRAL_API_KEY"))

    with st.expander("⚙️ Settings & API Keys", expanded=not (has_sarvam or has_mistral)):
        if has_sarvam:
            st.markdown('<small style="color:#10b981;">✓ Sarvam API Key connected (secured)</small>', unsafe_allow_html=True)
        sarvam_key_val = st.text_input(
            "Sarvam API Key",
            value="",
            type="password",
            placeholder="Connected via Server" if has_sarvam else "Enter your Sarvam API Key",
            help="Your key stays secure on the server. If connected, you don't need to enter anything. Enter a custom key only if you wish to override.",
        )
        if sarvam_key_val.strip():
            os.environ["SARVAM_API_KEY"] = sarvam_key_val.strip()

        if has_mistral:
            st.markdown('<small style="color:#10b981;">✓ Mistral API Key connected (secured)</small>', unsafe_allow_html=True)
        mistral_key_val = st.text_input(
            "Mistral API Key (Optional)",
            value="",
            type="password",
            placeholder="Connected via Server" if has_mistral else "Enter Mistral API Key",
            help="Optional alternative LLM from console.mistral.ai",
        )
        if mistral_key_val.strip():
            os.environ["MISTRAL_API_KEY"] = mistral_key_val.strip()

        whisper_model_choice = st.selectbox(
            "Whisper Model",
            ["tiny", "base", "small", "medium"],
            index=0,
            help="'tiny' is recommended for fast CPU execution (3x faster). 'base' has slightly higher accuracy.",
        )
        os.environ["WHISPER_MODEL"] = whisper_model_choice

        active_llm = "Mistral" if os.getenv("MISTRAL_API_KEY") else ("Sarvam" if os.getenv("SARVAM_API_KEY") else "None")
        st.markdown(f'<small style="color:var(--text-muted)">Active LLM: <b>{active_llm}</b></small>', unsafe_allow_html=True)

        ffmpeg_installed = bool(shutil.which("ffmpeg"))
        if ffmpeg_installed:
            st.markdown('<small style="color:#10b981;">✓ FFmpeg detected</small>', unsafe_allow_html=True)
        else:
            st.markdown('<small style="color:#ef4444;">⚠️ FFmpeg not found in PATH</small>', unsafe_allow_html=True)

    run_btn = st.button("⚡  Analyse", use_container_width=True)

    if st.session_state.pipeline_done:
        st.markdown("---")
        st.markdown('<span class="badge badge-green">Pipeline Status</span>', unsafe_allow_html=True)
        for step, icon, label in [
            ("audio",      "🔊", "Audio Processing"),
            ("transcript", "📝", "Transcription"),
            ("title",      "🏷️", "Title Generation"),
            ("summary",    "📋", "Summarisation"),
            ("extract",    "🔍", "Extraction"),
            ("rag",        "🧠", "RAG Engine"),
        ]:
            render_step_bar(label, step, icon)

# ─── Main Area ──────────────────────────────────────────────────────────────────
st.markdown('<div class="hero-title">AI Video Assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Transcribe · Summarise · Chat with your meetings</div>', unsafe_allow_html=True)
st.markdown("---")

# ── Run Pipeline ────────────────────────────────────────────────────────────────
if run_btn:
    if not source.strip():
        st.error("Please enter a YouTube URL, local file path, or upload a media file.")
    elif not os.getenv("MISTRAL_API_KEY") and not os.getenv("SARVAM_API_KEY"):
        st.error("🔑 API Key required! Please enter your Sarvam API Key or Mistral API Key in the sidebar '⚙️ Settings & API Keys' or in your .env file.")
    elif language == "hinglish" and not os.getenv("SARVAM_API_KEY"):
        st.error("🔑 Sarvam API Key is required for Hinglish translation. Please enter it in the sidebar settings.")
    else:
        st.session_state.pipeline_done = False
        st.session_state.result = None
        st.session_state.chat_history = []
        st.session_state.pipeline_steps = {}

        try:
            with st.status("🎬 Processing Video...", expanded=True) as status_box:
                transcript = None
                is_youtube = source.startswith("http://") or source.startswith("https://")
                if is_youtube:
                    st.write("🔍 Checking for direct YouTube transcript (fast cloud bypass)...")
                    transcript = fetch_youtube_transcript(source)
                    if transcript:
                        st.write(f"✓ Retrieved transcript directly ({len(transcript)} characters) — avoided cloud video download!")

                if not transcript:
                    st.write("🔊 **Step 1/2**: Downloading & extracting audio...")
                    chunks = process_input(source)
                    st.write(f"✓ Audio extracted ({len(chunks)} chunk(s))")

                    st.write(f"📝 **Step 2/2**: Transcribing speech ({language})...")
                    transcript = transcribe_all(chunks, language)
                    st.write(f"✓ Transcription complete ({len(transcript)} characters)")

                st.write("⚡ **Step 3/4**: Generating title, summary, action items & chat index in parallel...")
                with ThreadPoolExecutor(max_workers=6) as executor:
                    fut_title = executor.submit(generate_title, transcript)
                    fut_summary = executor.submit(summarize, transcript)
                    fut_action = executor.submit(extract_action_items, transcript)
                    fut_decisions = executor.submit(extract_key_decisions, transcript)
                    fut_questions = executor.submit(extract_questions, transcript)
                    fut_rag = executor.submit(build_rag_chain, transcript)

                    title = fut_title.result()
                    st.write(f"✓ Title: **{title}**")

                    summary = fut_summary.result()
                    st.write("✓ Summary ready!")

                    action_items = fut_action.result()
                    decisions = fut_decisions.result()
                    questions = fut_questions.result()
                    st.write("✓ Action items & decisions extracted!")

                    st.write("🧠 **Step 4/4**: Indexing knowledge base for chat...")
                    rag_chain = fut_rag.result()
                    st.write("✓ RAG chat engine ready!")

                status_box.update(label="✅ Analysis Complete!", state="complete", expanded=False)

            st.session_state.result = {
                "title": title,
                "transcript": transcript,
                "summary": summary,
                "action_items": action_items,
                "key_decisions": decisions,
                "open_questions": questions,
                "rag_chain": rag_chain,
            }
            st.session_state.pipeline_done = True
            time.sleep(0.3)
            st.rerun()

        except Exception as e:
            err_text = str(e)
            if any(term in err_text.lower() for term in ["quota", "credit", "402", "429", "insufficient", "balance", "rate_limit"]):
                st.error("""
                💳 **Demo AI Credits Exhausted**
                
                The server's pre-configured Sarvam AI credit limit has been reached.
                
                👉 **How to continue testing:**
                1. Expand **⚙️ Settings & API Keys** in the left sidebar.
                2. Enter your own free API key from [Sarvam AI](https://dashboard.sarvam.ai/) or [Mistral AI](https://console.mistral.ai/).
                3. Click **⚡ Analyse** to run with your key!
                """)
            else:
                st.error(f"❌ Error during processing: {e}")

# ── Results ──────────────────────────────────────────────────────────────────────
if st.session_state.result:
    r = st.session_state.result

    # Title banner
    st.markdown(f"""
    <div class="card">
        <div class="card-title">📌 Session Title</div>
        <div style="font-family:'Syne',sans-serif;font-size:1.4rem;font-weight:700;color:var(--text)">
            {r['title']}
        </div>
    </div>""", unsafe_allow_html=True)

    # Top row: summary + transcript
    col1, col2 = st.columns([3, 2], gap="medium")

    with col1:
        st.markdown(f"""
        <div class="card">
            <div class="card-title">📋 Summary</div>
            <div class="card-content">{r['summary']}</div>
        </div>""", unsafe_allow_html=True)

    with col2:
        with st.expander("📝 Full Transcript", expanded=False):
            st.markdown(f'<div class="transcript-box">{r["transcript"]}</div>', unsafe_allow_html=True)

    # Second row: action items | decisions | questions
    c1, c2, c3 = st.columns(3, gap="medium")

    with c1:
        st.markdown(f"""
        <div class="card">
            <div class="card-title">✅ Action Items</div>
            <div class="card-content">{r['action_items']}</div>
        </div>""", unsafe_allow_html=True)

    with c2:
        st.markdown(f"""
        <div class="card">
            <div class="card-title">🔑 Key Decisions</div>
            <div class="card-content">{r['key_decisions']}</div>
        </div>""", unsafe_allow_html=True)

    with c3:
        st.markdown(f"""
        <div class="card">
            <div class="card-title">❓ Open Questions</div>
            <div class="card-content">{r['open_questions']}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # ── RAG Chat ──────────────────────────────────────────────────────────────
    st.markdown('<div style="font-family:\'Syne\',sans-serif;font-size:1.2rem;font-weight:700;margin-bottom:1rem">💬 Chat with your Meeting</div>', unsafe_allow_html=True)

    # Chat history display
    if st.session_state.chat_history:
        chat_html = '<div class="chat-container">'
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                chat_html += f"""
                <div class="chat-msg" style="align-items:flex-end">
                    <span class="chat-label user-label">You</span>
                    <div class="chat-bubble user-bubble">{msg['content']}</div>
                </div>"""
            else:
                chat_html += f"""
                <div class="chat-msg" style="align-items:flex-start">
                    <span class="chat-label bot-label">🤖 Assistant</span>
                    <div class="chat-bubble bot-bubble">{msg['content']}</div>
                </div>"""
        chat_html += '</div>'
        st.markdown(chat_html, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="card" style="text-align:center;padding:2rem">
            <div style="font-size:2rem;margin-bottom:0.5rem">💬</div>
            <div style="color:var(--text-muted);font-size:0.85rem">Ask anything about your meeting transcript</div>
        </div>""", unsafe_allow_html=True)

    # Chat input
    chat_col1, chat_col2 = st.columns([5, 1], gap="small")
    with chat_col1:
        user_input = st.text_input("Your question", placeholder="What were the main decisions made?", label_visibility="collapsed")
    with chat_col2:
        send_btn = st.button("Send →", use_container_width=True)

    if send_btn and user_input.strip():
        q_text = user_input.strip()
        st.session_state.chat_history.append({"role": "user", "content": q_text})

        stream_placeholder = st.empty()
        full_reply = ""
        try:
            for token in stream_question(r["rag_chain"], q_text):
                full_reply += token
                stream_placeholder.markdown(f"""
                <div class="chat-container">
                    <div class="chat-msg" style="align-items:flex-start">
                        <span class="chat-label bot-label">🤖 Assistant</span>
                        <div class="chat-bubble bot-bubble">{full_reply} ▌</div>
                    </div>
                </div>""", unsafe_allow_html=True)

            st.session_state.chat_history.append({"role": "assistant", "content": full_reply})
            st.rerun()
        except Exception as e:
            err_str = str(e).lower()
            if any(term in err_str for term in ["quota", "credit", "402", "429", "insufficient", "balance", "rate_limit"]):
                credit_msg = (
                    "💳 **Demo Credits Exhausted**: The server's pre-configured Sarvam AI credits have been reached.\n\n"
                    "👉 To continue chatting, please enter a free API key from [Sarvam AI](https://dashboard.sarvam.ai/) "
                    "or [Mistral AI](https://console.mistral.ai/) in the sidebar settings."
                )
                st.session_state.chat_history.append({"role": "assistant", "content": credit_msg})
            else:
                st.session_state.chat_history.append({"role": "assistant", "content": f"⚠️ Could not generate answer: {e}"})
            st.rerun()

    if st.session_state.chat_history:
        if st.button("🗑️ Clear Chat", type="secondary"):
            st.session_state.chat_history = []
            st.rerun()

else:
    # Empty state
    st.markdown("""
    <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;padding:5rem 2rem;text-align:center">
        <div style="font-size:4rem;margin-bottom:1rem">🎬</div>
        <div style="font-family:'Syne',sans-serif;font-size:1.5rem;font-weight:700;color:var(--text);margin-bottom:0.5rem">
            Ready to Analyse
        </div>
        <div style="color:var(--text-muted);font-size:0.85rem;max-width:380px;line-height:1.7">
            Paste a YouTube URL or local file path in the sidebar, choose your language, and hit <strong>Analyse</strong> to get started.
        </div>
        <div style="margin-top:2rem;display:flex;gap:1rem;flex-wrap:wrap;justify-content:center">
            <span class="badge badge-purple">Transcription</span>
            <span class="badge badge-cyan">Summarisation</span>
            <span class="badge badge-green">RAG Chat</span>
        </div>
    </div>""", unsafe_allow_html=True)