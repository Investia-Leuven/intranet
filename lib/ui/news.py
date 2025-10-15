"""
News Feed
Ultra-optimized version for Heroku.
Preloads caches, minimizes API latency, and displays financial/portfolio news with AI summaries.
"""

import os
import re
import time
import requests
import feedparser
import streamlit as st
import yfinance as yf
from datetime import datetime
from supabase import create_client
import google.generativeai as genai
from difflib import SequenceMatcher

# --- Load keys ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
NEWSDATA_API_KEY = os.getenv("NEWSDATA_API_KEY")
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY")
SUPABASE_ANALYST_URL = os.getenv("SUPABASE_ANALYST_URL")
SUPABASE_ANALYST_KEY = os.getenv("SUPABASE_ANALYST_KEY")

# --- Initialize clients ---
genai.configure(api_key=GEMINI_API_KEY)
supabase_analyst = create_client(SUPABASE_ANALYST_URL, SUPABASE_ANALYST_KEY)

# --- Static name mapping (instant lookup) ---
TICKER_NAME_MAP = {
    "AIR.PA": "Airbus",
    "ASML": "ASML",
    "BABA": "Alibaba Group",
    "DEME.BR": "Deme Group",
    "ENX.PA": "Euronext",
    "MC.PA": "LVMH",
    "MDLZ": "Mondelez",
    "NDA.DE": "Nordea Bank",
    "OR.PA": "L'Oréal",
    "PUB.PA": "Publicis Groupe",
    "SGBS.AS": "Société Générale",
}

# ---------- Helpers ----------
def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()

def ensure_period(s: str) -> str:
    s = s.strip()
    return s if s.endswith((".", "!", "?")) else (s + "." if s else s)

def deduplicate_articles(articles):
    """Remove duplicate or nearly identical titles."""
    seen, unique = [], []
    for art in articles:
        title = (art.get("title") or "").lower().strip()
        if not title:
            continue
        title = re.sub(r"[^a-z0-9\s]", "", title)
        if any(SequenceMatcher(None, title, s).ratio() > 0.9 for s in seen):
            continue
        seen.append(title)
        unique.append(art)
    return unique

# ---------- Fetch functions ----------
@st.cache_data(ttl=86400)
def fetch_yahoo_rss(limit=5):
    feed = feedparser.parse("https://finance.yahoo.com/news/rssindex")
    results = []
    for it in feed.entries[:limit]:
        try:
            dt = datetime(*it.published_parsed[:6]).strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            dt = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        results.append({
            "title": it.get("title", "No title"),
            "url": it.get("link", "#"),
            "source": {"name": "Yahoo Finance"},
            "publishedAt": dt,
            "description": strip_html(it.get("summary", "")),
        })
    return results

@st.cache_data(ttl=3600)
def fetch_newsdata(query, limit=3):
    try:
        url = f"https://newsdata.io/api/1/news?apikey={NEWSDATA_API_KEY}&q={query}&language=en&category=business"
        res = requests.get(url, timeout=8)
        data = res.json()
        if "results" not in data:
            return []
        arts = data["results"][:limit]
        return [{
            "title": a.get("title"),
            "url": a.get("link"),
            "source": {"name": a.get("source_id", "NewsData.io")},
            "publishedAt": a.get("pubDate"),
            "description": strip_html(a.get("description", "")),
        } for a in arts]
    except Exception:
        return []

@st.cache_data(ttl=3600)
def fetch_gnews(query, limit=3):
    try:
        q = re.sub(r"[^a-zA-Z0-9\s]", " ", query)
        q = re.sub(r"\s+", " ", q).strip()
        url = f"https://gnews.io/api/v4/search?q={q}&lang=en&max={limit}&apikey={GNEWS_API_KEY}"
        res = requests.get(url, timeout=8)
        data = res.json()
        if "articles" not in data:
            return []
        return [{
            "title": a.get("title"),
            "url": a.get("url"),
            "source": {"name": a.get("source", {}).get("name", "GNews")},
            "publishedAt": a.get("publishedAt"),
            "description": strip_html(a.get("description", "")),
        } for a in data["articles"][:limit]]
    except Exception:
        return []

@st.cache_data(ttl=1800)
def fetch_yf_company(ticker, limit=3):
    """Yahoo Finance company-specific news (fast)."""
    try:
        t = yf.Ticker(ticker)
        news = (t.news or [])[:limit]
        out = []
        for n in news:
            if not n.get("title"):
                continue
            ts = n.get("providerPublishTime")
            published = datetime.utcfromtimestamp(ts).strftime("%Y-%m-%dT%H:%M:%SZ") if ts else None
            out.append({
                "title": n["title"],
                "url": n["link"],
                "source": {"name": "Yahoo Finance"},
                "publishedAt": published,
                "description": n.get("summary", ""),
            })
        return out
    except Exception:
        return []

# ---------- Portfolio fetching ----------
@st.cache_data(ttl=600)
def get_portfolio_stocks():
    """
    Fetch tickers from Supabase and map to readable names.
    - Uses static map first
    - Falls back to yfinance, then regex cleanup
    - Filters out junk strings like ISINs or numbers
    """
    try:
        res = supabase_analyst.table("analyst_stock_watchlist").select("ticker").execute()
        if not res.data:
            return []

        companies = []
        for row in res.data:
            ticker = row["ticker"]

            # --- Static map first ---
            if ticker in TICKER_NAME_MAP:
                name = TICKER_NAME_MAP[ticker]
            else:
                # Try yfinance for metadata
                try:
                    t = yf.Ticker(ticker)
                    info = getattr(t, "info", {}) or {}
                    name = info.get("shortName") or info.get("longName")
                except Exception:
                    name = None

                # Clean or replace invalid names
                if not name or re.search(r"[0-9,]|OP|ISIN", str(name)):
                    clean = re.sub(r"\.[A-Z]+$", "", ticker)
                    name = (
                        "Biocartis" if "BCART" in clean.upper()
                        else clean.capitalize()
                    )

                # Remove suffixes and tidy
                name = re.sub(r"\b(S\.?A\.?|N\.?V\.?|SE|Inc\.?|Corp\.?|SCA|PLC|AG|Ltd\.?|LLC)\b", "", name, flags=re.IGNORECASE)
                name = re.sub(r"\s+", " ", name).strip()

                # Cache for reuse
                TICKER_NAME_MAP[ticker] = name

            companies.append({"ticker": ticker, "name": name})

        return sorted(companies, key=lambda x: x["name"].lower())

    except Exception as e:
        st.error(f"Error fetching portfolio stocks: {e}")
        return []

# ---------- Gemini Summarization ----------
@st.cache_data(ttl=86400)
def summarize_article_gemini(title, description):
    """Generate short AI summary using Gemini (skip empty/no-title)."""
    if not title or title.lower().startswith("no title"):
        return ""
    desc = strip_html(description or "")
    if not desc or len(desc.split()) < 5:
        return ""

    try:
        model = genai.GenerativeModel("models/gemini-2.5-flash")
        prompt = (
            "Summarize this financial news in one or two complete sentences. "
            "Be factual and concise. Avoid repeating the title.\n\n"
            f"Title: {title}\n\nContent: {desc}"
        )
        response = model.generate_content(prompt, request_options={"timeout": 8})
        text = (response.text or "").strip()
        if not text.endswith((".", "!", "?")):
            text += "."
        return text
    except Exception:
        return desc[:160] + "..."

# ---------- Warmup Cache ----------
@st.cache_data(ttl=86400)
def warmup_cache():
    """Preload key data and news to make first load faster."""
    try:
        _ = get_portfolio_stocks()
        _ = fetch_gnews("stock market OR economy", limit=3)
        _ = fetch_newsdata("stock market OR economy", limit=3)
        _ = fetch_yahoo_rss(limit=3)
        print("✅ Cache warmed successfully")
    except Exception as e:
        print("⚠️ Cache warmup failed:", e)

# Run warmup immediately when the module is imported
warmup_cache()

# ---------- Main UI ----------
def render_news_section():
    st.subheader("News Feed")
    st.markdown("Stay updated with the latest market and investment insights.")

    tab_general, tab_portfolio = st.tabs(["🌍 General Market", "💼 Portfolio"])

    # ----- GENERAL MARKET -----
    with tab_general:
        with st.spinner("Fetching latest market headlines..."):
            gnews_articles = fetch_gnews("stock market OR economy OR investing", limit=5)
            newsdata_articles = fetch_newsdata("stock market OR economy OR investing", limit=5)
            yahoo_articles = fetch_yahoo_rss(limit=5)
            articles = gnews_articles or newsdata_articles or yahoo_articles
            articles = deduplicate_articles(articles[:5])

        if not articles:
            st.info("No recent market news found.")
        else:
            for a in articles:
                title = a.get("title") or ""
                if not title or title.lower().startswith("no title"):
                    continue
                url = a.get("url", "#")
                source = a.get("source", {}).get("name", "Unknown")
                raw_date = a.get("publishedAt")
                try:
                    published = datetime.strptime(raw_date[:19], "%Y-%m-%dT%H:%M:%S")
                    published_str = published.strftime("%b %d, %Y")
                except Exception:
                    published_str = "Unknown date"
                summary = summarize_article_gemini(title, a.get("description", ""))
                with st.container():
                    st.markdown(f"#### [{title}]({url})")
                    st.caption(f"🕓 {published_str} | 🏢 {source}")
                    if summary:
                        st.markdown(f"<div style='color:gray;font-style:italic;'>{summary}</div>", unsafe_allow_html=True)
                    st.markdown("---")

    # ----- PORTFOLIO -----
    with tab_portfolio:
        with st.spinner("Loading portfolio..."):
            stocks = get_portfolio_stocks()
        if not stocks:
            st.warning("No portfolio data found in Supabase.")
            return

        options = ["Most important headlines"] + [s["name"] for s in stocks]
        selected = st.selectbox("Select company:", options, index=0)

        with st.spinner("Fetching company headlines..."):
            articles = []
            if selected == "Most important headlines":
                for s in stocks[:5]:
                    full_name = s["name"]
                    ticker = s["ticker"]
                    news = (
                        fetch_gnews(full_name, limit=2)
                        or fetch_newsdata(full_name, limit=2)
                        or fetch_yf_company(ticker, limit=2)
                    )
                    for n in news:
                        n["company"] = full_name
                        articles.append(n)
                    if len(articles) >= 5:
                        break
                    time.sleep(0.1)  # ultra-short delay between calls
            else:
                company = next(s for s in stocks if s["name"] == selected)
                articles = (
                    fetch_gnews(company["name"], limit=3)
                    or fetch_newsdata(company["name"], limit=3)
                    or fetch_yf_company(company["ticker"], limit=3)
                )
                for a in articles:
                    a["company"] = company["name"]

            articles = deduplicate_articles(articles)

        if not articles:
            st.info("No recent news found for this selection.")
            return

        for a in articles:
            title = a.get("title") or ""
            if not title or title.lower().startswith("no title"):
                continue
            url = a.get("url", "#")
            source = a.get("source", {}).get("name", "Unknown")
            raw_date = a.get("publishedAt")
            try:
                published = datetime.strptime(raw_date[:19], "%Y-%m-%dT%H:%M:%S")
                published_str = published.strftime("%b %d, %Y")
            except Exception:
                published_str = "Unknown date"
            summary = summarize_article_gemini(title, a.get("description", ""))
            tag = f" ({a.get('company')})" if a.get("company") else ""
            with st.container():
                st.markdown(f"#### [{title}]({url}){tag}")
                st.caption(f"🕓 {published_str} | 🏢 {source}")
                if summary:
                    st.markdown(f"<div style='color:gray;font-style:italic;'>{summary}</div>", unsafe_allow_html=True)
                st.markdown("---")

    st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")