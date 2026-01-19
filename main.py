import os
import requests
import json
import time
import datetime
from datetime import timedelta
import jwt  # pip install pyjwt
import xml.etree.ElementTree as ET
from groq import Groq
from notion_client import Client

# --- Environments ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")
GHOST_API_KEY = os.environ.get("GHOST_API_KEY")
GHOST_API_URL = os.environ.get("GHOST_API_URL")

client = Groq(api_key=GROQ_API_KEY)
notion = Client(auth=NOTION_API_KEY)

def get_best_model():
    try:
        models = client.models.list()
        ids = [m.id for m in models.data]
        return "llama-3.3-70b-versatile" if "llama-3.3-70b-versatile" in ids else ids[0]
    except: return "llama-3.3-70b-versatile"

CURRENT_MODEL = get_best_model()

# --- [Function 1] 중복 뉴스 수집 방지 (링크 기준) ---
def is_already_processed(link):
    try:
        query = notion.databases.query(
            database_id=NOTION_DATABASE_ID,
            filter={"property": "원문링크", "url": {"equals": link}}
        )
        return len(query.get("results", [])) > 0
    except: return False

# --- [Function 2] 7일 쿨타임 금지 목록 조회 ---
def get_banned_entities():
    banned_names = []
    try:
        seven_days_ago = (datetime.date.today() - timedelta(days=7)).isoformat()
        
        # LastPublished 날짜가 7일 이내인 기업 조회
        query = notion.databases.query(
            database_id=NOTION_DATABASE_ID,
            filter={
                "property": "LastPublished",
                "date": {"on_or_after": seven_days_ago}
            }
        )
        for page in query.get("results", []):
            props = page.get("properties", {})
            title_list = props.get("회사명", {}).get("title", [])
            if title_list:
                banned_names.append(title_list[0].get("text", {}).get("content", ""))
        
        if banned_names:
            print(f"🚫 Cooldown Active (Banned for 7 days): {set(banned_names)}")
        return set(banned_names)
    except Exception as e:
        print(f"⚠️ 쿨타임 조회 실패 (속성 없음?): {e}")
        return set()

# --- [Function 3] 블로그 발행 후 도장 찍기 ---
def mark_as_published(page_id):
    try:
        notion.pages.update(
            page_id=page_id,
            properties={
                "LastPublished": {"date": {"start": datetime.date.today().isoformat()}}
            }
        )
    except Exception as e:
        print(f"⚠️ 발행일 업데이트 실패: {e}")

# --- [Function 4] 기업 히스토리 조회 (추세 분석용) ---
def fetch_company_history(company_name):
    try:
        # 해당 기업명의 과거 기록을 날짜순으로 조회
        query = notion.databases.query(
            database_id=NOTION_DATABASE_ID,
            filter={
                "property": "회사명",
                "title": {"equals": company_name}
            },
            sorts=[{"property": "날짜", "direction": "ascending"}]
        )
        
        history_text = ""
        results = query.get("results", [])
        
        # 최근 5개 데이터만 요약해서 문자열로 만듦
        for page in results[-5:]:
            props = page['properties']
            try:
                date = props['날짜']['date']['start']
                score = props['매력도']['number']
                summary = props['한줄요약']['rich_text'][0]['text']['content']
                history_text += f"- [{date}] Score {score}/10: {summary}\n"
            except: continue
            
        if not history_text:
            return "No historical data available (New Entry)."
        return history_text
    except Exception as e:
        return f"Error fetching history: {e}"

# --- [Collection] Google News RSS ---
def fetch_massive_infra_alpha():
    data = []
    queries = [
        "AI+datacenter+liquid+cooling+market",
        "TSMC+CoWoS+packaging+supply+chain",
        "HBM4+manufacturing+yield+news",
        "AI+infrastructure+nuclear+SMR+power",
        "Silicon+photonics+optical+interconnect",
        "NVIDIA+Blackwell+GB200+delivery+update",
        "AI+semiconductor+startup+funding"
    ]
    headers = {"User-Agent": "Mozilla/5.0"}
    for q in queries:
        try:
            # &tbs=qdr:d (최근 24시간)
            url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en&tbs=qdr:d"
            response = requests.get(url, headers=headers, timeout=15)
            root = ET.fromstring(response.content)
            for item in root.findall('.//item')[:5]: 
                link = item.find('link').text
                if not is_already_processed(link):
                    data.append({'title': item.find('title').text, 'link': link})
        except: pass
        time.sleep(1)
    return data

# --- [Analysis] VC Analysis ---
def analyze_high_quality(title, link):
    prompt = f"""
    Analyze for VC Investment Report. Title: {title} Link: {link}
    RULES: 1. JSON only. 2. English.
    JSON: {{
        "entity_name": "Company Name",
        "role": "Role",
        "tech_analysis": "Moat analysis",
        "partners": "Partners",
        "impact_score": 1-10,
        "investment_insight": "Insight",
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
    except: return None

# --- [Load] Notion (Append Mode for History) ---
def push_to_notion(data, link):
    try:
        notion_tags = [{"name": tag} for tag in data.get('tags', ["AI Infra"])]
        response = notion.pages.create(
            parent={"database_id": NOTION_DATABASE_ID},
            properties={
                "회사명": {"title": [{"text": {"content": data['entity_name']}}]},
                "Category": {"multi_select": notion_tags},
                "투자규모": {"rich_text": [{"text": {"content": data['role']}}]},
                "한줄요약": {"rich_text": [{"text": {"content": data['tech_analysis']}}]},
                "비즈니스모델": {"rich_text": [{"text": {"content": f"Partners: {data['partners']} | Insight: {data['investment_insight']}"}}]},
                "매력도": {"number": int(data.get('impact_score', 0))},
                "날짜": {"date": {"start": datetime.date.today().isoformat()}},
                "원문링크": {"url": link}
            }
        )
        data['page_id'] = response['id'] 
        return True
    except: return False

# --- [Ghost] Post ---
def post_to_ghost(title, html_content):
    try:
        key_id, secret = GHOST_API_KEY.split(':')
        iat = int(time.time())
        header = {'alg': 'HS256', 'typ': 'JWT', 'kid': key_id}
        payload = {'iat': iat, 'exp': iat + 5 * 60, 'aud': '/admin/'}
        token = jwt.encode(payload, bytes.fromhex(secret), algorithm='HS256', headers=header)
        
        url = f"{GHOST_API_URL.rstrip('/')}/ghost/api/admin/posts/?source=html"
        headers = {'Authorization': f'Ghost {token}'}
        body = {"posts": [{"title": title, "html": html_content, "status": "published"}]}
        
        res = requests.post(url, json=body, headers=headers)
        if res.status_code == 201: print(f"✅ Ghost Post Published: {title}")
        else: print(f"❌ Ghost Error: {res.json()}")
    except Exception as e: print(f"❌ Ghost Integration Error: {e}")

# --- [Image Finder] ---
def find_company_logo(company_name):
    try:
        search_url = f"https://api.duckduckgo.com/?q={company_name} logo vector&iax=images&ia=images&format=json"
        res = requests.get(search_url, timeout=5).json()
        if res.get('Image'): return res['Image']
    except: pass
    return "https://via.placeholder.com/200?text=Logo"

# --- [Report] Comparison with History & Trend ---
def create_comparison_report(results, banned_set):
    if not results: return
    
    # 카테고리 선정
    all_tags = []
    for r in results: all_tags.extend(r.get('tags', []))
    target_cat = max(set(all_tags), key=all_tags.count) if all_tags else "AI Infra"
    
    # 쿨타임 필터링
    candidates = []
    for r in results:
        is_target_cat = target_cat in r.get('tags', [])
        is_banned = r['entity_name'] in banned_set
        if is_target_cat and not is_banned:
            candidates.append(r)
    
    candidates.sort(key=lambda x: x['impact_score'], reverse=True)
    
    # 후보 부족 시 쿨타임 해제 (예외 처리)
    if len(candidates) < 3:
        print("⚠️ Not enough unique candidates. Ignoring cooldown for this run.")
        candidates = [r for r in results if target_cat in r.get('tags', [])]
        candidates.sort(key=lambda x: x['impact_score'], reverse=True)

    if len(candidates) < 3: return
    
    high, mid, low = candidates[0], candidates[len(candidates)//2], candidates[-1]
    
    # 히스토리 데이터 조회
    high_hist = fetch_company_history(high['entity_name'])
    mid_hist = fetch_company_history(mid['entity_name'])
    low_hist = fetch_company_history(low['entity_name'])

    # 로고 조회
    high_logo = find_company_logo(high['entity_name'])
    mid_logo = find_company_logo(mid['entity_name'])
    low_logo = find_company_logo(low['entity_name'])

    prompt = f"""
    Write a detailed A4-length HTML blog post.
    Theme: {target_cat} Market Analysis & Future Outlook.
    
    KEY INSTRUCTION: Analyze the provided 'Historical Data' to determine the trend (Rising, Falling, Stable).
    
    Structure:
    1. <h2>Market Pulse: {target_cat}</h2>
    2. <h2>Trend Analysis: Leader vs Challenger vs Emerging</h2>
       - Include a "Trend Verdict" for each company based on history.
       - Use <img> tags for logos.
    3. <h2>Deep Dive</h2>
    4. <h2>Verdict & Strategy</h2>
    
    Companies:
    1. LEADER: {high['entity_name']} (Score {high['impact_score']})
       - Logo: {high_logo}
       - Insight: {high['tech_analysis']}
       - HISTORY: {high_hist}
       
    2. CHALLENGER: {mid['entity_name']} (Score {mid['impact_score']})
       - Logo: {mid_logo}
       - Insight: {mid['tech_analysis']}
       - HISTORY: {mid_hist}
       
    3. EMERGING: {low['entity_name']} (Score {low['impact_score']})
       - Logo: {low_logo}
       - Insight: {low['tech_analysis']}
       - HISTORY: {low_hist}
    
    Output: HTML only. Professional VC Tone.
    """
    
    try:
        response = client.chat.completions.create(
            model=CURRENT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=3000
        )
        html = response.choices[0].message.content
        title = f"[Trend Report] {target_cat}: {high['entity_name']} vs {mid['entity_name']} ({datetime.date.today()})"
        
        post_to_ghost(title, html)
        
        # [중요] 사용된 기업들 노션에 '사용됨' 도장 찍기 (쿨타임 시작)
        print("📝 Updating Cooldown status in Notion...")
        if 'page_id' in high: mark_as_published(high['page_id'])
        if 'page_id' in mid: mark_as_published(mid['page_id'])
        if 'page_id' in low: mark_as_published(low['page_id'])
        
    except Exception as e: print(f"❌ Report Gen Failed: {e}")

# --- Main ---
if __name__ == "__main__":
    print("🚀 AI Bot Started. Fetching Banned List...")
    
    # 1. 쿨타임(7일) 목록 가져오기
    banned_companies = get_banned_entities()
    
    raw_list = fetch_massive_infra_alpha()
    report_pool = []
    unique_links = set()
    success_count = 0
    
    for item in raw_list:
        if success_count >= 50: break
        if item['link'] in unique_links: continue
        
        res = analyze_high_quality(item['title'], item['link'])
        
        if res and int(res.get('impact_score', 0)) >= 6:
            # 노션에 데이터 저장 (Append Mode)
            if push_to_notion(res, item['link']):
                report_pool.append(res)
                success_count += 1
                unique_links.add(item['link'])
                print(f"   ✅ Saved: {res['entity_name']}")
                time.sleep(5) # 8초 -> 5초로 약간 단축
        else:
            time.sleep(1)

    if report_pool:
        print(f"📊 Generating Blog Post (Trend Analysis Included)...")
        create_comparison_report(report_pool, banned_companies)

    print("🏁 Done.")
