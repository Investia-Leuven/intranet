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
from dotenv import load_dotenv

# --- Environment setup ---
load_dotenv()
os.environ["GRPC_VERBOSITY"] = "ERROR"
os.environ["GLOG_minloglevel"] = "3"
os.environ["GOOGLE_API_USE_V1_ENDPOINT"] = "1"

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

def is_valid_article(article: dict) -> bool:
    """Returns False if the article has no proper title or 'No title' placeholder."""
    title = (article.get("title") or "").strip()
    return bool(title and title.lower() != "no title")

# ---------- Fetch functions ----------
@st.cache_data(ttl=86400)
def fetch_yahoo_rss(limit: int = 5):
    feed = feedparser.parse("https://finance.yahoo.com/news/rssindex")
    results = []
    for it in feed.entries[:limit]:
        title = strip_html(it.get("title", ""))
        if not title or title.lower() == "no title":
            continue
        try:
            dt = datetime(*it.published_parsed[:6]).strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            dt = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        results.append({
            "title": title,
            "url": it.get("link", "#"),
            "source": {"name": "Yahoo Finance"},
            "publishedAt": dt,
            "description": strip_html(it.get("summary", "")),
        })
    return [a for a in results if is_valid_article(a)]

@st.cache_data(ttl=3600)
def fetch_newsdata(query: str, limit: int = 5):
    try:
        url = f"https://newsdata.io/api/1/news?apikey={NEWSDATA_API_KEY}&q={query}&language=en&category=business"
        res = requests.get(url, timeout=10)
        data = res.json()
        articles = data.get("results", [])[:limit]
        results = []
        for a in articles:
            title = strip_html(a.get("title", ""))
            if not title or title.lower() == "no title":
                continue
            results.append({
                "title": title,
                "url": a.get("link"),
                "source": {"name": a.get("source_id", "NewsData.io")},
                "publishedAt": a.get("pubDate"),
                "description": strip_html(a.get("description", "")),
            })
        return [a for a in results if is_valid_article(a)]
    except Exception as e:
        print("NewsData error:", e)
        return []

@st.cache_data(ttl=3600)
def fetch_gnews(query: str, limit: int = 4):
    try:
        q = re.sub(r"[^a-zA-Z0-9\s]", " ", query)
        q = re.sub(r"\s+", " ", q).strip()
        url = f"https://gnews.io/api/v4/search?q={q}&lang=en&max={limit}&apikey={GNEWS_API_KEY}"
        res = requests.get(url, timeout=10)
        data = res.json()
        if "articles" not in data:
            return []
        results = []
        for a in data["articles"][:limit]:
            title = strip_html(a.get("title", ""))
            if not title or title.lower() == "no title":
                continue
            results.append({
                "title": title,
                "url": a.get("url"),
                "source": {"name": a.get("source", {}).get("name", "GNews")},
                "publishedAt": a.get("publishedAt"),
                "description": strip_html(a.get("description", "")),
            })
        return [a for a in results if is_valid_article(a)]
    except Exception as e:
        print("GNews error:", e)
        return []

@st.cache_data(ttl=1800)
def get_portfolio_stocks():
    try:
        res = supabase_analyst.table("analyst_stock_watchlist").select("ticker").execute()
        if not res.data:
            return []
        companies = []
        for row in res.data:
            t = row["ticker"]
            try:
                info = yf.Ticker(t).info
                name = info.get("longName") or info.get("shortName") or t
            except Exception:
                name = t
            companies.append({"ticker": t, "name": name})
        return companies
    except Exception as e:
        st.error(f"Error fetching portfolio stocks: {e}")
        return []

def fetch_yf_company(ticker: str, limit: int = 3):
    try:
        t = yf.Ticker(ticker)
        news = (t.news or [])[:limit]
        results = []
        for n in news:
            title = strip_html(n.get("title", ""))
            if not title or title.lower() == "no title":
                continue
            ts = n.get("providerPublishTime")
            published = datetime.utcfromtimestamp(ts).strftime("%Y-%m-%dT%H:%M:%SZ") if ts else None
            results.append({
                "title": title,
                "url": n.get("link"),
                "source": {"name": "Yahoo Finance"},
                "publishedAt": published,
                "description": n.get("summary", "") or "",
            })
        return [a for a in results if is_valid_article(a)]
    except Exception:
        return []

# ---------- Gemini Summarization ----------
def summarize_article_gemini(title: str, description: str) -> str:
    if not title or title.lower() == "no title":
        return ""  # skip invalid ones

    clean_title = strip_html(title)
    clean_desc = strip_html(description)
    title_only = (
        not clean_desc
        or clean_desc.lower().strip() in clean_title.lower()
        or len(clean_desc.split()) < 5
    )
    try:
        model = genai.GenerativeModel("models/gemini-2.5-flash")
        if title_only:
            prompt = (
                "You are a financial journalist. "
                "Given only a headline, infer the most plausible financial or economic context in one full sentence. "
                "Do not repeat the title.\n\n"
                f"Headline: {clean_title}"
            )
        else:
            prompt = (
                "You are a financial analyst summarizing market and company news. "
                "Write one or two complete sentences summarizing the key insight, avoiding repetition.\n\n"
                f"Title: {clean_title}\n\nContent: {clean_desc}"
            )
        response = model.generate_content(prompt)
        text = (response.text or "").strip()
        return ensure_period(text)
    except Exception as e:
        print("Gemini summary failed:", e)
        return ""

# ---------- Deduplication ----------
def deduplicate_articles(articles):
    unique = []
    seen = []
    for art in articles:
        title = (art.get("title") or "").strip().lower()
        title = re.sub(r"[^a-z0-9\s]", "", title)
        if not title or title == "no title":
            continue
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
            gnews_articles = fetch_gnews("stock market OR economy OR investing", limit=7)
            newsdata_articles = fetch_newsdata("stock market OR economy OR investing", limit=7)
            yahoo_articles = fetch_yahoo_rss(limit=7)
            articles = gnews_articles or newsdata_articles or yahoo_articles
            articles = [a for a in deduplicate_articles(articles[:5]) if is_valid_article(a)]

        if not articles:
            st.info("No recent market news found.")
        else:
            for a in articles:
                if not is_valid_article(a):
                    continue
                title = a["title"]
                url = a.get("url") or "#"
                source = a.get("source", {}).get("name", "Unknown Source")
                published_str = "Unknown date"
                if a.get("publishedAt"):
                    try:
                        published = datetime.fromisoformat(a["publishedAt"].replace("Z", "+00:00"))
                        published_str = published.strftime("%b %d, %Y")
                    except Exception:
                        pass
                summary = summarize_article_gemini(title, a.get("description", ""))

                with st.container():
                    st.markdown(f"#### [{title}]({url})")
                    st.caption(f"🕓 {published_str} | 🏢 {source}")
                    if summary:
                        st.markdown(
                            f"<div style='color:gray;font-style:italic;'>{summary}</div>",
                            unsafe_allow_html=True,
                        )
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
            if selected == "Most important headlines":
                all_articles = []
                for s in stocks:
                    news = (
                        fetch_gnews(s["name"], limit=1)
                        or fetch_newsdata(s["name"], limit=1)
                        or fetch_yf_company(s["ticker"], limit=1)
                    )
                    all_articles.extend([n for n in news if is_valid_article(n)])
                    if len(all_articles) >= 5:
                        break
                    time.sleep(0.3)
                articles = deduplicate_articles(all_articles)
            else:
                articles = (
                    fetch_gnews(selected, limit=3)
                    or fetch_newsdata(selected, limit=3)
                    or fetch_yf_company(next(s["ticker"] for s in stocks if s["name"] == selected), limit=3)
                )
                articles = [a for a in articles if is_valid_article(a)]
                for a in articles:
                    a["company"] = selected

        if not articles:
            st.info("No recent news found for this selection.")
            return

        for a in articles:
            if not is_valid_article(a):
                continue
            title = a["title"]
            url = a.get("url") or "#"
            source = a.get("source", {}).get("name", "Unknown Source")
            published_str = "Unknown date"
            if a.get("publishedAt"):
                try:
                    published = datetime.fromisoformat(a["publishedAt"].replace("Z", "+00:00"))
                    published_str = published.strftime("%b %d, %Y")
                except Exception:
                    pass
            summary = summarize_article_gemini(title, a.get("description", ""))
            tag = f" ({a.get('company')})" if a.get("company") else ""

            with st.container():
                st.markdown(f"#### [{title}]({url}){tag}")
                st.caption(f"🕓 {published_str} | 🏢 {source}")
                if summary:
                    st.markdown(
                        f"<div style='color:gray;font-style:italic;'>{summary}</div>",
                        unsafe_allow_html=True,
                    )
                st.markdown("---")

    st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
