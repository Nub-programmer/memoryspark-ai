import json
import os
import re
from collections import Counter
from datetime import datetime
from statistics import mean
from typing import Any, Dict, List, Optional

import streamlit as st

try:
    from google import genai
    from google.genai import types
except Exception:  # pragma: no cover - dependency fallback during setup
    genai = None
    types = None


THEMES = [
    "Family",
    "Childhood",
    "Friendship",
    "Education",
    "Travel",
    "Celebration",
    "Career",
    "Other",
]

THEME_KEYWORDS = {
    "Family": ["mother", "father", "mom", "dad", "sister", "brother", "grandmother", "grandfather", "family", "home"],
    "Childhood": ["child", "children", "school", "play", "toy", "birthday", "young", "kid", "kidhood", "summer"],
    "Friendship": ["friend", "friends", "best friend", "classmate", "neighbor", "buddy", "companions", "together"],
    "Education": ["school", "teacher", "lesson", "classroom", "study", "college", "university", "exam", "graduation"],
    "Travel": ["trip", "travel", "journey", "train", "plane", "airport", "road", "vacation", "visit", "beach"],
    "Celebration": ["birthday", "wedding", "holiday", "party", "celebration", "anniversary", "festival", "ceremony"],
    "Career": ["job", "work", "office", "career", "boss", "team", "project", "promotion", "shift", "retirement"],
}

SENSORY_WORDS = {
    "sound": ["sound", "music", "voice", "voices", "laugh", "laughs", "noise", "bell", "radio", "song", "silence"],
    "smell": ["smell", "scent", "odor", "perfume", "baking", "coffee", "soap", "rain", "smoke", "fresh"],
    "sight": ["see", "saw", "look", "light", "color", "colors", "bright", "dark", "window", "picture", "garden", "street"],
    "object": ["chair", "table", "dress", "car", "book", "toy", "cup", "photo", "letter", "watch", "ring", "house"],
}

EMOTION_WORDS = [
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
]

LOCATION_WORDS = [
    "home",
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
]

LOCAL_STORY_SPARKS = {
    "Family": "In the quiet rhythm of familiar voices, the memory opens like a warm room.",
    "Childhood": "Before the day grew complicated, there was a small moment that still glows softly.",
    "Friendship": "Between shared laughter and ordinary time, something lasting was being built.",
    "Education": "In that classroom light, a lesson became more than words on a page.",
    "Travel": "Somewhere between departure and return, the world felt wider than before.",
    "Celebration": "Under the gentle noise of celebration, the moment carried itself like music.",
    "Career": "Amid the steady pace of work, one memory remained especially clear.",
    "Other": "In the edge of the ordinary, a memory waits with quiet detail.",
}


def initialize_state() -> None:
    if "memory_journal" not in st.session_state:
        st.session_state.memory_journal = []


def get_api_key() -> Optional[str]:
    try:
        if "GEMINI_API_KEY" in st.secrets:
            return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass

    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


@st.cache_resource(show_spinner=False)
def get_gemini_client() -> Optional[Any]:
    api_key = get_api_key()
    if not api_key or genai is None:
        return None
    return genai.Client(api_key=api_key)


def configure_page() -> None:
    st.set_page_config(
        page_title="MemorySpark AI",
        page_icon="MemorySpark AI",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """
        <style>
        :root {
            --bg: #f4f7fb;
            --panel: #ffffff;
            --panel-alt: #edf3f9;
            --text: #173042;
            --muted: #5d7285;
            --border: #d9e3ec;
            --accent: #2f6f95;
            --accent-soft: #e5f1f8;
        }

        .stApp {
            background: linear-gradient(180deg, #f7fafc 0%, #eef4f9 100%);
            color: var(--text);
        }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 2.5rem;
            max-width: 1180px;
        }

        .hero {
            background: linear-gradient(135deg, rgba(47,111,149,0.10), rgba(47,111,149,0.02));
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 1.5rem 1.6rem;
            margin-bottom: 1.25rem;
        }

        .hero h1 {
            margin: 0;
            color: var(--text);
            font-size: 2.1rem;
            line-height: 1.1;
        }

        .hero p {
            margin: 0.65rem 0 0;
            color: var(--muted);
            max-width: 70ch;
            line-height: 1.55;
        }

        .section-card {
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 1rem 1.1rem;
            box-shadow: 0 10px 24px rgba(23, 48, 66, 0.04);
            margin-bottom: 1rem;
        }

        .section-card h2, .section-card h3 {
            margin-top: 0;
        }

        .muted {
            color: var(--muted);
        }

        .badge {
            display: inline-block;
            padding: 0.35rem 0.65rem;
            margin: 0.2rem 0.35rem 0.2rem 0;
            border-radius: 999px;
            background: var(--accent-soft);
            color: var(--accent);
            font-weight: 600;
            font-size: 0.88rem;
        }

        .analysis-box {
            background: #fbfdff;
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 0.9rem 1rem;
        }

        .journal-item {
            border-left: 3px solid var(--accent);
            padding-left: 0.8rem;
            margin-bottom: 0.9rem;
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


def sanitize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def extract_json(text: str) -> Dict[str, Any]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start : end + 1]

    return json.loads(cleaned)


def build_prompt(memory_text: str) -> str:
    themes = ", ".join(THEMES)
    return f"""
You are supporting reminiscence therapy for dementia care, caregiver conversations, research notes, and cognitive stimulation.

Analyze the memory below and return only valid JSON with this schema:
{{
  "primary_theme": one of [{themes}],
  "secondary_themes": array of 0 to 2 theme strings from the same list,
  "theme_reason": short explanation,
  "richness_score": integer from 1 to 10,
  "richness_reason": short explanation tied to sensory details, emotional details, people references, and location references,
  "sensory_recall": {{
    "sounds": [2 to 3 questions],
    "smells": [2 to 3 questions],
    "sights": [2 to 3 questions],
    "objects": [2 to 3 questions]
  }},
  "emotional_reflection": {{
    "feelings": [2 to 3 questions],
    "relationships": [2 to 3 questions],
    "meaning": [2 to 3 questions]
  }},
  "storytelling_spark": short poetic sentence starter
}}

Rules:
- Keep questions gentle, concrete, and supportive.
- Make the storytelling spark brief and evocative.
- Do not mention that you are an AI.

Memory:
"""{memory_text}"""
"""


def local_theme(memory_text: str) -> str:
    lowered = memory_text.lower()
    best_theme = "Other"
    best_count = 0
    for theme, keywords in THEME_KEYWORDS.items():
        count = sum(lowered.count(keyword) for keyword in keywords)
        if count > best_count:
            best_theme = theme
            best_count = count
    return best_theme


def local_richness_score(memory_text: str) -> int:
    lowered = memory_text.lower()
    tokens = re.findall(r"[a-zA-Z']+", lowered)
    sensory_hits = sum(
        sum(1 for token in tokens if token == keyword)
        for keywords in SENSORY_WORDS.values()
        for keyword in keywords
    )
    emotion_hits = sum(1 for word in EMOTION_WORDS if word in lowered)
    location_hits = sum(1 for word in LOCATION_WORDS if word in lowered)
    people_hits = sum(1 for word in ["mother", "father", "friend", "sister", "brother", "grandmother", "grandfather", "teacher", "coworker", "partner"] if word in lowered)

    score = 1
    score += min(3, sensory_hits)
    score += min(2, emotion_hits)
    score += min(2, people_hits)
    score += min(2, location_hits)
    score += min(2, len(tokens) // 40)
    return max(1, min(10, score))


def local_questions(theme: str, memory_text: str) -> Dict[str, Dict[str, List[str]]]:
    theme_hint = theme.lower()
    sensory = {
        "sounds": [
            f"What sounds stand out most in this {theme_hint} memory?",
            "Were there voices, music, or background noises that shaped the moment?",
            "Did silence or a specific sound make the memory feel stronger?",
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
    emotions = {
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
    return {"sensory_recall": sensory, "emotional_reflection": emotions}


def local_story_spark(theme: str, memory_text: str) -> str:
    starter = LOCAL_STORY_SPARKS.get(theme, LOCAL_STORY_SPARKS["Other"])
    preview_words = sanitize_text(memory_text).split()
    if preview_words:
        preview = " ".join(preview_words[:10])
        return f"{starter} {preview.lower().rstrip('.')}..."
    return starter


def build_local_analysis(memory_text: str) -> Dict[str, Any]:
    primary_theme = local_theme(memory_text)
    richness_score = local_richness_score(memory_text)
    questions = local_questions(primary_theme, memory_text)
    return {
        "primary_theme": primary_theme,
        "secondary_themes": [],
        "theme_reason": f"The text contains cues linked to {primary_theme.lower()}.",
        "richness_score": richness_score,
        "richness_reason": "This is a heuristic fallback based on the presence of sensory, emotional, people, and location details.",
        "sensory_recall": questions["sensory_recall"],
        "emotional_reflection": questions["emotional_reflection"],
        "storytelling_spark": local_story_spark(primary_theme, memory_text),
    }


def normalize_analysis(raw: Dict[str, Any], memory_text: str) -> Dict[str, Any]:
    theme = raw.get("primary_theme") or raw.get("theme") or local_theme(memory_text)
    if theme not in THEMES:
        theme = "Other"

    secondary = raw.get("secondary_themes") or raw.get("secondary_theme") or []
    if isinstance(secondary, str):
        secondary = [secondary]
    secondary = [item for item in secondary if item in THEMES and item != theme][:2]

    sensory = raw.get("sensory_recall") or raw.get("sensory_questions") or {}
    emotional = raw.get("emotional_reflection") or raw.get("emotional_questions") or {}

    def coerce_questions(section: Any, category: str) -> List[str]:
        value = section.get(category, []) if isinstance(section, dict) else []
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, list):
            value = []
        cleaned = [sanitize_text(str(item)) for item in value if sanitize_text(str(item))]
        return cleaned[:3]

    richness = raw.get("richness_score", local_richness_score(memory_text))
    try:
        richness = int(richness)
    except Exception:
        richness = local_richness_score(memory_text)
    richness = max(1, min(10, richness))

    storytelling_spark = sanitize_text(str(raw.get("storytelling_spark", "")))
    if not storytelling_spark:
        storytelling_spark = local_story_spark(theme, memory_text)

    return {
        "primary_theme": theme,
        "secondary_themes": secondary,
        "theme_reason": sanitize_text(str(raw.get("theme_reason", ""))) or f"The memory aligns most closely with {theme.lower()}.",
        "richness_score": richness,
        "richness_reason": sanitize_text(str(raw.get("richness_reason", ""))) or "The score reflects the level of sensory, emotional, people, and location detail.",
        "sensory_recall": {
            "sounds": coerce_questions(sensory, "sounds") or local_questions(theme, memory_text)["sensory_recall"]["sounds"],
            "smells": coerce_questions(sensory, "smells") or local_questions(theme, memory_text)["sensory_recall"]["smells"],
            "sights": coerce_questions(sensory, "sights") or local_questions(theme, memory_text)["sensory_recall"]["sights"],
            "objects": coerce_questions(sensory, "objects") or local_questions(theme, memory_text)["sensory_recall"]["objects"],
        },
        "emotional_reflection": {
            "feelings": coerce_questions(emotional, "feelings") or local_questions(theme, memory_text)["emotional_reflection"]["feelings"],
            "relationships": coerce_questions(emotional, "relationships") or local_questions(theme, memory_text)["emotional_reflection"]["relationships"],
            "meaning": coerce_questions(emotional, "meaning") or local_questions(theme, memory_text)["emotional_reflection"]["meaning"],
        },
        "storytelling_spark": storytelling_spark,
    }


def analyze_with_gemini(memory_text: str) -> Dict[str, Any]:
    client = get_gemini_client()
    if client is None or types is None:
        return build_local_analysis(memory_text)

    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    prompt = build_prompt(memory_text)

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.35,
                response_mime_type="application/json",
            ),
        )
        raw = extract_json(response.text or "{}")
        return normalize_analysis(raw, memory_text)
    except Exception:
        return build_local_analysis(memory_text)


def add_memory_to_journal(memory_text: str, analysis: Dict[str, Any]) -> None:
    st.session_state.memory_journal.append(
        {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "memory": memory_text,
            "analysis": analysis,
        }
    )


def compute_statistics() -> Dict[str, Any]:
    journal = st.session_state.memory_journal
    if not journal:
        return {"count": 0, "most_common_theme": "No memories yet", "avg_score": 0.0}

    themes = [entry["analysis"]["primary_theme"] for entry in journal]
    scores = [entry["analysis"]["richness_score"] for entry in journal]
    most_common_theme = Counter(themes).most_common(1)[0][0]
    return {
        "count": len(journal),
        "most_common_theme": most_common_theme,
        "avg_score": mean(scores),
    }


def render_sidebar() -> None:
    stats = compute_statistics()
    st.sidebar.title("Memory Journal")
    st.sidebar.caption("Session-based log for submitted memories.")
    st.sidebar.metric("Total memories logged", stats["count"])
    st.sidebar.metric("Most common theme", stats["most_common_theme"])
    st.sidebar.metric("Average richness score", f"{stats['avg_score']:.1f}" if stats["count"] else "0.0")

    st.sidebar.divider()
    st.sidebar.subheader("Care note")
    st.sidebar.write(
        "MemorySpark AI supports reflection and conversation. It is not a diagnostic tool and should not replace clinical judgment."
    )

    if st.session_state.memory_journal:
        st.sidebar.subheader("Recent entries")
        for entry in reversed(st.session_state.memory_journal[-5:]):
            theme = entry["analysis"]["primary_theme"]
            timestamp = entry["timestamp"]
            preview = sanitize_text(entry["memory"])
            if len(preview) > 90:
                preview = preview[:87] + "..."
            st.sidebar.markdown(
                f"""
                <div class="journal-item">
                    <div><strong>{theme}</strong></div>
                    <div class="muted" style="font-size: 0.85rem;">{timestamp}</div>
                    <div style="font-size: 0.92rem; margin-top: 0.2rem;">{preview}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    if st.sidebar.button("Clear journal", use_container_width=True):
        st.session_state.memory_journal = []
        st.rerun()


def render_theme_badges(primary: str, secondary: List[str]) -> None:
    badges = [primary] + secondary
    badge_markup = "".join(f'<span class="badge">{item}</span>' for item in badges)
    st.markdown(badge_markup, unsafe_allow_html=True)


def render_question_list(title: str, questions: List[str]) -> None:
    st.markdown(f"#### {title}")
    for item in questions:
        st.markdown(f"- {item}")


def render_analysis(memory_text: str, analysis: Dict[str, Any]) -> None:
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("Memory Theme Analysis")
    render_theme_badges(analysis["primary_theme"], analysis["secondary_themes"])
    st.write(analysis["theme_reason"])
    st.markdown('</div>', unsafe_allow_html=True)

    cols = st.columns([1, 2])
    with cols[0]:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("Memory Richness Score")
        st.metric("Score", analysis["richness_score"], help="1 = sparse memory detail, 10 = highly vivid memory detail")
        st.progress(analysis["richness_score"] / 10)
        st.write(analysis["richness_reason"])
        st.markdown('</div>', unsafe_allow_html=True)

    with cols[1]:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("Storytelling Spark")
        st.write(analysis["storytelling_spark"])
        st.markdown('</div>', unsafe_allow_html=True)

    sensory = analysis["sensory_recall"]
    emotional = analysis["emotional_reflection"]

    left, right = st.columns(2)
    with left:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("Sensory Recall")
        render_question_list("Sounds", sensory["sounds"])
        render_question_list("Smells", sensory["smells"])
        render_question_list("Sights", sensory["sights"])
        render_question_list("Objects", sensory["objects"])
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("Emotional Reflection")
        render_question_list("Feelings", emotional["feelings"])
        render_question_list("Relationships", emotional["relationships"])
        render_question_list("Meaning", emotional["meaning"])
        st.markdown('</div>', unsafe_allow_html=True)

    with st.expander("View structured analysis", expanded=False):
        st.json(analysis)
        st.caption(f"Original memory: {memory_text}")


def render_intro() -> None:
    st.markdown(
        """
        <div class="hero">
            <h1>MemorySpark AI</h1>
            <p>
                A clinical, accessible reminiscence assistant that helps users reflect on a memory,
                identify its theme, explore sensory detail, and generate gentle follow-up prompts.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="section-card">
            <strong>Suggested input:</strong>
            <span class="muted">A family dinner, a school day, a favorite trip, a work milestone, or any small moment you want to revisit.</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    configure_page()
    initialize_state()
    render_sidebar()
    render_intro()

    api_key = get_api_key()
    if not api_key:
        st.info("No Gemini API key detected. The app will use a local fallback analyzer until a key is provided.")

    with st.form("memory_form", clear_on_submit=False):
        memory_text = st.text_area(
            "Enter a memory",
            height=180,
            placeholder="Example: I remember the smell of my grandmother's kitchen and the sound of rain on the window during Sunday lunches.",
        )
        submitted = st.form_submit_button("Analyze memory", use_container_width=True)

    if submitted:
        sanitized = sanitize_text(memory_text)
        if not sanitized:
            st.warning("Please enter a memory before analyzing.")
        else:
            with st.spinner("Analyzing memory..."):
                analysis = analyze_with_gemini(sanitized)
            add_memory_to_journal(sanitized, analysis)
            st.success("Memory analyzed and saved to the journal.")
            render_analysis(sanitized, analysis)

    if not st.session_state.memory_journal:
        st.markdown(
            """
            <div class="section-card">
                <h3 style="margin-top: 0;">How the app works</h3>
                <p class="muted">
                    Submit a memory once to generate the theme analysis, richness score, sensory recall prompts,
                    emotional reflection questions, and a storytelling starter. Every submitted memory remains in the
                    session journal until you clear it.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("Memory Journal Review")
        for entry in reversed(st.session_state.memory_journal):
            theme = entry["analysis"]["primary_theme"]
            score = entry["analysis"]["richness_score"]
            timestamp = entry["timestamp"]
            memory = entry["memory"]
            preview = memory if len(memory) <= 160 else memory[:157] + "..."
            st.markdown(
                f"""
                <div class="journal-item">
                    <div><strong>{timestamp}</strong> · {theme} · Richness {score}/10</div>
                    <div style="margin-top: 0.25rem;">{preview}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()