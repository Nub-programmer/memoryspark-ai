import json
import os
import html
import re
from collections import Counter
from datetime import datetime
from statistics import mean
from typing import Any, Dict, List, Optional, Sequence, Tuple

import plotly.express as px
import streamlit as st

try:
    from google import genai
    from google.genai import types
except Exception:  # pragma: no cover - dependency fallback during setup
    genai = None
    types = None


THEMES = ["Family", "Childhood", "School", "Travel", "Friendship", "Celebration", "Career", "Other"]
SENTIMENT_LABELS = ["Positive", "Neutral", "Reflective", "Melancholic"]

THEME_KEYWORDS = {
    "Family": ["mother", "father", "mom", "dad", "sister", "brother", "grandmother", "grandfather", "family", "home"],
    "Childhood": ["child", "children", "play", "toy", "young", "kid", "schoolyard", "summer", "birthday", "schoolbag"],
    "School": ["school", "teacher", "lesson", "classroom", "study", "college", "university", "exam", "graduation", "homework"],
    "Travel": ["trip", "travel", "journey", "train", "plane", "airport", "road", "vacation", "visit", "beach", "hotel"],
    "Friendship": ["friend", "friends", "best friend", "classmate", "neighbor", "buddy", "companions", "together", "pal"],
    "Celebration": ["birthday", "wedding", "holiday", "party", "celebration", "anniversary", "festival", "ceremony", "gathering"],
    "Career": ["job", "work", "office", "career", "boss", "team", "project", "promotion", "shift", "retirement", "colleague"],
}

SENSORY_KEYWORDS = {
    "sounds": ["sound", "music", "voice", "voices", "laugh", "laughs", "noise", "bell", "radio", "song", "silence", "rain"],
    "smells": ["smell", "scent", "odor", "perfume", "baking", "coffee", "soap", "rain", "smoke", "fresh", "bread"],
    "sights": ["see", "saw", "look", "light", "color", "colors", "bright", "dark", "window", "picture", "garden", "street", "sun"],
    "objects": ["chair", "table", "dress", "car", "book", "toy", "cup", "photo", "letter", "watch", "ring", "house", "pencil"],
}

EMOTIONAL_KEYWORDS = [
    "happy",
    "sad",
    "angry",
    "proud",
    "worried",
    "safe",
    "loved",
    "lonely",
    "excited",
    "calm",
    "afraid",
    "grateful",
    "peaceful",
    "hopeful",
    "relieved",
    "ashamed",
    "frustrated",
    "comforted",
]

PEOPLE_KEYWORDS = [
    "mother",
    "father",
    "mom",
    "dad",
    "sister",
    "brother",
    "grandmother",
    "grandfather",
    "friend",
    "teacher",
    "neighbor",
    "partner",
    "spouse",
    "child",
    "children",
    "coworker",
    "colleague",
]

PLACE_KEYWORDS = [
    "home",
    "house",
    "street",
    "room",
    "garden",
    "school",
    "church",
    "park",
    "kitchen",
    "city",
    "village",
    "hospital",
    "station",
    "beach",
    "office",
    "classroom",
    "yard",
    "store",
]

POSITIVE_KEYWORDS = ["joy", "joyful", "smile", "smiled", "warm", "lovely", "wonderful", "peaceful", "grateful", "hopeful", "happy", "glad"]
REFLECTIVE_KEYWORDS = ["remember", "recall", "think", "thought", "reflect", "meaning", "important", "learn", "realized", "realise", "notice"]
MELANCHOLIC_KEYWORDS = ["miss", "lonely", "lost", "sad", "sadness", "grief", "tear", "tears", "empty", "ache", "quiet", "faded"]

LOCAL_STORY_SPARKS = {
    "Family": "In the quiet rhythm of familiar voices, the memory opens like a warm room.",
    "Childhood": "Before the day grew complicated, there was a small moment that still glows softly.",
    "School": "In the steady light of learning, something lasting began to take shape.",
    "Travel": "Somewhere between departure and return, the world felt wider than before.",
    "Friendship": "Between shared laughter and ordinary time, something lasting was being built.",
    "Celebration": "Under the gentle noise of celebration, the moment carried itself like music.",
    "Career": "Amid the steady pace of work, one memory remained especially clear.",
    "Other": "In the edge of the ordinary, a memory waits with quiet detail.",
}


def configure_page() -> None:
    st.set_page_config(
        page_title="MemorySpark AI",
        page_icon="M",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """
        <style>
        :root {
            --bg: #f5f8fb;
            --panel: #ffffff;
            --panel-alt: #eef3f7;
            --text: #183243;
            --muted: #5f7486;
            --border: #dbe4ec;
            --accent: #356b87;
            --accent-soft: #e6f0f6;
            --success: #2f7a5f;
        }

        .stApp {
            background: linear-gradient(180deg, #f8fbfd 0%, #eef3f7 100%);
            color: var(--text);
        }

        .block-container {
            padding-top: 1.8rem;
            padding-bottom: 2.5rem;
            max-width: 1220px;
        }

        .muted {
            color: var(--muted);
        }

        .badge {
            display: inline-block;
            margin: 0.2rem 0.35rem 0.2rem 0;
            padding: 0.3rem 0.65rem;
            border-radius: 999px;
            background: var(--accent-soft);
            color: var(--accent);
            font-size: 0.88rem;
            font-weight: 600;
        }

        .entry-chip {
            display: inline-block;
            margin: 0.2rem 0.28rem 0.2rem 0;
            padding: 0.22rem 0.5rem;
            border-radius: 999px;
            background: #f2f6f9;
            color: var(--text);
            border: 1px solid var(--border);
            font-size: 0.8rem;
        }

        .note-box {
            border: 1px solid var(--border);
            background: #fbfdff;
            border-radius: 14px;
            padding: 0.85rem 0.95rem;
        }

        .panel-title {
            margin: 0 0 0.35rem 0;
            font-size: 1.05rem;
            color: var(--text);
        }

        .section-shell {
            border: 1px solid var(--border);
            background: var(--panel);
            border-radius: 18px;
            padding: 1rem 1.1rem;
            box-shadow: 0 8px 22px rgba(24, 50, 67, 0.04);
            margin-bottom: 1rem;
        }

        .entry-preview {
            border-left: 3px solid var(--accent);
            padding-left: 0.75rem;
            margin: 0.45rem 0 0.85rem 0;
        }

        .stTextArea textarea {
            background: #ffffff;
        }

        footer {
            visibility: hidden;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def initialize_state() -> None:
    st.session_state.setdefault("memory_journal", [])
    st.session_state.setdefault("selected_entry_id", None)


def load_gemini_api_key() -> str:
    api_key = None
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        st.error(
            "Missing Gemini API Key. Add GEMINI_API_KEY to .streamlit/secrets.toml for Streamlit Cloud or set GEMINI_API_KEY in your local environment."
        )
        st.stop()

    return api_key


@st.cache_resource(show_spinner=False)
def get_gemini_client(api_key: str) -> Optional[Any]:
    if genai is None:
        return None
    return genai.Client(api_key=api_key)


def sanitize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_count(text: str, keywords: Sequence[str]) -> int:
    lowered = text.lower()
    total = 0
    for keyword in keywords:
        pattern = r"\b" + re.escape(keyword) + r"\b"
        total += len(re.findall(pattern, lowered))
    return total


def clamp(value: int, minimum: int = 1, maximum: int = 10) -> int:
    return max(minimum, min(maximum, value))


def extract_json(text: str) -> Dict[str, Any]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start : end + 1]
    return json.loads(cleaned)


def build_prompt(memory_text: str, caregiver_notes: str) -> str:
    theme_choices = ", ".join(THEMES)
    sentiment_choices = ", ".join(SENTIMENT_LABELS)
    return f"""
You are analyzing a reminiscence note for dementia care research.

Return only valid JSON with this schema:
{{
  "primary_theme": one of [{theme_choices}],
  "secondary_themes": array of 0 to 2 values from the same list,
  "theme_reason": short explanation,
  "sentiment": one of [{sentiment_choices}],
  "sentiment_reason": short explanation,
  "sensory_questions": {{
    "sounds": [2 to 3 gentle questions],
    "smells": [2 to 3 gentle questions],
    "sights": [2 to 3 gentle questions],
    "objects": [2 to 3 gentle questions]
  }},
  "emotional_questions": {{
    "feelings": [2 to 3 gentle questions],
    "relationships": [2 to 3 gentle questions],
    "meaning": [2 to 3 gentle questions]
  }},
  "poem": a short poem of 2 to 4 lines inspired by the memory,
  "storytelling_prompt": a short storytelling prompt or sentence starter
}}

Rules:
- Keep language gentle, clinical, and supportive.
- Prefer concrete sensory language.
- Do not mention being an AI.

Memory:
{memory_text}

Caregiver notes:
{caregiver_notes or "None"}
"""


def detect_theme(memory_text: str) -> Tuple[str, List[str], str]:
    lowered = memory_text.lower()
    hits = {theme: normalize_count(lowered, keywords) for theme, keywords in THEME_KEYWORDS.items()}
    ordered = sorted(hits.items(), key=lambda item: item[1], reverse=True)
    primary = ordered[0][0] if ordered and ordered[0][1] > 0 else "Other"
    secondary = [theme for theme, score in ordered[1:3] if score > 0 and theme != primary]
    reason = f"Detected cues most strongly aligned with {primary.lower()}."
    return primary, secondary, reason


def detect_sentiment(memory_text: str) -> Tuple[str, str]:
    lowered = memory_text.lower()
    scores = {
        "Positive": normalize_count(lowered, POSITIVE_KEYWORDS),
        "Neutral": 1 if len(lowered.split()) < 15 else 0,
        "Reflective": normalize_count(lowered, REFLECTIVE_KEYWORDS),
        "Melancholic": normalize_count(lowered, MELANCHOLIC_KEYWORDS),
    }

    best_label = max(scores, key=scores.get)
    if scores[best_label] == 0:
        best_label = "Neutral"

    reason_map = {
        "Positive": "The memory includes language that suggests warmth, gratitude, or pleasure.",
        "Neutral": "The memory reads as descriptive or factual without a strong emotional signal.",
        "Reflective": "The wording suggests observation, meaning-making, or careful recall.",
        "Melancholic": "The wording carries loss, longing, or sadness.",
    }
    return best_label, reason_map[best_label]


def build_questions(theme: str, memory_text: str) -> Dict[str, Dict[str, List[str]]]:
    theme_hint = theme.lower()
    sensory = {
        "sounds": [
            f"What sounds stand out most in this {theme_hint} memory?",
            "Were there voices, music, or background noises that shaped the moment?",
            "Did silence or a particular sound make this memory feel stronger?",
        ],
        "smells": [
            "What smell, if any, comes to mind first?",
            "Was there a familiar scent tied to the place or people?",
            "Did any smell help bring the memory back clearly?",
        ],
        "sights": [
            "What do you remember seeing around you?",
            "Were there colors, lighting, or small visual details that felt important?",
            "What scene would you want someone else to picture?",
        ],
        "objects": [
            "Was there an object that mattered in this moment?",
            "Did anything you touched or held help anchor the memory?",
            "Which item would best represent this experience?",
        ],
    }
    emotional = {
        "feelings": [
            "How did you feel in that moment?",
            "Did those feelings change as the event unfolded?",
            "What feeling returns most strongly when you recall it now?",
        ],
        "relationships": [
            "Who felt important in this memory?",
            "How did other people shape the experience?",
            "Did this moment affect how you felt about anyone involved?",
        ],
        "meaning": [
            "What made this memory important to you?",
            "What does it say about that period of your life?",
            "Why might this moment still matter today?",
        ],
    }
    return {"sensory_questions": sensory, "emotional_questions": emotional}


def build_local_poem(theme: str, memory_text: str) -> str:
    base = LOCAL_STORY_SPARKS.get(theme, LOCAL_STORY_SPARKS["Other"])
    preview = " ".join(sanitize_text(memory_text).split()[:8])
    return "\n".join(
        [
            f"{base}",
            f"A quiet trace of {preview.lower() if preview else 'the moment'} remains.",
            "Softly, the mind returns and holds it close.",
        ]
    )


def build_local_analysis(memory_text: str, caregiver_notes: str) -> Dict[str, Any]:
    theme, secondary, theme_reason = detect_theme(memory_text)
    sentiment, sentiment_reason = detect_sentiment(memory_text)
    lowered = memory_text.lower()
    emotional_refs = normalize_count(lowered, EMOTIONAL_KEYWORDS)
    sensory_refs = sum(normalize_count(lowered, keywords) for keywords in SENSORY_KEYWORDS.values())
    people_refs = normalize_count(lowered, PEOPLE_KEYWORDS)
    place_refs = normalize_count(lowered, PLACE_KEYWORDS)
    detail_total = emotional_refs + sensory_refs + people_refs + place_refs
    word_count = len(sanitize_text(memory_text).split())

    richness_score = clamp(1 + min(3, sensory_refs) + min(2, emotional_refs) + min(2, people_refs) + min(2, place_refs) + (1 if word_count > 35 else 0))
    cognitive_index = max(1, min(100, int(15 + detail_total * 12 + min(20, word_count // 5))))

    questions = build_questions(theme, memory_text)
    poem = build_local_poem(theme, memory_text)
    storytelling_prompt = f"Begin with: 'I still remember when {sanitize_text(memory_text)[:70].rstrip('.')}'"

    return {
        "primary_theme": theme,
        "secondary_themes": secondary,
        "theme_reason": theme_reason,
        "sentiment": sentiment,
        "sentiment_reason": sentiment_reason,
        "richness_breakdown": {
            "emotional_references": emotional_refs,
            "sensory_references": sensory_refs,
            "people_references": people_refs,
            "place_references": place_refs,
        },
        "richness_score": richness_score,
        "cognitive_stimulation_index": cognitive_index,
        "sensory_questions": questions["sensory_questions"],
        "emotional_questions": questions["emotional_questions"],
        "poem": poem,
        "storytelling_prompt": storytelling_prompt,
        "caregiver_notes": caregiver_notes,
    }


def normalize_ai_list(value: Any, allowed: Sequence[str], fallback: List[str]) -> List[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return fallback
    cleaned = []
    for item in value:
        text = sanitize_text(str(item))
        if text in allowed and text not in cleaned:
            cleaned.append(text)
    return cleaned[:2] if cleaned else fallback


def normalize_question_block(value: Any, fallback: Dict[str, List[str]]) -> Dict[str, List[str]]:
    if not isinstance(value, dict):
        return fallback

    normalized: Dict[str, List[str]] = {}
    for key, default_questions in fallback.items():
        items = value.get(key, default_questions)
        if isinstance(items, str):
            items = [items]
        if not isinstance(items, list):
            items = default_questions
        cleaned = [sanitize_text(str(item)) for item in items if sanitize_text(str(item))]
        normalized[key] = cleaned[:3] if cleaned else default_questions
    return normalized


def normalize_ai_response(raw: Dict[str, Any], local: Dict[str, Any], memory_text: str, caregiver_notes: str) -> Dict[str, Any]:
    theme = raw.get("primary_theme", local["primary_theme"])
    if theme not in THEMES:
        theme = local["primary_theme"]

    secondary = normalize_ai_list(raw.get("secondary_themes"), THEMES, local["secondary_themes"])
    secondary = [item for item in secondary if item != theme][:2]

    sentiment = raw.get("sentiment", local["sentiment"])
    if sentiment not in SENTIMENT_LABELS:
        sentiment = local["sentiment"]

    return {
        **local,
        "primary_theme": theme,
        "secondary_themes": secondary,
        "theme_reason": sanitize_text(str(raw.get("theme_reason", local["theme_reason"]))) or local["theme_reason"],
        "sentiment": sentiment,
        "sentiment_reason": sanitize_text(str(raw.get("sentiment_reason", local["sentiment_reason"]))) or local["sentiment_reason"],
        "sensory_questions": normalize_question_block(raw.get("sensory_questions"), local["sensory_questions"]),
        "emotional_questions": normalize_question_block(raw.get("emotional_questions"), local["emotional_questions"]),
        "poem": sanitize_text(str(raw.get("poem", local["poem"]))) or local["poem"],
        "storytelling_prompt": sanitize_text(str(raw.get("storytelling_prompt", local["storytelling_prompt"]))) or local["storytelling_prompt"],
        "caregiver_notes": caregiver_notes,
    }


def analyze_with_gemini(api_key: str, memory_text: str, caregiver_notes: str) -> Dict[str, Any]:
    local = build_local_analysis(memory_text, caregiver_notes)
    client = get_gemini_client(api_key)
    if client is None or types is None:
        return local

    try:
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            contents=build_prompt(memory_text, caregiver_notes),
            config=types.GenerateContentConfig(
                temperature=0.35,
                response_mime_type="application/json",
            ),
        )
        raw = extract_json(response.text or "{}")
        return normalize_ai_response(raw, local, memory_text, caregiver_notes)
    except Exception:
        return local


def build_entry(memory_text: str, caregiver_notes: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": len(st.session_state.memory_journal) + 1,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "memory": memory_text,
        "caregiver_notes": caregiver_notes,
        "analysis": analysis,
    }


def add_entry(memory_text: str, caregiver_notes: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
    entry = build_entry(memory_text, caregiver_notes, analysis)
    st.session_state.memory_journal.append(entry)
    st.session_state.selected_entry_id = entry["id"]
    return entry


def get_selected_entry() -> Optional[Dict[str, Any]]:
    if not st.session_state.memory_journal:
        return None
    selected_id = st.session_state.get("selected_entry_id")
    if selected_id is None:
        return st.session_state.memory_journal[-1]
    for entry in st.session_state.memory_journal:
        if entry["id"] == selected_id:
            return entry
    return st.session_state.memory_journal[-1]


def select_sidebar_entry() -> None:
    journal = st.session_state.memory_journal
    st.sidebar.subheader("Memory Journal")
    st.sidebar.caption("Select an entry to load it into the main panel.")

    if not journal:
        st.sidebar.info("No memories logged yet.")
        return

    selected_id = st.sidebar.selectbox(
        "View previous entries",
        options=[entry["id"] for entry in journal],
        format_func=lambda entry_id: next(
            f"{item['timestamp']} · {item['analysis']['primary_theme']} · {item['analysis']['sentiment']}"
            for item in journal
            if item["id"] == entry_id
        ),
        index=len(journal) - 1,
    )
    st.session_state.selected_entry_id = selected_id

    st.sidebar.markdown("### Recent entries")
    for entry in reversed(journal[-5:]):
        st.sidebar.markdown(
            f"""
            <div class="entry-preview">
                <div><strong>{entry['analysis']['primary_theme']}</strong> · {entry['analysis']['sentiment']}</div>
                <div class="muted" style="font-size: 0.84rem;">{entry['timestamp']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if st.sidebar.button("Clear journal", use_container_width=True):
        st.session_state.memory_journal = []
        st.session_state.selected_entry_id = None
        st.rerun()


def compute_session_length_minutes() -> int:
    journal = st.session_state.memory_journal
    if not journal:
        return 0
    first = datetime.fromisoformat(journal[0]["timestamp"])
    delta = datetime.now() - first
    return max(0, int(delta.total_seconds() // 60))


def compute_dashboard_metrics() -> Dict[str, Any]:
    journal = st.session_state.memory_journal
    if not journal:
        return {
            "count": 0,
            "avg_richness": 0.0,
            "most_common_theme": "No memories yet",
            "session_length": 0,
        }

    themes = [entry["analysis"]["primary_theme"] for entry in journal]
    scores = [entry["analysis"]["richness_score"] for entry in journal]
    return {
        "count": len(journal),
        "avg_richness": mean(scores),
        "most_common_theme": Counter(themes).most_common(1)[0][0],
        "session_length": compute_session_length_minutes(),
    }


def render_badges(primary: str, secondary: Sequence[str]) -> None:
    items = [primary] + list(secondary)
    st.markdown("".join(f'<span class="badge">{item}</span>' for item in items), unsafe_allow_html=True)


def format_count_label(value: int) -> str:
    return str(value) if value else "0"


def render_dashboard() -> None:
    metrics = compute_dashboard_metrics()
    st.markdown('<div class="section-shell">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">Research Dashboard</div>', unsafe_allow_html=True)
    cols = st.columns(4)
    cols[0].metric("Total Memories Logged", format_count_label(metrics["count"]))
    cols[1].metric("Average Richness Score", f"{metrics['avg_richness']:.1f}" if metrics["count"] else "0.0")
    cols[2].metric("Most Common Theme", metrics["most_common_theme"])
    cols[3].metric("Session Length", f"{metrics['session_length']} min")
    st.markdown('</div>', unsafe_allow_html=True)


def render_selected_entry(entry: Dict[str, Any]) -> None:
    analysis = entry["analysis"]

    st.markdown('<div class="section-shell">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">Selected Memory</div>', unsafe_allow_html=True)
    st.write(f"**Timestamp:** {entry['timestamp']}")
    render_badges(analysis["primary_theme"], analysis["secondary_themes"])
    st.write(entry["memory"])
    if entry["caregiver_notes"]:
        st.markdown("**Caregiver Notes**")
        st.markdown(f'<div class="note-box">{html.escape(entry["caregiver_notes"])} </div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    left, right = st.columns([1, 1])
    with left:
        with st.container(border=True):
            st.subheader("Memory Richness Analysis")
            st.metric("Memory Richness Score", f"{analysis['richness_score']}/10")
            st.write(analysis["theme_reason"])
            st.write(analysis["sentiment_reason"])
            breakdown = analysis["richness_breakdown"]
            breakdown_cols = st.columns(4)
            breakdown_cols[0].metric("Emotional", breakdown["emotional_references"])
            breakdown_cols[1].metric("Sensory", breakdown["sensory_references"])
            breakdown_cols[2].metric("People", breakdown["people_references"])
            breakdown_cols[3].metric("Place", breakdown["place_references"])
            st.metric("Cognitive Stimulation Index", f"{analysis['cognitive_stimulation_index']}/100")

    with right:
        with st.container(border=True):
            st.subheader("Sentiment Analysis")
            st.markdown(f"<span class='badge'>{analysis['sentiment']}</span>", unsafe_allow_html=True)

    with st.container(border=True):
        st.subheader("Creative Cognitive Stimulation Module")
        st.markdown("**Sensory Recall Questions**")
        for key in ["sounds", "smells", "sights", "objects"]:
            st.markdown(f"**{key.capitalize()}**")
            for question in analysis["sensory_questions"][key]:
                st.markdown(f"- {question}")

        st.markdown("**Emotional Reflection Questions**")
        for key in ["feelings", "relationships", "meaning"]:
            st.markdown(f"**{key.capitalize()}**")
            for question in analysis["emotional_questions"][key]:
                st.markdown(f"- {question}")

        st.markdown("**Short Poem**")
        st.write(analysis["poem"])
        st.markdown("**Storytelling Prompt**")
        st.write(analysis["storytelling_prompt"])


def render_visual_analytics() -> None:
    journal = st.session_state.memory_journal
    if not journal:
        return

    theme_counts = Counter(entry["analysis"]["primary_theme"] for entry in journal)
    sentiment_counts = Counter(entry["analysis"]["sentiment"] for entry in journal)
    richness_points = [
        {"timestamp": datetime.fromisoformat(entry["timestamp"]), "richness": entry["analysis"]["richness_score"]}
        for entry in journal
    ]

    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(
            x=list(theme_counts.keys()),
            y=list(theme_counts.values()),
            title="Theme Distribution",
        )
        fig.update_traces(marker=dict(color="#7da4ba"))
        fig.update_layout(template="plotly_white", height=360, margin=dict(l=10, r=10, t=50, b=10), coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.pie(
            names=list(sentiment_counts.keys()),
            values=list(sentiment_counts.values()),
            title="Sentiment Distribution",
            hole=0.45,
            color_discrete_sequence=["#7aa0b7", "#c5d5df", "#91b8a8", "#9fb1c3"],
        )
        fig.update_layout(template="plotly_white", height=360, margin=dict(l=10, r=10, t=50, b=10))
        st.plotly_chart(fig, use_container_width=True)

    fig = px.line(
        x=[item["timestamp"] for item in richness_points],
        y=[item["richness"] for item in richness_points],
        markers=True,
        title="Richness Over Time",
    )
    fig.update_traces(line=dict(color="#356b87", width=3), marker=dict(size=8))
    fig.update_layout(template="plotly_white", height=360, margin=dict(l=10, r=10, t=50, b=10))
    st.plotly_chart(fig, use_container_width=True)


def render_timeline() -> None:
    journal = st.session_state.memory_journal
    if not journal:
        return

    st.markdown('<div class="section-shell">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">Timeline View</div>', unsafe_allow_html=True)
    for entry in sorted(journal, key=lambda item: item["timestamp"]):
        analysis = entry["analysis"]
        with st.expander(f"{entry['timestamp']} · {analysis['primary_theme']} · {analysis['sentiment']} · {analysis['richness_score']}/10", expanded=False):
            st.write(entry["memory"])
            if entry["caregiver_notes"]:
                st.markdown("**Caregiver Notes**")
                st.write(entry["caregiver_notes"])
            st.markdown("**Cognitive Stimulation Index**")
            st.write(f"{analysis['cognitive_stimulation_index']}/100")
    st.markdown('</div>', unsafe_allow_html=True)


def export_journal_markdown() -> str:
    journal = sorted(st.session_state.memory_journal, key=lambda item: item["timestamp"])
    lines = ["# MemorySpark AI Export", f"Generated: {datetime.now().isoformat(timespec='seconds')}", ""]
    for entry in journal:
        analysis = entry["analysis"]
        lines.extend(
            [
                f"## {entry['timestamp']} - {analysis['primary_theme']}",
                f"- Sentiment: {analysis['sentiment']}",
                f"- Memory Richness Score: {analysis['richness_score']}/10", 
                f"- Cognitive Stimulation Index: {analysis['cognitive_stimulation_index']}/100", 
                f"- Emotional references: {analysis['richness_breakdown']['emotional_references']}",
                f"- Sensory references: {analysis['richness_breakdown']['sensory_references']}",
                f"- People references: {analysis['richness_breakdown']['people_references']}",
                f"- Place references: {analysis['richness_breakdown']['place_references']}",
                "",
                "### Memory",
                entry["memory"],
                "",
            ]
        )
        if entry["caregiver_notes"]:
            lines.extend(["### Caregiver Notes", entry["caregiver_notes"], ""])
        lines.extend(
            [
                "### Creative Cognitive Stimulation Module",
                "#### Sensory Recall Questions",
            ]
        )
        for section in ["sounds", "smells", "sights", "objects"]:
            lines.append(f"- {section.capitalize()}: " + " | ".join(analysis["sensory_questions"][section]))
        lines.append("#### Emotional Reflection Questions")
        for section in ["feelings", "relationships", "meaning"]:
            lines.append(f"- {section.capitalize()}: " + " | ".join(analysis["emotional_questions"][section]))
        lines.extend(
            [
                "#### Short Poem",
                analysis["poem"],
                "",
                "#### Storytelling Prompt",
                analysis["storytelling_prompt"],
                "",
                "---",
                "",
            ]
        )
    return "\n".join(lines)


def export_journal_text() -> str:
    journal = sorted(st.session_state.memory_journal, key=lambda item: item["timestamp"])
    lines = ["MemorySpark AI Export", f"Generated: {datetime.now().isoformat(timespec='seconds')}", ""]
    for entry in journal:
        analysis = entry["analysis"]
        lines.extend(
            [
                f"Timestamp: {entry['timestamp']}",
                f"Theme: {analysis['primary_theme']}",
                f"Sentiment: {analysis['sentiment']}",
                f"Memory Richness Score: {analysis['richness_score']}/10",
                f"Cognitive Stimulation Index: {analysis['cognitive_stimulation_index']}/100",
                "Memory:",
                entry["memory"],
                "",
            ]
        )
    return "\n".join(lines)


def render_export_feature() -> None:
    if not st.session_state.memory_journal:
        return

    st.markdown('<div class="section-shell">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">Export Feature</div>', unsafe_allow_html=True)
    export_format = st.radio("Choose export format", ["Markdown", "Text"], horizontal=True)
    if export_format == "Markdown":
        export_data = export_journal_markdown()
        file_name = f"memoryspark-ai-export-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
        mime = "text/markdown"
    else:
        export_data = export_journal_text()
        file_name = f"memoryspark-ai-export-{datetime.now().strftime('%Y%m%d-%H%M%S')}.txt"
        mime = "text/plain"

    st.download_button(
        "Download export",
        data=export_data,
        file_name=file_name,
        mime=mime,
        use_container_width=False,
    )
    st.caption("The exported content is formatted to be PDF-ready through markdown or plain text conversion.")
    st.markdown('</div>', unsafe_allow_html=True)


def render_intro() -> None:
    st.markdown(
        """
        <div class="section-shell">
            <h1 style="margin: 0 0 0.25rem 0; color: #183243;">MemorySpark AI</h1>
            <p class="muted" style="margin: 0; line-height: 1.55; max-width: 85ch;">
                A clinical, accessible reminiscence research prototype for dementia care settings. It helps users capture memories,
                attach caregiver notes, analyze themes and richness, and generate gentle cognitive stimulation prompts.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_input_form(api_key: str) -> Optional[Dict[str, Any]]:
    st.markdown('<div class="section-shell">', unsafe_allow_html=True)
    st.markdown('<div class="panel-title">Submit a Memory</div>', unsafe_allow_html=True)
    with st.form("memory_form", clear_on_submit=False):
        memory_text = st.text_area(
            "Memory entry",
            height=180,
            placeholder="Example: I remember the smell of my grandmother's kitchen, the rain on the window, and the way my sister laughed at the table.",
        )
        caregiver_notes = st.text_area(
            "Optional caregiver notes",
            height=110,
            placeholder="Add context, observations, or follow-up questions for later review.",
        )
        submitted = st.form_submit_button("Analyze memory", use_container_width=True)

    st.markdown('</div>', unsafe_allow_html=True)

    if not submitted:
        return None

    memory_text = sanitize_text(memory_text)
    caregiver_notes = sanitize_text(caregiver_notes)
    if not memory_text:
        st.warning("Please enter a memory before analyzing.")
        return None

    with st.spinner("Analyzing memory..."):
        analysis = analyze_with_gemini(api_key, memory_text, caregiver_notes)

    entry = add_entry(memory_text, caregiver_notes, analysis)
    st.success("Memory saved to the journal.")
    return entry


def render_header_alerts(api_key: str) -> None:
    st.info("Gemini is configured securely through Streamlit secrets or environment variables. No API keys are hardcoded in the app.")


def main() -> None:
    configure_page()
    initialize_state()
    api_key = load_gemini_api_key()
    render_intro()
    select_sidebar_entry()
    render_header_alerts(api_key)

    new_entry = render_input_form(api_key)
    active_entry = new_entry or get_selected_entry()

    if st.session_state.memory_journal:
        render_dashboard()

    if active_entry:
        render_selected_entry(active_entry)
        render_visual_analytics()
        render_timeline()
        render_export_feature()
    else:
        with st.container(border=True):
            st.subheader("How it works")
            st.write(
                "Submit a memory to generate theme detection, richness analysis, sentiment analysis, the Creative Cognitive Stimulation Module, a timeline view, and export-ready notes for later review."
            )


if __name__ == "__main__":
    main()