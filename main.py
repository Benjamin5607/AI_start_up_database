import os
import requests
import json
import time
from groq import Groq
from notion_client import Client

# --- Environments ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

client = Groq(api_key=GROQ_API_KEY)
notion = Client(auth=NOTION_API_KEY)

def get_best_model():
    try:
        models = client.models.list()
        ids = [m.id for m in models.data]
        return "llama-3.3-70b-versatile" if "llama-3.3-70b-versatile" in ids else ids[0]
    except: return "llama-3.3-70b-versatile"

CURRENT_MODEL = get_best_model()

# --- [Collection] Multi-Source English Scraper ---
def fetch_raw_alpha():
    data = []
    # 1. Targeted News (AI Semi & Video) via DuckDuckGo
    queries = ["AI semiconductor startup funding news", "Generative video AI venture capital"]
    for q in queries:
        try:
            url = f"https://api.duckduckgo.com/?q={q}&format=json"
            res = requests.get(url).json()
            for topic in res.get('RelatedTopics', [])[:5]:
                if 'FirstURL' in topic:
                    data.append({'title': topic['Text'], 'link': topic['FirstURL'], 'source': 'Global News'})
        except: pass

    # 2. Tech-Alpha (Hacker News High Points)
    try:
        hn_url = "http://hn.algolia.com/api/v1/search?query=AI&tags=story&numericFilters=points>100"
        res = requests.get(hn_url).json()
        for h in res['hits'][:10]:
            data.append({'title': h['title'], 'link': h['url'], 'source': 'HackerNews'})
    except: pass

    return data

# --- [Analysis] Professional VC Analysis (All English) ---
def analyze_as_vc(title, link, source):
    prompt = f"""
    You are a Senior Partner at a Top-tier Silicon Valley VC. 
    Analyze the following information and provide a high-value investment report for premium subscribers.
    
    Info: {title}
    Source: {source}
    Link: {link}

    STRICT RULES:
    1. Respond ONLY in JSON format.
    2. EVERYTHING in the JSON must be in ENGLISH.
    3. Be critical and analytical. Avoid generic summaries.

    JSON Structure:
    {{
        "company_name": "Target entity or project name",
        "funding_status": "Estimated funding round (e.g. Series C, Stealth, Debt Financing)",
        "tech_edge": "Deep-dive into their technical moat or competitive advantage",
        "business_viability": "How will they dominate the market? Revenue model and Exit potential",
        "investment_score": 1-10 (Strictly based on ROI potential),
        "expert_insight": "A sharp, non-obvious insight connecting this to macro-tech trends (e.g. CUDA dominance, HBM supply chain)"
    }}
    """
    try:
        completion = client.chat.completions.create(
            model=CURRENT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(completion.choices[0].message.content)
    except: return None

# --- [Load] Notion Update (All English) ---
def push_to_notion(data, link):
    notion.pages.create(
        parent={"database_id": NOTION_DATABASE_ID},
        properties={
            "회사명": {"title": [{"text": {"content": data['company_name']}}]},
            "투자규모": {"rich_text": [{"text": {"content": data['funding_status']}}]},
            "한줄요약": {"rich_text": [{"text": {"content": data['tech_edge']}}]},
            "비즈니스모델": {"rich_text": [{"text": {"content": f"BM: {data['business_viability']} | Insight: {data['expert_insight']}"}}]},
            "매력도": {"number": int(data['investment_score'])},
            "원문링크": {"url": link}
        }
    )

if __name__ == "__main__":
    print(f"🚀 High-Alpha Scraper Initiated (Model: {CURRENT_MODEL})")
    raw_list = fetch_raw_alpha()
    
    unique_links = set()
    for item in raw_list:
        if item['link'] and item['link'] not in unique_links:
            print(f"Analyzing: {item['title'][:60]}...")
            analysis = analyze_as_vc(item['title'], item['link'], item['source'])
            
            # Only push high-quality leads (Score 8+)
            if analysis and int(analysis.get('investment_score', 0)) >= 8:
                push_to_notion(analysis, item['link'])
                print(f"✅ Premium Lead Uploaded: {analysis['company_name']}")
                unique_links.add(item['link'])
            time.sleep(8)
