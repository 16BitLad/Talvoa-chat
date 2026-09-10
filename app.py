import os
import json
import uuid
import time
from datetime import datetime
import streamlit as st
from google import genai
from google.genai import types

# 1. Page Configuration
st.set_page_config(
    page_title="WITTALVA – Fellow Guide",
    page_icon="🧭",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# 2. JSON Storage Handlers & History Limit (Max 10)
STORAGE_FILE = "chats_history.json"
MAX_HISTORY_COUNT = 10

def trim_chats_history(data):
    """Behält strikt nur die letzten 10 Chats bei."""
    if len(data) > MAX_HISTORY_COUNT:
        keys_to_keep = list(data.keys())[-MAX_HISTORY_COUNT:]
        return {k: data[k] for k in keys_to_keep}
    return data

def load_stored_chats():
    """Lädt gespeicherte Chats aus der lokalen chats_history.json Datei."""
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return trim_chats_history(data)
        except Exception:
            return {}
    return {}

def save_stored_chats(data):
    """Speichert die Chats dauerhaft in chats_history.json."""
    try:
        trimmed_data = trim_chats_history(data)
        with open(STORAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(trimmed_data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

# 3. Multi-Language UI Dictionary & Automatic Device Detection
UI_TEXTS = {
    "de": {
        "subtitle": "Ihr Wegbegleiter und Berater für alltägliche Fragen",
        "placeholder": "Wie kann ich helfen?",
        "new_chat": "➕ Neuer Chat",
        "history_show": "📜 Chat-Verlauf",
        "history_hide": "▲ Verlauf ausblenden",
        "prev_conv": "Bisherige Gespräche",
        "no_conv": "Noch keine bisherigen Gespräche gespeichert.",
    },
    "en": {
        "subtitle": "Your fellow guide and advisor through day-to-day matters",
        "placeholder": "How can I help?",
        "new_chat": "➕ Open new chat",
        "history_show": "📜 Chat history",
        "history_hide": "▲ Hide history",
        "prev_conv": "Previous Conversations",
        "no_conv": "No previous conversations stored yet.",
    },
    "es": {
        "subtitle": "Tu guía y asesor para los asuntos cotidianos",
        "placeholder": "¿En qué puedo ayudarte?",
        "new_chat": "➕ Nuevo chat",
        "history_show": "📜 Historial de chats",
        "history_hide": "▲ Ocultar historial",
        "prev_conv": "Conversaciones anteriores",
        "no_conv": "Aún no hay conversaciones previas guardadas.",
    },
    "fr": {
        "subtitle": "Votre guide et conseiller pour les affaires du quotidien",
        "placeholder": "Comment puis-je vous aider ?",
        "new_chat": "➕ Nouveau chat",
        "history_show": "📜 Historique des discussions",
        "history_hide": "▲ Masquer l'historique",
        "prev_conv": "Conversations précédentes",
        "no_conv": "Aucune conversation précédente enregistrée.",
    }
}

def detect_device_language():
    try:
        lang_header = st.context.headers.get("Accept-Language", "")
        if lang_header:
            primary = lang_header.split(",")[0].split("-")[0].lower()
            if primary in UI_TEXTS:
                return primary
    except Exception:
        pass
    return "de"

user_lang = detect_device_language()
txt = UI_TEXTS[user_lang]

# 4. State Initializations
if "all_chats" not in st.session_state:
    st.session_state.all_chats = load_stored_chats()

if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None

if "show_history" not in st.session_state:
    st.session_state.show_history = False

if "editing_idx" not in st.session_state:
    st.session_state.editing_idx = None

if "regenerate_prompt" not in st.session_state:
    st.session_state.regenerate_prompt = None

def toggle_history():
    st.session_state.show_history = not st.session_state.show_history

def start_new_chat():
    st.session_state.current_chat_id = None
    st.session_state.show_history = False
    st.session_state.editing_idx = None

def select_chat(chat_id):
    st.session_state.current_chat_id = chat_id
    st.session_state.show_history = False
    st.session_state.editing_idx = None

def delete_message(idx):
    if st.session_state.current_chat_id in st.session_state.all_chats:
        st.session_state.all_chats[st.session_state.current_chat_id]["messages"].pop(idx)
        save_stored_chats(st.session_state.all_chats)
        st.session_state.editing_idx = None

def set_editing_message(idx):
    st.session_state.editing_idx = idx

def trigger_regenerate(idx):
    chat_id = st.session_state.current_chat_id
    if chat_id in st.session_state.all_chats:
        msgs = st.session_state.all_chats[chat_id]["messages"]
        # Falls eine Assistant-Nachricht aktualisiert wird, nehmen wir die vorherige User-Nachricht
        if msgs[idx]["role"] == "assistant":
            if idx > 0 and msgs[idx-1]["role"] == "user":
                target_prompt = msgs[idx-1]["content"]
                # Entferne die alten Nachrichten ab diesem Stand
                st.session_state.all_chats[chat_id]["messages"] = msgs[:idx]
                st.session_state.regenerate_prompt = target_prompt
        else:
            target_prompt = msgs[idx]["content"]
            st.session_state.all_chats[chat_id]["messages"] = msgs[:idx]
            st.session_state.regenerate_prompt = target_prompt
        save_stored_chats(st.session_state.all_chats)

current_messages = []
if st.session_state.current_chat_id and st.session_state.current_chat_id in st.session_state.all_chats:
    current_messages = st.session_state.all_chats[st.session_state.current_chat_id]["messages"]
else:
    st.session_state.current_chat_id = None

chat_window_height = "calc(100vh - 460px)" if st.session_state.show_history else "calc(100vh - 210px)"

# 5. Custom CSS: Art-Déco, Dark-Theme & Hover-Aktions-Icons
st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Six+Caps&display=swap');

    .stApp {{ 
        background-color: #18181b !important; 
        color: #f4f4f5 !important; 
    }}
    header, footer {{ 
        visibility: hidden !important; 
        display: none !important; 
    }}
    .block-container {{ 
        padding-top: 0.8rem !important; 
        padding-bottom: 0 !important; 
        max-width: 750px !important; 
        text-align: center;
    }}

    /* HEADER TITEL */
    .header-title-container {{
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 0.4rem !important;
        flex-wrap: wrap !important;
        margin-bottom: 0.1rem !important;
    }}
    .wittalva-title {{
        font-family: 'Six Caps', 'Arial Narrow', sans-serif !important;
        font-size: 4.2rem !important;
        font-weight: 400 !important;
        letter-spacing: 0.12em !important;
        text-transform: uppercase !important;
        line-height: 0.85 !important;
        color: #ffffff !important;
        display: inline-block !important;
    }}
    .rune-divider {{
        color: #52525b !important;
        font-size: 2.2rem !important;
        font-weight: 300 !important;
        line-height: 0.85 !important;
        margin: 0 0.2rem !important;
    }}
    .rune-text {{
        font-family: 'Segoe UI Historic', 'Noto Sans Runic', sans-serif !important;
        font-size: 2.3rem !important;
        letter-spacing: 0.15em !important;
        color: #a1a1aa !important;
        font-weight: normal !important;
        line-height: 0.85 !important;
        display: inline-block !important;
    }}

    /* GLOBAL BUTTON DEFAULT */
    .stButton > button,
    button[data-testid="stBaseButton-secondary"] {{
        background-color: #202024 !important;
        color: #e4e4e7 !important;
        border: 1px solid #2e2e33 !important;
        border-radius: 8px !important;
        font-size: 0.85rem !important;
        transition: all 0.2s ease !important;
    }}
    .stButton > button:hover,
    button[data-testid="stBaseButton-secondary"]:hover {{
        background-color: #2a2a30 !important;
        border-color: #52525b !important;
        color: #ffffff !important;
    }}

    /* CHAT FORM */
    div[data-testid="stForm"] {{
        background-color: #27272a !important;
        border: 1px solid #3f3f46 !important;
        border-radius: 12px !important;
        padding: 0.3rem 0.5rem !important;
        margin: 0.4rem auto 0.6rem auto !important;
    }}
    div[data-testid="stForm"] [data-testid="stHorizontalBlock"] {{
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
        gap: 0.4rem !important;
    }}
    div[data-testid="stForm"] [data-testid="stHorizontalBlock"] > div:first-child {{
        flex: 1 1 auto !important;
        min-width: 0 !important;
    }}
    div[data-testid="stForm"] [data-testid="stHorizontalBlock"] > div:last-child {{
        flex: 0 0 42px !important;
        width: 42px !important;
        min-width: 42px !important;
    }}

    div[data-testid="stTextInput"],
    div[data-testid="stTextInput"] div[data-baseweb="base-input"],
    div[data-testid="stTextInput"] div[data-baseweb="input"],
    div[data-testid="stTextInput"] input {{
        background-color: #27272a !important;
        color: #ffffff !important;
        border: none !important;
        box-shadow: none !important;
        font-size: 0.95rem !important;
    }}
    div[data-testid="stTextInput"] input::placeholder {{
        color: #a1a1aa !important;
        opacity: 1 !important;
    }}
    div[data-testid="stInputInstructions"] {{
        display: none !important;
    }}

    div[data-testid="stFormSubmitButton"] button {{
        background-color: #3f3f46 !important;
        color: #ffffff !important;
        border: 1px solid #52525b !important;
        border-radius: 8px !important;
        font-size: 1.2rem !important;
        height: 40px !important;
        min-height: 40px !important;
        width: 100% !important;
        padding: 0 !important;
    }}

    /* ACTION BUTTONS (NEU CHAT / HISTORY) */
    div[data-testid="stHorizontalBlock"]:not(div[data-testid="stForm"] *):not(.msg-actions *) {{
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        justify-content: center !important;
        align-items: center !important;
        max-width: 340px !important;
        width: 100% !important;
        margin: 0.2rem auto 0.6rem auto !important;
        gap: 0.5rem !important;
    }}

    /* CHAT BUBBLES */
    div[data-testid="stChatMessage"] {{
        padding: 0.6rem 0.9rem !important;
        margin-bottom: 0.6rem !important;
        border-radius: 12px !important;
        width: fit-content !important;
        max-width: 88% !important;
        position: relative !important;
    }}
    div[data-testid="stChatMessage"] * {{
        color: #f4f4f5 !important;
        text-align: left !important;
    }}

    div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {{
        background-color: #27272a !important;
        border: 1px solid #3f3f46 !important;
        border-bottom-left-radius: 3px !important;
        margin-left: 0 !important;
        margin-right: auto !important;
    }}

    div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {{
        background-color: #1e1e22 !important;
        border: 1px solid #333338 !important;
        border-bottom-right-radius: 3px !important;
        margin-left: auto !important;
        margin-right: 0 !important;
    }}

    [data-testid^="stChatMessageAvatar"] {{
        display: none !important;
    }}

    /* HOVER ACTION BUTTONS IN CHAT MESSAGES */
    .msg-actions {{
        opacity: 0;
        visibility: hidden;
        transition: opacity 0.2s ease, visibility 0.2s ease;
        margin-top: 0.3rem;
        padding-top: 0.2rem;
        border-top: 1px solid #27272a;
    }}
    div[data-testid="stChatMessage"]:hover .msg-actions {{
        opacity: 1;
        visibility: visible;
    }}
    .msg-actions button {{
        padding: 0.1rem 0.3rem !important;
        font-size: 0.75rem !important;
        height: 24px !important;
        min-height: 24px !important;
        line-height: 1 !important;
        border-radius: 4px !important;
        background-color: #18181b !important;
        border: 1px solid #3f3f46 !important;
    }}
    .msg-actions button:hover {{
        background-color: #3f3f46 !important;
        color: #ffffff !important;
    }}

    /* Scroll Container */
    div[data-testid="stVerticalBlockBorderWrapper"]:not(:has(.history-dropdown-box)) {{
        height: {chat_window_height} !important;
        min-height: {chat_window_height} !important;
        max-height: {chat_window_height} !important;
        background-color: #141416 !important;
        border: 1px solid #27272a !important;
        border-radius: 12px !important;
        padding: 0.8rem !important;
        overflow-y: auto !important;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

# 6. Header Section
st.markdown(
    f"""
    <div style="text-align: center; margin-bottom: 0.1rem;">
        <div class="header-title-container">
            <span class="wittalva-title">WITTALVA</span>
            <span class="rune-divider">/</span>
            <span class="rune-text">ᚹᛁᛏᛏᚨᛚᚹᚨ</span>
        </div>
        <p style="color: #a1a1aa; font-size: 0.95rem; margin-top: 0.1rem;">{txt["subtitle"]}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# 7. Form Input Field
with st.form(key="chat_input_form", clear_on_submit=True):
    col_input, col_submit = st.columns([9, 1])
    with col_input:
        user_prompt = st.text_input(
            "Input",
            placeholder=txt["placeholder"],
            label_visibility="collapsed",
            key="user_text_input",
        )
    with col_submit:
        submitted = st.form_submit_button("↑")

# 8. Action Buttons Row
col_b1, col_b2 = st.columns(2)
with col_b1:
    st.button(txt["new_chat"], use_container_width=True, key="btn_global_new", on_click=start_new_chat)
with col_b2:
    hist_label = txt["history_hide"] if st.session_state.show_history else txt["history_show"]
    st.button(hist_label, use_container_width=True, key="btn_global_hist", on_click=toggle_history)

# 9. History Dropdown
if st.session_state.show_history:
    with st.container():
        st.markdown(
            f'<p style="color: #a1a1aa; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 0.4rem; font-weight: 600; text-align: left;">{txt["prev_conv"]}</p>',
            unsafe_allow_html=True,
        )
        if len(st.session_state.all_chats) == 0:
            st.markdown(f"<p style='color: #71717a; font-size: 0.85rem; margin: 0; text-align: left;'>{txt['no_conv']}</p>", unsafe_allow_html=True)
        else:
            for c_id, c_data in reversed(list(st.session_state.all_chats.items())):
                btn_label = f"💬 {c_data['title']}   •   🕒 {c_data['timestamp']}"
                st.button(
                    btn_label, 
                    key=f"hist_select_{c_id}", 
                    use_container_width=True,
                    on_click=select_chat,
                    args=(c_id,)
                )

# API Configuration
api_key = os.environ.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("GEMINI_API_KEY is not configured in secrets.")
    st.stop()
client = genai.Client(api_key=api_key)

# Helper function to render chat message content with hover action icons
def render_chat_message(msg, idx):
    with st.chat_message(msg["role"]):
        if msg.get("duration"):
            st.markdown(
                f'<div style="font-size: 0.65rem; color: #71717a; margin-bottom: 0.2rem; font-family: inherit;">{msg["duration"]}</div>',
                unsafe_allow_html=True,
            )
        
        # Inline-Bearbeitung der Nachricht
        if st.session_state.editing_idx == idx:
            edited_text = st.text_input("Nachricht bearbeiten", value=msg["content"], key=f"edit_val_{idx}")
            col_save, col_cancel = st.columns(2)
            with col_save:
                if st.button("Speichern", key=f"save_btn_{idx}"):
                    st.session_state.all_chats[st.session_state.current_chat_id]["messages"][idx]["content"] = edited_text
                    save_stored_chats(st.session_state.all_chats)
                    st.session_state.editing_idx = None
                    st.rerun()
            with col_cancel:
                if st.button("Abbrechen", key=f"cancel_btn_{idx}"):
                    st.session_state.editing_idx = None
                    st.rerun()
        else:
            st.markdown(msg["content"])
            
            # Hover-Aktionsleiste
            st.markdown('<div class="msg-actions">', unsafe_allow_html=True)
            ac1, ac2, ac3, _ = st.columns([1, 1, 1, 7])
            with ac1:
                st.button("🔄", key=f"act_ref_{idx}", help="Aktualisieren", on_click=trigger_regenerate, args=(idx,))
            with ac2:
                st.button("✏️", key=f"act_edit_{idx}", help="Bearbeiten", on_click=set_editing_message, args=(idx,))
            with ac3:
                st.button("🗑️", key=f"act_del_{idx}", help="Löschen", on_click=delete_message, args=(idx,))
            st.markdown('</div>', unsafe_allow_html=True)

# 10. Handle Form Submission or Regenerate Request
active_prompt = None
if submitted and user_prompt and len(user_prompt.strip()) > 0:
    active_prompt = user_prompt.strip()
elif st.session_state.regenerate_prompt:
    active_prompt = st.session_state.regenerate_prompt
    st.session_state.regenerate_prompt = None

if active_prompt:
    st.session_state.show_history = False
    now_str = datetime.now().strftime("%d.%m.%Y, %H:%M")

    if not st.session_state.current_chat_id:
        new_id = str(uuid.uuid4())[:8]
        title = active_prompt[:35] + "..." if len(active_prompt) > 35 else active_prompt
        st.session_state.all_chats[new_id] = {
            "title": title,
            "timestamp": now_str,
            "messages": [],
        }
        st.session_state.current_chat_id = new_id

    st.session_state.all_chats = trim_chats_history(st.session_state.all_chats)

    st.session_state.all_chats[st.session_state.current_chat_id]["messages"].append(
        {"role": "user", "content": active_prompt}
    )
    save_stored_chats(st.session_state.all_chats)

    active_history = st.session_state.all_chats[st.session_state.current_chat_id]["messages"]

    api_contents = []
    for msg in active_history[:-1]:
        api_role = "model" if msg["role"] == "assistant" else "user"
        api_contents.append(
            types.Content(
                role=api_role,
                parts=[types.Part.from_text(text=msg["content"])],
            )
        )

    wrapped_prompt = f"<untrusted_input>\n{active_prompt}\n</untrusted_input>"
    api_contents.append(
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=wrapped_prompt)],
        )
    )

    chat_box = st.container(border=True)
    with chat_box:
        for idx, msg in enumerate(active_history[:-1]):
            render_chat_message(msg, idx)
        
        with st.chat_message("user"):
            st.markdown(active_prompt)

        with st.chat_message("assistant"):
            start_time = time.time()
            timer_placeholder = st.empty()
            message_placeholder = st.empty()

            timer_placeholder.markdown(
                '<div style="font-size: 0.65rem; color: #71717a; margin-bottom: 0.2rem; font-family: inherit;">0.0s</div>',
                unsafe_allow_html=True,
            )

            full_response = ""

            try:
                response_stream = client.models.generate_content_stream(
                    model="gemini-3.6-flash",
                    contents=api_contents,
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        top_p=0.8,
                        thinking_config=types.ThinkingConfig(
                            thinking_budget=1024
                        ),
                    ),
                )
                for chunk in response_stream:
                    elapsed = time.time() - start_time
                    timer_placeholder.markdown(
                        f'<div style="font-size: 0.65rem; color: #71717a; margin-bottom: 0.2rem; font-family: inherit;">{elapsed:.1f}s</div>',
                        unsafe_allow_html=True,
                    )

                    if chunk.candidates and chunk.candidates[0].content.parts:
                        for part in chunk.candidates[0].content.parts:
                            if getattr(part, "thought", False):
                                continue
                            if part.text:
                                full_response += part.text
                                message_placeholder.markdown(full_response + "▌")
                    elif hasattr(chunk, "text") and chunk.text:
                        full_response += chunk.text
                        message_placeholder.markdown(full_response + "▌")

                total_duration = f"{time.time() - start_time:.1f}s"
                timer_placeholder.markdown(
                    f'<div style="font-size: 0.65rem; color: #71717a; margin-bottom: 0.2rem; font-family: inherit;">{total_duration}</div>',
                    unsafe_allow_html=True,
                )
                message_placeholder.markdown(full_response)
            except Exception as e:
                st.error(f"API Error: {e}")

    if full_response:
        st.session_state.all_chats[st.session_state.current_chat_id]["messages"].append(
            {"role": "assistant", "content": full_response, "duration": total_duration}
        )
        save_stored_chats(st.session_state.all_chats)
        st.rerun()

# 11. Render Persistent Output Window
elif len(current_messages) > 0:
    chat_box = st.container(border=True)
    with chat_box:
        for idx, msg in enumerate(current_messages):
            render_chat_message(msg, idx)
