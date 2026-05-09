#!/usr/bin/env python3
"""
Lead Signal Scanner - Simplified & High-Signal Version
Scans Reddit RSS + optional X for real consulting opportunities.
"""

import os
import json
import feedparser
from datetime import datetime, timezone
from typing import List, Dict


def load_config():
    with open("config/keywords.json") as f:
        return json.load(f)


def matches_intent(text: str, intent_keywords: List[str]) -> bool:
    text_lower = text.lower()
    return any(phrase in text_lower for phrase in intent_keywords)


def is_relevant_lead(title: str, text: str, topic_keywords: List[str]) -> bool:
    """Filter out irrelevant leads that don't match Harrison's expertise"""
    combined = f"{title} {text}".lower()

    # Harrison's expertise areas
    relevant_terms = [
        "data analytics",
        "predictive modeling",
        "machine learning",
        "ml",
        "ai",
        "industrial",
        "energy",
        "gas turbine",
        "turbine",
        "maintenance",
        "sensor data",
        "performance",
        "efficiency",
        "engineering",
        "python",
        "tensorflow",
        "keras",
        "model",
        "dataset",
        "analysis",
        "optimization",
        "manufacturing",
        "production",
        "power",
        "thermal",
        "mechanical",
    ]

    # Check if any relevant terms are present
    has_relevant_terms = any(term in combined for term in relevant_terms)

    # Exclude clearly irrelevant categories
    irrelevant_terms = [
        "gaming",
        "video edit",
        "content creator",
        "social media",
        "instagram",
        "youtube",
        "shoe brand",
        "fashion",
        "marketing campaign",
        "ui/ux",
        "frontend",
        "website design",
        "graphic design",
        "creative design",
        "account management",
        "hiring thread",
        "internship",
        "bbc",
        "property tax",
    ]

    has_irrelevant_terms = any(term in combined for term in irrelevant_terms)

    return has_relevant_terms and not has_irrelevant_terms


def score_lead(
    title: str,
    text: str,
    published,
    topic_keywords: List[str],
    intent_keywords: List[str],
) -> int:
    score = 0
    combined = f"{title} {text}".lower()

    # Strong intent in title = big points
    if any(
        w in title.lower()
        for w in [
            "looking for",
            "need help",
            "struggling with",
            "hiring",
            "seeking consultant",
        ]
    ):
        score += 6

    # Topic matches
    for kw in topic_keywords:
        if kw.lower() in combined:
            score += 2

    # Intent matches
    for kw in intent_keywords:
        if kw.lower() in combined:
            score += 2

    # Recency bonus
    try:
        age_hours = (datetime.now(timezone.utc) - published).total_seconds() / 3600
        if age_hours < 6:
            score += 5
        elif age_hours < 24:
            score += 3
        elif age_hours < 48:
            score += 1
    except:
        pass

    return score


def scan_reddit_rss(config) -> List[Dict]:
    leads = []
    for sub in config["subreddits"]:
        try:
            feed = feedparser.parse(f"https://www.reddit.com/r/{sub}/new.rss")
            for entry in feed.entries[:30]:  # latest 30 per sub
                title = entry.title
                text = getattr(entry, "summary", "") or getattr(
                    entry, "description", ""
                )
                published = (
                    datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                    if hasattr(entry, "published_parsed")
                    else datetime.now(timezone.utc)
                )

                if not matches_intent(f"{title} {text}", config["intent_keywords"]):
                    continue

                # Filter for relevance to Harrison's expertise
                if not is_relevant_lead(title, text, config["topic_keywords"]):
                    continue

                score = score_lead(
                    title,
                    text,
                    published,
                    config["topic_keywords"],
                    config["intent_keywords"],
                )
                if score < config.get("min_score", 4):
                    continue

                leads.append(
                    {
                        "source": "reddit",
                        "subreddit": sub,
                        "title": title,
                        "url": entry.link,
                        "text_snippet": (text or title)[:280],
                        "score": score,
                        "published": published.isoformat(),
                    }
                )
        except Exception as e:
            print(f"RSS error on r/{sub}: {e}")
            continue

    return leads


def scan_x(config) -> List[Dict]:
    # Optional - only runs if you add TWITTER_BEARER_TOKEN
    import tweepy

    bearer = os.environ.get("TWITTER_BEARER_TOKEN")
    if not bearer:
        return []

    client = tweepy.Client(bearer_token=bearer)
    query = '(("data analytics" OR "predictive modeling" OR "reliability engineer" OR "industrial analytics" OR "gas turbine") (consultant OR freelance OR "need help" OR "looking for" OR struggling OR hiring)) -filter:replies'

    leads = []
    try:
        tweets = client.search_recent_tweets(
            query=query,
            max_results=15,
            tweet_fields=["created_at", "text", "public_metrics"],
        )
        for tweet in tweets.data or []:
            text = tweet.text
            if not matches_intent(text, config["intent_keywords"]):
                continue
            score = score_lead(
                text,
                "",
                tweet.created_at,
                config["topic_keywords"],
                config["intent_keywords"],
            )
            if score < 5:
                continue
            leads.append(
                {
                    "source": "x",
                    "title": text[:120] + "..." if len(text) > 120 else text,
                    "url": f"https://x.com/i/status/{tweet.id}",
                    "text_snippet": text[:280],
                    "score": score,
                    "published": tweet.created_at.isoformat(),
                }
            )
    except Exception as e:
        print(f"X error: {e}")
    return leads


def generate_report(leads: List[Dict]) -> str:
    if not leads:
        return "No strong leads today. Keywords are working — just a quiet day."

    leads = sorted(leads, key=lambda x: x["score"], reverse=True)[:12]

    report = f"# Daily Lead Signals – {datetime.now().strftime('%Y-%m-%d')}\n\n"
    report += (
        "**Harrison Eller** | Data Analytics • Industrial AI • Energy & Gas Turbines\n"
    )
    report += (
        "ASME Turbo Expo 2024 Author • 50+ turbines • 2.2% avg efficiency gains\n\n"
    )

    for i, lead in enumerate(leads, 1):
        report += f"### {i}. {lead['source'].upper()} – Score {lead['score']}\n"
        report += f"**{lead['title']}**\n\n"
        report += f"{lead['text_snippet']}\n\n"
        report += f"[View Post]({lead['url']})\n\n"
        report += "**Suggested outreach (copy-paste ready):**\n\n"
        report += "Hi there,\n\n"
        report += f"Saw your post about {lead['title'][:60]}... — I built something very similar for 50+ gas turbines.\n\n"
        report += "I published a DNN model (TensorFlow/Keras) that predicts performance with 0.55–0.7 ppm MAE and quantified real efficiency gains after maintenance. The same approach works great for industrial sensor data and predictive modeling.\n\n"
        report += "Happy to share the exact approach if helpful. No pitch — just thought it might save you time.\n\n"
        report += "15-min call this week?\n\n"
        report += "Best,\nHarrison Eller\nLinkedIn: https://www.linkedin.com/in/harrison-eller-46934b184/\n\n"
        report += "---\n\n"

    return report


if __name__ == "__main__":
    config = load_config()
    print("Scanning Reddit RSS feeds...")
    reddit_leads = scan_reddit_rss(config)
    print(f"Found {len(reddit_leads)} Reddit leads")

    print("Scanning X (if token present)...")
    x_leads = scan_x(config)
    print(f"Found {len(x_leads)} X leads")

    all_leads = reddit_leads + x_leads
    report = generate_report(all_leads)

    print("\n" + "=" * 60)
    print(report)
    print("=" * 60)

    # Save for GitHub Action
    with open("/tmp/daily-leads.md", "w") as f:
        f.write(report)
