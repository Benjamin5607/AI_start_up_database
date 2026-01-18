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

# --- [Collection] Deep & Massive Infra Scraper ---
def fetch_massive_infra_alpha():
    data = []
    # More specific and diverse queries to reach 50+ candidates
    queries = [
        "NVIDIA Blackwell supply chain partners and suppliers",
        "AI Data Center liquid cooling solutions startups",
        "TSMC CoWoS packaging capacity and partners",
        "Top AI infrastructure companies list 2024 2025",
        "HBM4 technology roadmap and supply chain",
        "ASML EUV supply chain companies",
        "Data center power grid and SMR nuclear energy providers",
        "Optical interconnects and silicon photonics for AI",
        "Hyperscale data center construction partners",
        "NVIDIA GH200 GB200 component suppliers"
    ]
    
    for q in queries:
        try:
            url = f"https://api.duckduckgo.com/?q={q}&format=json"
            res = requests.get(url).json()
            # Grab up to 8 topics per query to ensure volume
            for topic in res.get('RelatedTopics', [])[:8]:
                if 'FirstURL' in topic:
                    data.append({'title': topic['Text'], 'link': topic['FirstURL'], 'category': 'Infra/SupplyChain'})
        except: pass
        time.sleep(1) # Small gap between search queries

    # Add Hacker News for more volume
    try:
        hn_url = "http://hn.algolia.com/api/v1/search?query=semiconductor OR hardware OR datacenter&tags=story&hitsPerPage=20"
        res = requests.get(hn_url).json()
        for h in res['hits']:
            data.append({'title': h['title'], 'link': h['url'], 'category': 'Tech Alpha'})
    except: pass

    return data

# --- [Analysis] VC Analysis (English) ---
def analyze_as_pro(title, link, category):
    prompt = f"""
    Analyze this for a Tier-1 VC Investment Report.
    Title: {title}
    Link: {link}
    Category: {category}

    STRICT RULES:
    1. Respond in JSON. 2. LANGUAGE: ENGLISH.
    3. Be specific about the 'Moat' (Competitive Advantage).

    JSON Structure:
    {{
        "entity_name": "Company name",
        "role": "Role in AI Ecosystem (e.g. Partner, Supplier)",
        "tech_analysis": "Depth of technical moat",
        "partners": "Major partners (NVIDIA, TSMC, etc.)",
        "impact_score": 1-10,
        "investment_insight": "Why this matters now"
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

# --- [Load] Notion ---
def push_to_notion(data, link):
    notion.pages.create(
        parent={"database_id": NOTION_DATABASE_ID},
        properties={
            "회사명": {"title": [{"text": {"content": data['entity_name']}}]},
            "투자규모": {"rich_text": [{"text": {"content": data['role']}}]},
            "한줄요약": {"rich_text": [{"text": {"content": data['tech_analysis']}}]},
            "비즈니스모델": {"rich_text": [{"text": {"content": f"Partners: {data['partners']} | Insight: {data['investment_insight']}"}}]},
            "매력도": {"number": int(data.get('impact_score', 0))},
            "원문링크": {"url": link}
        }
    )

if __name__ == "__main__":
    print(f"🚀 Massive Scrape Initiated. Target: 50 High-Value Leads.")
    raw_candidates = fetch_massive_infra_alpha()
    
    unique_links = set()
    success_count = 0
    
    for item in raw_candidates:
        if success_count >= 50: break # Stop at 50
        if not item['link'] or item['link'] in unique_links: continue
        
        print(f"[{success_count+1}/50] Analyzing: {item['title'][:50]}...")
        res = analyze_as_pro(item['title'], item['link'], item['category'])
        
        # We only take the best (Impact Score 7+)
        if res and int(res.get('impact_score', 0)) >= 7:
            push_to_notion(res, item['link'])
            print(f"   ✅ Added: {res['entity_name']}")
            success_count += 1
            unique_links.add(item['link'])
            
            # THE 8-SECOND SLEEP as requested
            print(f"   💤 Sleeping 8 seconds to stay safe...")
            time.sleep(8)
        else:
            # Short sleep even for skipped items to be safe
            time.sleep(2)

    print(f"🏁 Finished. Total {success_count} premium leads added to Notion.")
