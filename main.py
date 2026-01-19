import os
import requests
import json
import time
import datetime
from datetime import timedelta # 날짜 계산용
import jwt
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

# --- [Check 1] 중복 수집 방지 ---
def is_already_processed(link):
    try:
        query = notion.databases.query(
            database_id=NOTION_DATABASE_ID,
            filter={"property": "원문링크", "url": {"equals": link}}
        )
        return len(query.get("results", [])) > 0
    except: return False

# --- [Check 2] 7일 쿨타임 금지 목록 조회 (NEW) ---
def get_banned_entities():
    banned_names = []
    try:
        # 오늘 기준 7일 전 날짜 계산
        seven_days_ago = (datetime.date.today() - timedelta(days=7)).isoformat()
        
        # LastPublished가 7일 이내인 데이터 조회
        query = notion.databases.query(
            database_id=NOTION_DATABASE_ID,
            filter={
                "property": "LastPublished",
                "date": {"on_or_after": seven_days_ago}
            }
        )
        for page in query.get("results", []):
            # 회사명 추출
            props = page.get("properties", {})
            title_list = props.get("회사명", {}).get("title", [])
            if title_list:
                banned_names.append(title_list[0].get("text", {}).get("content", ""))
        
        print(f"🚫 Banned Companies (Cooldown Active): {banned_names}")
        return set(banned_names)
    except Exception as e:
        print(f"⚠️ 쿨타임 조회 실패 (속성 없음?): {e}")
        return set()

# --- [Action] 블로그 발행 후 날짜 도장 찍기 (NEW) ---
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
            url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en&tbs=qdr:d"
            response = requests.get(url, headers=headers, timeout=15)
            root = ET.fromstring(response.content)
            for item in root.findall('.//item')[:5]: # 쿼리당 5개로 제한 (너무 많음 방지)
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

# --- [Load] Notion ---
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
        # 생성된 페이지 ID를 반환하여 나중에 업데이트할 수 있게 함
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
    return "https://via.placeholder.com/200?text=No+Logo"

# --- [Report] Comparison ---
def create_comparison_report(results, banned_set):
    if not results: return
    
    # 태그 빈도수 계산
    all_tags = []
    for r in results: all_tags.extend(r.get('tags', []))
    target_cat = max(set(all_tags), key=all_tags.count) if all_tags else "AI Infra"
    
    # 1차 필터링: 해당 카테고리 + 금지 목록 제외
    candidates = []
    for r in results:
        is_target_cat = target_cat in r.get('tags', [])
        is_banned = r['entity_name'] in banned_set
        if is_target_cat and not is_banned:
            candidates.append(r)
    
    candidates.sort(key=lambda x: x['impact_score'], reverse=True)
    
    # 후보가 부족하면 쿨타임 무시하고 그냥 가져옴 (예외 처리)
    if len(candidates) < 3:
        print("⚠️ Not enough unique candidates. Ignoring cooldown for this run.")
        candidates = [r for r in results if target_cat in r.get('tags', [])]
        candidates.sort(key=lambda x: x['impact_score'], reverse=True)

    if len(candidates) < 3: return
    
    high, mid, low = candidates[0], candidates[len(candidates)//2], candidates[-1]
    
    # 로고 찾기
    high_logo = find_company_logo(high['entity_name'])
    mid_logo = find_company_logo(mid['entity_name'])
    low_logo = find_company_logo(low['entity_name'])

    prompt = f"""
    Write a detailed A4-length HTML blog post.
    Theme: {target_cat} Investment Analysis.
    
    Structure:
    1. <h2>Market Pulse: {target_cat}</h2> (Industry Context)
    2. <h2>The Triad Analysis</h2> (Comparison Table style in text)
       - Compare Leader vs Challenger vs Emerging.
       - Use <img> tags for logos.
    3. <h2>Deep Dive</h2> (Analysis of each)
    4. <h2>Verdict</h2> (Investment Strategy)
    
    Companies:
    - Leader: {high['entity_name']} (Score {high['impact_score']}) - {high['tech_analysis']} (Logo: {high_logo})
    - Challenger: {mid['entity_name']} (Score {mid['impact_score']}) - {mid['tech_analysis']} (Logo: {mid_logo})
    - Emerging: {low['entity_name']} (Score {low['impact_score']}) - {low['tech_analysis']} (Logo: {low_logo})
    
    Output: HTML only. Professional Tone.
    """
    
    try:
        response = client.chat.completions.create(
            model=CURRENT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2500
        )
        html = response.choices[0].message.content
        title = f"[Weekly Alpha] {target_cat}: {high['entity_name']} vs {mid['entity_name']} ({datetime.date.today()})"
        
        post_to_ghost(title, html)
        
        # [중요] 사용된 기업들 노션에 '사용됨' 도장 찍기
        print("📝 Updating Cooldown status in Notion...")
        if 'page_id' in high: mark_as_published(high['page_id'])
        if 'page_id' in mid: mark_as_published(mid['page_id'])
        if 'page_id' in low: mark_as_published(low['page_id'])
        
    except Exception as e: print(f"❌ Report Gen Failed: {e}")

# --- Main ---
if __name__ == "__main__":
    print("🚀 AI Bot Started. Fetching Banned List...")
    
    # 1. 금지 목록(쿨타임) 가져오기
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
            # 노션에 저장하면서 page_id 받아옴
            if push_to_notion(res, item['link']):
                report_pool.append(res)
                success_count += 1
                unique_links.add(item['link'])
                print(f"   ✅ Saved: {res['entity_name']}")
                time.sleep(5)
        else:
            time.sleep(1)

    if report_pool:
        print(f"📊 Generating Blog Post (Excluding {len(banned_companies)} banned items)...")
        # 금지 목록을 넘겨줘서 필터링 수행
        create_comparison_report(report_pool, banned_companies)

    print("🏁 Done.")
