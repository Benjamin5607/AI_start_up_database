import os
import requests
import json
import time
import datetime
import xml.etree.ElementTree as ET # RSS 파싱용
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

# --- [Collection] Google News RSS (Massive & Reliable) ---
def fetch_massive_infra_alpha():
    data = []
    # Google News RSS queries for AI Infrastructure
    queries = [
        "NVIDIA+Blackwell+supply+chain",
        "AI+Data+Center+cooling+solutions",
        "TSMC+CoWoS+partners",
        "Semiconductor+startup+funding",
        "AI+infrastructure+power+grid"
    ]
    
    for q in queries:
        try:
            # Google News RSS는 차단이 거의 없고 데이터가 풍부함
            url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
            response = requests.get(url, timeout=10)
            root = ET.fromstring(response.content)
            
            for item in root.findall('.//item')[:15]: # 쿼리당 15개씩 확보
                title = item.find('title').text
                link = item.find('link').text
                data.append({'title': title, 'link': link})
        except Exception as e:
            print(f"⚠️ Query '{q}' failed: {e}")
        time.sleep(1)
    
    return data

# --- [Analysis & Load 통합] ---
def process_and_push(item, success_count):
    # AI 분석 프롬프트 (Category 태그 포함)
    prompt = f"""
    Analyze this for a Tier-1 VC Investment Report.
    Title: {item['title']}
    Link: {item['link']}

    STRICT RULES:
    1. Respond in JSON. 2. LANGUAGE: ENGLISH.
    3. Identify 2-3 relevant category tags (e.g., "Semiconductor", "Data Center", "Cooling", "Power", "Networking", "AI Startup").

    JSON Structure:
    {{
        "entity_name": "Company/Project Name",
        "role": "Role in AI Ecosystem",
        "tech_analysis": "Technical moat analysis",
        "partners": "Major partners",
        "impact_score": 1-10,
        "investment_insight": "VC perspective insight",
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
        
        # 점수 필터링 (6점 이상만)
        if int(res.get('impact_score', 0)) >= 6:
            notion_tags = [{"name": tag} for tag in res.get('tags', ["AI Infra"])]
            notion.pages.create(
                parent={"database_id": NOTION_DATABASE_ID},
                properties={
                    "회사명": {"title": [{"text": {"content": res['entity_name']}}]},
                    "Category": {"multi_select": notion_tags},
                    "투자규모": {"rich_text": [{"text": {"content": res['role']}}]},
                    "한줄요약": {"rich_text": [{"text": {"content": res['tech_analysis']}}]},
                    "비즈니스모델": {"rich_text": [{"text": {"content": f"Partners: {res['partners']} | Insight: {res['investment_insight']}"}}]},
                    "매력도": {"number": int(res['impact_score'])},
                    "날짜": {"date": {"start": datetime.date.today().isoformat()}},
                    "원문링크": {"url": item['link']}
                }
            )
            print(f"   ✅ [{success_count+1}/50] Added: {res['entity_name']} (Score: {res['impact_score']})")
            return True
    except Exception as e:
        print(f"   ❌ Error processing {item['title'][:30]}: {e}")
    return False

if __name__ == "__main__":
    print(f"🚀 Global AI Infra Scraper Initiated. (Model: {CURRENT_MODEL})")
    raw_candidates = fetch_massive_infra_alpha()
    print(f"📦 Total {len(raw_candidates)} candidates found. Processing...")

    unique_links = set()
    success_count = 0
    
    for item in raw_candidates:
        if success_count >= 50: break
        if not item.get('link') or item['link'] in unique_links: continue
        
        print(f"Analyzing candidate: {item['title'][:50]}...")
        if process_and_push(item, success_count):
            success_count += 1
            unique_links.add(item['link'])
            print(f"   💤 Sleeping 8 seconds to stay safe...")
            time.sleep(8)
        else:
            time.sleep(1) # Skip 시에도 짧은 휴식

    print(f"🏁 Finished. Total {success_count} leads added to Notion.")
