"""
Visible Dataset Creation Pipeline
---------------------------------
A Streamlit app that walks the audience through three stages:
  1. Raw Harvest         - fetch messy HTML for a department/subject
  2. Parsing & Structuring - turn HTML into a clean relational DataFrame
  3. AI Feature Enrichment - derive new columns (sentiment, length)

Run:
    pip install -r requirements.txt
    streamlit run streamlit_app.py
"""

from __future__ import annotations

import hashlib
import re
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
from bs4 import BeautifulSoup

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# ---------------------------------------------------------------------------
# Page config & sidebar
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Visible Dataset Creation Pipeline",
    page_icon="🧪",
    layout="wide",
)

st.title("🧪 Visible Dataset Creation Pipeline")
st.caption(
    "Watch raw web text evolve into a clean, AI-enriched dataset — live, "
    "step by step."
)

with st.sidebar:
    st.header("Controls")
    show_schema = st.toggle("Show Dataset Schema", value=False)
    fetch_delay = st.slider(
        "Simulated fetch delay (sec/page)", 0.0, 1.0, 0.3, 0.1,
        help="Slows down the harvest so the progress bar is visible during demos.",
    )
    st.divider()
    st.markdown(
        "**Pipeline stages**\n"
        "1. Raw Harvest\n"
        "2. Parsing & Structuring\n"
        "3. AI Feature Enrichment"
    )

# ---------------------------------------------------------------------------
# Fixture loading (offline "scrape")
# ---------------------------------------------------------------------------
DEPARTMENT_FIXTURES = {
    "Computer Science": [
        "cs_page_1.html", "cs_page_2.html", "cs_page_3.html",
    ],
    "Chemistry": [
        "chem_page_1.html", "chem_page_2.html",
    ],
    "Mathematics": [
        "math_page_1.html", "math_page_2.html",
    ],
}


def list_departments() -> list[str]:
    return list(DEPARTMENT_FIXTURES.keys())


def harvest_pages(department: str, delay: float, progress_cb) -> list[tuple[str, str]]:
    """Return [(filename, raw_html), ...] simulating a live multi-page scrape."""
    files = DEPARTMENT_FIXTURES.get(department, [])
    out: list[tuple[str, str]] = []
    for i, fname in enumerate(files, start=1):
        path = FIXTURES_DIR / fname
        html = path.read_text(encoding="utf-8") if path.exists() else ""
        time.sleep(delay)
        progress_cb(i / len(files), f"Fetched {fname} ({len(html):,} bytes)")
        out.append((fname, html))
    return out


# ---------------------------------------------------------------------------
# Step 1 — Raw Harvest
# ---------------------------------------------------------------------------
st.header("1️⃣  Raw Harvest")
st.write(
    "Enter a **department or subject** below. The app will fetch multiple review "
    "pages and show you the raw, unstructured HTML coming back from the wild."
)

col_a, col_b = st.columns([3, 1])
with col_a:
    department = st.selectbox(
        "Department / subject keyword",
        options=list_departments(),
        index=0,
    )
with col_b:
    st.write("")  # vertical spacer
    st.write("")
    run_harvest = st.button("🌾 Run Harvest", type="primary", use_container_width=True)

if run_harvest or "harvested" in st.session_state:
    if run_harvest:
        progress = st.progress(0.0, text="Starting harvest…")
        status = st.empty()

        def _cb(p: float, msg: str):
            progress.progress(p, text=msg)
            status.write(f"• {msg}")

        pages = harvest_pages(department, fetch_delay, _cb)
        progress.progress(1.0, text="Harvest complete.")
        st.session_state["harvested"] = pages
        st.session_state["harvested_dept"] = department

    pages = st.session_state["harvested"]
    st.success(
        f"Harvested **{len(pages)} pages** for "
        f"**{st.session_state['harvested_dept']}** — "
        f"{sum(len(h) for _, h in pages):,} total bytes of raw HTML."
    )

    preview_idx = st.selectbox(
        "Inspect raw HTML for page:",
        options=list(range(len(pages))),
        format_func=lambda i: pages[i][0],
    )
    st.text_area(
        "Raw HTML/Text Ingested (first 500 chars)",
        value=pages[preview_idx][1][:500],
        height=180,
    )

# ---------------------------------------------------------------------------
# Step 2 — Parsing & Structuring
# ---------------------------------------------------------------------------
st.header("2️⃣  Parsing & Structuring")
st.write(
    "Now we extract specific attributes from that messy text and build a "
    "**relational table** — the moment unstructured HTML becomes a dataset."
)


def parse_pages(pages: list[tuple[str, str]]) -> pd.DataFrame:
    """Parse fixture HTML into a structured DataFrame."""
    rows: list[dict] = []
    course_re = re.compile(r"[^A-Za-z0-9]")

    for fname, html in pages:
        soup = BeautifulSoup(html, "html.parser")
        for card in soup.select(".review"):
            raw_course = (card.select_one(".course") or {}).get_text(strip=True) \
                if card.select_one(".course") else ""
            raw_date = (card.select_one(".date") or {}).get_text(strip=True) \
                if card.select_one(".date") else ""
            raw_text = card.select_one(".body").get_text(" ", strip=True) \
                if card.select_one(".body") else ""

            # Course code: normalize to uppercase alphanumeric (cs-101 -> CS101)
            course_code = course_re.sub("", raw_course).upper()

            # Timestamp: parse a handful of formats, fall back to NaT
            ts = pd.to_datetime(raw_date, errors="coerce")

            # Stable Review_ID hashed from source + text
            rid = hashlib.sha1(
                f"{fname}|{course_code}|{raw_text}".encode()
            ).hexdigest()[:12]

            rows.append({
                "Review_ID": rid,
                "Timestamp": ts.date() if pd.notna(ts) else None,
                "Course_Code": course_code,
                "Raw_Review_Text": raw_text,
                "Source_Page": fname,
            })

    df = pd.DataFrame(rows)
    if not df.empty:
        df["Timestamp"] = pd.to_datetime(df["Timestamp"])
    return df


if "harvested" in st.session_state:
    if st.button("🧱 Parse & Structure", type="primary"):
        with st.spinner("Parsing HTML → DataFrame…"):
            df = parse_pages(st.session_state["harvested"])
            st.session_state["df"] = df

if "df" in st.session_state and not st.session_state["df"].empty:
    df = st.session_state["df"]
    st.success(f"Built a structured dataset with **{len(df)} rows** and **{df.shape[1]} columns**.")
    st.dataframe(df, use_container_width=True, height=320)

    if show_schema:
        with st.expander("📐 Dataset schema", expanded=True):
            schema = pd.DataFrame({
                "column": df.columns,
                "dtype": [str(t) for t in df.dtypes],
                "non_null": df.notna().sum().values,
                "example": [str(df[c].dropna().iloc[0]) if df[c].notna().any() else "—"
                            for c in df.columns],
            })
            st.dataframe(schema, use_container_width=True, hide_index=True)
else:
    st.info("Run the harvest above, then parse to see the structured DataFrame.")

# ---------------------------------------------------------------------------
# Step 3 — AI Feature Enrichment
# ---------------------------------------------------------------------------
st.header("3️⃣  AI Feature Enrichment")
st.write(
    "A dataset isn't just what you **collect** — it's also what you **derive**. "
    "We append new columns by analyzing each review."
)

POSITIVE = {
    "great", "excellent", "amazing", "love", "loved", "clear", "helpful",
    "fantastic", "best", "engaging", "fair", "kind", "patient", "good",
    "awesome", "brilliant", "enjoyed",
}
NEGATIVE = {
    "boring", "bad", "worst", "hate", "hated", "confusing", "rude",
    "unfair", "terrible", "awful", "hard", "difficult", "unclear",
    "disorganized", "harsh",
}


def sentiment_score(text: str) -> float:
    tokens = re.findall(r"[a-z']+", text.lower())
    if not tokens:
        return 0.0
    pos = sum(1 for t in tokens if t in POSITIVE)
    neg = sum(1 for t in tokens if t in NEGATIVE)
    return round((pos - neg) / max(len(tokens) ** 0.5, 1), 3)


def sentiment_label(score: float) -> str:
    if score > 0.15:
        return "positive"
    if score < -0.15:
        return "negative"
    return "neutral"


if "df" in st.session_state and not st.session_state["df"].empty:
    if st.button("🤖 Enrich with AI features", type="primary"):
        df = st.session_state["df"].copy()
        progress = st.progress(0.0, text="Scoring reviews…")
        scores, lengths, labels = [], [], []
        for i, txt in enumerate(df["Raw_Review_Text"].fillna("")):
            s = sentiment_score(txt)
            scores.append(s)
            labels.append(sentiment_label(s))
            lengths.append(len(txt))
            progress.progress((i + 1) / len(df), text=f"Scored {i+1}/{len(df)}")
            time.sleep(0.02)
        df["Review_Length"] = lengths
        df["Sentiment_Score"] = scores
        df["Sentiment_Label"] = labels
        st.session_state["df_enriched"] = df
        progress.progress(1.0, text="Enrichment complete.")

if "df_enriched" in st.session_state:
    df_e = st.session_state["df_enriched"]
    st.success(f"Added **3 derived columns** — dataset now has **{df_e.shape[1]} columns**.")
    st.dataframe(df_e, use_container_width=True, height=340)

    c1, c2, c3 = st.columns(3)
    c1.metric("Avg sentiment", f"{df_e['Sentiment_Score'].mean():+.3f}")
    c2.metric("Avg review length", f"{df_e['Review_Length'].mean():.0f} chars")
    c3.metric("% positive", f"{(df_e['Sentiment_Label'] == 'positive').mean()*100:.0f}%")

    with st.expander("📊 Sentiment distribution"):
        st.bar_chart(df_e["Sentiment_Label"].value_counts())

    st.download_button(
        "⬇️ Download dataset as CSV",
        data=df_e.to_csv(index=False).encode("utf-8"),
        file_name=f"{st.session_state.get('harvested_dept','dataset').lower().replace(' ','_')}_reviews.csv",
        mime="text/csv",
    )
else:
    st.info("Parse a dataset first, then enrich it here.")
