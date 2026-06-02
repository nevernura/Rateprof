# Visible Dataset Creation Pipeline

A Streamlit demo that walks an audience through turning **raw, messy HTML**
into a **clean, AI-enriched dataset** in three visible stages:

1. **Raw Harvest** — pick a department (Computer Science, Chemistry, Mathematics),
   watch a live progress bar fetch multiple review pages, and inspect a snippet
   of the raw HTML coming back.
2. **Parsing & Structuring** — extract `Review_ID`, `Timestamp`, `Course_Code`,
   and `Raw_Review_Text` from each page and render the resulting relational
   table with `st.dataframe`. Toggle **"Show Dataset Schema"** in the sidebar
   to reveal dtypes and example values.
3. **AI Feature Enrichment** — append derived columns (`Review_Length`,
   `Sentiment_Score`, `Sentiment_Label`) live, then download the final CSV.

The demo runs **fully offline** against bundled HTML fixtures in `fixtures/` —
no network, no rate limits, no flakiness during a live presentation.

## Setup

```bash
cd prof_pipeline
python -m venv .venv && source .venv/bin/activate   # optional
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Then open the URL Streamlit prints (usually http://localhost:8501).

## Files

```
prof_pipeline/
├── streamlit_app.py      # the 3-step Streamlit UI
├── requirements.txt
├── README.md
└── fixtures/             # offline "scraped" HTML pages
    ├── cs_page_1.html ... cs_page_3.html
    ├── chem_page_1.html ... chem_page_2.html
    └── math_page_1.html ... math_page_2.html
```

## Talking points for the demo

- **Step 1 sells the mess:** show the raw HTML text area — nav bars, ad slots,
  weird whitespace, inconsistent course codes (`cs-101`, `CS 201`, `Cs 220`).
- **Step 2 sells structure:** the same chaos becomes a tidy 5-column table.
  Course codes are normalized (`cs-101 → CS101`), dates parsed to `datetime64`.
  Flip the **Show Dataset Schema** toggle to make dtypes explicit.
- **Step 3 sells derivation:** the dataset *grows* on screen as sentiment and
  length columns appear. End with the CSV download — "this dataset did not
  exist 30 seconds ago."

## Swapping in real scraping later

`harvest_pages()` in `streamlit_app.py` is the single seam to replace. Return
`[(page_name, raw_html), ...]` from `requests.get()` instead of reading
fixtures and the rest of the pipeline works unchanged.
