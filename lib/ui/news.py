"""
News Feed
Displays general market news and financial news filtered by portfolio holdings, all with AI summaries
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

# ---------- Helpers ----------
def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()

def ensure_period(s: str) -> str:
    s = s.strip()
    return s if s.endswith((".", "!", "?")) else (s + "." if s else s)

# ---------- Fetch functions ----------
@st.cache_data(ttl=86400)
def fetch_yahoo_rss(limit: int = 5):
    """Fetch Yahoo Finance RSS headlines."""
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
def fetch_newsdata(query: str, limit: int = 5):
    """Fetch news from NewsData.io."""
    try:
        url = f"https://newsdata.io/api/1/news?apikey={NEWSDATA_API_KEY}&q={query}&language=en&category=business"
        res = requests.get(url, timeout=10)
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
    except Exception as e:
        print("NewsData error:", e)
        return []

@st.cache_data(ttl=3600)
def fetch_gnews(query: str, limit: int = 4):
    """Backup fetch from GNews."""
    try:
        q = re.sub(r"[^a-zA-Z0-9\s]", " ", query)
        q = re.sub(r"\s+", " ", q).strip()
        url = f"https://gnews.io/api/v4/search?q={q}&lang=en&max={limit}&apikey={GNEWS_API_KEY}"
        res = requests.get(url, timeout=10)
        data = res.json()
        if "articles" not in data:
            return []
        arts = data["articles"][:limit]
        return [{
            "title": a.get("title"),
            "url": a.get("url"),
            "source": {"name": a.get("source", {}).get("name", "GNews")},
            "publishedAt": a.get("publishedAt"),
            "description": strip_html(a.get("description", "")),
        } for a in arts]
    except Exception as e:
        print("GNews error:", e)
        return []

@st.cache_data(ttl=1800)
def get_portfolio_stocks():
    """Fetch tickers from Supabase and map to readable names."""
    try:
        res = supabase_analyst.table("analyst_stock_watchlist").select("ticker").execute()
        if not res.data:
            return []
        companies = []
        for row in res.data:
            t = row["ticker"]
            try:
                info = yf.Ticker(t).info
                name = info.get("shortName") or info.get("longName") or t
            except Exception:
                name = t
            companies.append({"ticker": t, "name": name})
        return companies
    except Exception as e:
        st.error(f"Error fetching portfolio stocks: {e}")
        return []

def fetch_yf_company(ticker: str, limit: int = 3):
    """Fallback: Yahoo Finance company news via yfinance."""
    try:
        t = yf.Ticker(ticker)
        news = (t.news or [])[:limit]
        out = []
        for n in news:
            ts = n.get("providerPublishTime")
            published = datetime.utcfromtimestamp(ts).strftime("%Y-%m-%dT%H:%M:%SZ") if ts else None
            out.append({
                "title": n.get("title"),
                "url": n.get("link"),
                "source": {"name": "Yahoo Finance"},
                "publishedAt": published,
                "description": n.get("summary", "") or "",
            })
        return out
    except Exception:
        return []

# ---------- Gemini Summarization ----------
def summarize_article_gemini(title: str, description: str) -> str:
    """Smart Gemini summarizer that avoids title repetition and infers context when text is missing."""
    clean_title = strip_html(title or "")
    clean_desc = strip_html(description or "")

    # If description empty or almost same as title → context inference mode
    title_only = (
        not clean_desc
        or clean_desc.lower().strip() in clean_title.lower()
        or len(clean_desc.split()) < 5
    )

    model = genai.GenerativeModel("gemini-1.5-flash")

    try:
        if title_only:
            # --- Context inference mode ---
            response = model.generate_content(
                [
                    "You are a financial journalist.",
                    (
                        "Given only a headline, infer the most plausible financial or economic context in one full sentence. "
                        "Focus on what the headline likely means for investors, markets, or companies. "
                        "Do not repeat or rephrase the title; instead, explain its implication. "
                        "Be factual, neutral, and concise."
                    ),
                    f"Headline: {clean_title}"
                ],
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=100,
                ),
            )
        else:
            # --- Normal summarization mode ---
            response = model.generate_content(
                [
                    "You are a financial analyst summarizing market and company news.",
                    (
                        "Write 1–2 full sentences summarizing the main takeaway. "
                        "If it's about earnings, say whether results beat expectations. "
                        "If it's about M&A, highlight buyer, seller, and rationale. "
                        "Avoid repeating the title. End with a complete sentence."
                    ),
                    f"Title: {clean_title}\n\nContent: {clean_desc}"
                ],
                generation_config=genai.types.GenerationConfig(
                    temperature=0.4,
                    max_output_tokens=160,
                ),
            )

        summary = (response.text or "").strip()
        # Ensure it ends neatly
        if not summary.endswith((".", "!", "?")):
            summary += "."
        return summary

    except Exception as e:
        print("Gemini summary failed:", e)
        # Minimal fallback: short snippet from description or title
        snippet = clean_desc or clean_title
        words = snippet.split()
        snippet = " ".join(words[:25]) + ("..." if len(words) > 25 else "")
        return ensure_period(snippet)

def deduplicate_articles(articles):
    """Remove duplicate or nearly identical titles."""
    seen = []
    unique = []
    for art in articles:
        title = (art.get("title") or "").lower().strip()
        title = re.sub(r"[^a-z0-9\s]", "", title)
        if not title:
            continue

        # Check for near-duplicates (90% similarity)
        if any(SequenceMatcher(None, title, s).ratio() > 0.9 for s in seen):
            continue

        seen.append(title)
        unique.append(art)
    return unique

# ---------- Main UI ----------
def render_news_section():
    st.subheader("News Feed")
    st.markdown("Stay updated with the latest market and investment insights.")

    tab_general, tab_portfolio = st.tabs(["🌍 General Market", "💼 Portfolio"])

    # ----- GENERAL MARKET -----
    with tab_general:
        with st.spinner("Fetching latest market headlines..."):
            # Priority: GNews → NewsData → Yahoo
            gnews_articles = fetch_gnews("stock market OR economy OR investing", limit=7)
            newsdata_articles = fetch_newsdata("stock market OR economy OR investing", limit=7)
            yahoo_articles = fetch_yahoo_rss(limit=7)

            # Combine by priority
            articles = gnews_articles or newsdata_articles or yahoo_articles
            articles = deduplicate_articles(articles[:5])


        if not articles:
            st.info("No recent market news found.")
        else:
            for a in articles:
                title = a.get("title") or "No title"
                url = a.get("url") or "#"
                source = a.get("source", {}).get("name", "Unknown Source")

                # Date formatting
                raw_date = a.get("publishedAt")
                published = None
                if raw_date:
                    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S", "%a, %d %b %Y %H:%M:%S %Z"):
                        try:
                            published = datetime.strptime(raw_date[:19], fmt)
                            break
                        except Exception:
                            continue
                published_str = published.strftime("%b %d, %Y") if published else "Unknown date"

                desc = a.get("description", "")
                summary = summarize_article_gemini(title, desc)

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

        with st.spinner("Fetching portfolio headlines..."):
            articles = []

            if selected == "Most important headlines":
                for s in stocks[:5]:
                    news = (
                        fetch_gnews(s["name"], limit=2)
                        or fetch_newsdata(s["name"], limit=2)
                        or fetch_yf_company(s["ticker"], limit=2)
                    )
                    for n in news:
                        n["company"] = s["name"]
                        articles.append(n)
                    if len(articles) >= 5:
                        break
                    time.sleep(0.5)
            else:
                articles = (
                    fetch_gnews(selected, limit=3)
                    or fetch_newsdata(selected, limit=3)
                    or fetch_yf_company(next(s["ticker"] for s in stocks if s["name"] == selected), limit=3)
                )
                for a in articles:
                    a["company"] = selected

            articles = deduplicate_articles(articles)

        if not articles:
            st.info("No recent news found for this selection.")
            return

        for a in articles:
            title = a.get("title") or "No title"
            url = a.get("url") or "#"
            source = a.get("source", {}).get("name", "Unknown Source")

            raw_date = a.get("publishedAt")
            published = None
            if raw_date:
                for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S", "%a, %d %b %Y %H:%M:%S %Z"):
                    try:
                        published = datetime.strptime(raw_date[:19], fmt)
                        break
                    except Exception:
                        continue
            published_str = published.strftime("%b %d, %Y") if published else "Unknown date"

            desc = a.get("description", "")
            summary = summarize_article_gemini(title, desc)
            tag = f" ({a.get('company')})" if a.get("company") else ""

            with st.container():
                st.markdown(f"#### [{title}]({url}){tag}")
                st.caption(f"🕓 {published_str} | 🏢 {source}")
                if summary:
                    st.markdown(f"<div style='color:gray;font-style:italic;'>{summary}</div>", unsafe_allow_html=True)
                st.markdown("---")

    st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
