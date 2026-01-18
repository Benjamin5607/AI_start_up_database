import os
import requests
import json
import time
import datetime
import xml.etree.ElementTree as ET # RSS 파싱용 (표준 라이브러리)
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

# --- [Collection] Google News RSS (Massive & High-Quality) ---
def fetch_massive_infra_alpha():
    data = []
    # 쿼리에 공백 대신 +를 써서 구글 뉴스 RSS 주소를 만듭니다.
    queries = [
        "NVIDIA+Blackwell+supply+chain",
        "AI+Data+Center+cooling+solutions",
        "TSMC+CoWoS+packaging+partners",
        "Semiconductor+startup+funding+news",
        "AI+infrastructure+power+grid+SMR",
        "Silicon+photonics+AI+networking"
    ]
    
    headers = {"User-Agent": "Mozilla/5.0"}

    for q in queries:
        try:
            # 구글 뉴스 RSS는 데이터를 아주 잘 뱉어줍니다.
            url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
            response = requests.get(url, headers=headers, timeout=15)
            # RSS(XML) 파싱
            root = ET.fromstring(response.content)
            
            for item in root.findall('.//item')[:10]: # 쿼리당 10개씩 확보
                title = item.find('title').text
                link = item.find('link').text
                data.append({'title': title, 'link': link})
            print(f"📊 Query '{q}' success: Found items.")
        except Exception as e:
            print(f"⚠️ Query '{q}' failed: {e}")
        time.sleep(1)
    
    return data

# --- [Analysis & Load 통합] ---
def process_and_push(item, success_count):
    prompt = f"""
    Analyze this for a Tier-1 VC Investment Report. 
    Focus on AI Infrastructure, Data Centers, and Semiconductor Supply Chains.
    
    Title: {item['title']}
    Link: {item['link']}

    STRICT RULES:
    1. Respond ONLY in JSON. 2. LANGUAGE: ENGLISH.
    3. Categorize into 2-3 tags (e.g., "Semiconductor", "Data Center", "Cooling", "Power", "Networking", "AI Startup").

    JSON Structure:
    {{
        "entity_name": "Company/Project Name",
        "role": "Role in AI Ecosystem (e.g., Supplier, Partner, Builder)",
        "tech_analysis": "Deep dive into their technical moat",
        "partners": "Major partners or customers",
        "impact_score": 1-10,
        "investment_insight": "VC strategic insight",
        "tags": ["Tag1", "Tag2"]
    }}
    """
    try:
        completion = client.chat.completions.create(
            model=CURRENT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        res = json.loads(completion.choices[0].message.content)
        
        # 6점 이상 고가치 정보만 노션 전송
        if int(res.get('impact_score', 0)) >= 6:
            notion_tags = [{"name": tag} for tag in res.get('tags', ["AI Infra"])]
            notion.pages.create(
                parent={"database_id": NOTION_DATABASE_ID},
                properties={
                    "회사명": {"title": [{"text": {"content": res['entity_name']}}]},
                    "Category": {"multi_select": notion_tags}, # 노션에 'Category' 컬럼 필수
                    "투자규모": {"rich_text": [{"text": {"content": res['role']}}]},
                    "한줄요약": {"rich_text": [{"text": {"content": res['tech_analysis']}}]},
                    "비즈니스모델": {"rich_text": [{"text": {"content": f"Partners: {res['partners']} | Insight: {res['investment_insight']}"}}]},
                    "매력도": {"number": int(res['impact_score'])},
                    "날짜": {"date": {"start": datetime.date.today().isoformat()}},
                    "원문링크": {"url": item['link']}
                }
            )
            return res['entity_name'], res['impact_score']
    except Exception as e:
        print(f"   ❌ AI/Notion Error: {e}")
    return None

if __name__ == "__main__":
    print(f"🚀 Google News RSS Aggregator Initiated. (Model: {CURRENT_MODEL})")
    raw_candidates = fetch_massive_infra_alpha()
    print(f"📦 Total {len(raw_candidates)} candidates found. Processing...")

    unique_links = set()
    success_count = 0
    
    for item in raw_candidates:
        if success_count >= 50: break
        if not item.get('link') or item['link'] in unique_links: continue
        
        print(f"Analyzing: {item['title'][:60]}...")
        result = process_and_push(item, success_count)
        
        if result:
            name, score = result
            success_count += 1
            unique_links.add(item['link'])
            print(f"   ✅ [{success_count}/50] Added: {name} (Score: {score})")
            print(f"   💤 Sleeping 8 seconds...")
            time.sleep(8)
        else:
            time.sleep(1)

    print(f"🏁 Finished. Total {success_count} premium leads added to Notion.")
