import os
import requests
import json
import time
import datetime
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

# --- [Collection] 데이터 수집 ---
def fetch_massive_infra_alpha():
    data = []
    queries = [
        "NVIDIA Blackwell supply chain partners",
        "AI Data Center liquid cooling solutions",
        "TSMC CoWoS packaging partners",
        "HBM4 supply chain companies",
        "Data center power grid SMR nuclear",
        "Silicon photonics AI networking",
        "Hyperscale data center construction",
        "NVIDIA component suppliers GB200"
    ]
    
    for q in queries:
        try:
            # DuckDuckGo HTML 구조 대응을 위해 쿼리 최적화
            url = f"https://api.duckduckgo.com/?q={q}&format=json"
            res = requests.get(url, timeout=10).json()
            for topic in res.get('RelatedTopics', [])[:10]:
                if 'FirstURL' in topic:
                    data.append({'title': topic['Text'], 'link': topic['FirstURL']})
        except: pass
        time.sleep(1)

    # Hacker News 보강 (데이터 확보용)
    try:
        hn_url = "http://hn.algolia.com/api/v1/search?query=semiconductor OR datacenter&tags=story&hitsPerPage=30"
        res = requests.get(hn_url).json()
        for h in res['hits']:
            data.append({'title': h['title'], 'link': h['url']})
    except: pass
    return data

# --- [Analysis] VC Analysis (With Tags) ---
def analyze_high_quality(title, link):
    prompt = f"""
    Analyze this for a Tier-1 VC Investment Report.
    Title: {title}
    Link: {link}

    STRICT RULES:
    1. Respond in JSON. 2. LANGUAGE: ENGLISH.
    3. Identify 2-3 relevant category tags (e.g., "Semiconductor", "Data Center", "Cooling", "Power", "Networking", "AI Startup").

    JSON Structure:
    {{
        "entity_name": "Company name",
        "role": "Role in AI Ecosystem",
        "tech_analysis": "Depth of technical moat",
        "partners": "Major partners",
        "impact_score": 1-10,
        "investment_insight": "Why this matters now",
        "tags": ["Tag1", "Tag2"]
    }}
    """
    try:
        completion = client.chat.completions.create(
            model=CURRENT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(completion.choices[0].message.content)
    except Exception as e:
        print(f"   ❌ AI Analysis Error: {e}")
        return None

# --- [Load] Notion ---
def push_to_notion(data, link):
    try:
        notion_tags = [{"name": tag} for tag in data.get('tags', ["AI Infra"])]
        notion.pages.create(
            parent={"database_id": NOTION_DATABASE_ID},
            properties={
                "회사명": {"title": [{"text": {"content": data['entity_name']}}]},
                "Category": {"multi_select": notion_tags}, # 노션에 'Category' 속성(다중선택)이 있어야 함
                "투자규모": {"rich_text": [{"text": {"content": data['role']}}]},
                "한줄요약": {"rich_text": [{"text": {"content": data['tech_analysis']}}]},
                "비즈니스모델": {"rich_text": [{"text": {"content": f"Partners: {data['partners']} | Insight: {data['investment_insight']}"}}]},
                "매력도": {"number": int(data.get('impact_score', 0))},
                "날짜": {"date": {"start": datetime.date.today().isoformat()}},
                "원문링크": {"url": link}
            }
        )
        return True
    except Exception as e:
        print(f"   ❌ Notion Push Error: {e}")
        return False

# --- Main Execution ---
if __name__ == "__main__":
    print(f"🚀 Massive Scrape Initiated. Target: 50 Premium Leads.")
    raw_candidates = fetch_massive_infra_alpha()
    print(f"📦 Total {len(raw_candidates)} candidates found. Filtering...")

    unique_links = set()
    success_count = 0
    
    for item in raw_candidates:
        if success_count >= 50: break
        if not item.get('link') or item['link'] in unique_links: continue
        
        print(f"[{success_count+1}/50] Analyzing: {item['title'][:50]}...")
        res = analyze_high_quality(item['title'], item['link'])
        
        # 필터링 점수를 5점으로 살짝 낮춰서 데이터 확보를 원활하게 함
        if res and int(res.get('impact_score', 0)) >= 5:
            if push_to_notion(res, item['link']):
                print(f"   ✅ Added: {res['entity_name']} (Score: {res['impact_score']})")
                success_count += 1
                unique_links.add(item['link'])
                print(f"   💤 Sleeping 8 seconds...")
                time.sleep(8)
        else:
            time.sleep(1)

    print(f"🏁 Finished. Total {success_count} leads added to Notion.")
