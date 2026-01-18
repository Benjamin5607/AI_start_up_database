import os
import requests
import json
import time
import datetime
import jwt
import xml.etree.ElementTree as ET
from groq import Groq
from notion_client import Client

# --- Environments ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

# Ghost Credentials
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

# --- [Check] 노션 내 중복 데이터 확인 ---
def is_already_processed(link):
    try:
        # 노션의 '원문링크' 속성에서 해당 URL이 이미 존재하는지 쿼리
        query = notion.databases.query(
            database_id=NOTION_DATABASE_ID,
            filter={
                "property": "원문링크",
                "url": {"equals": link}
            }
        )
        return len(query.get("results", [])) > 0
    except Exception as e:
        print(f"⚠️ 중복 체크 중 오류 발생: {e}")
        return False

# --- [Collection] Google News RSS (다양화 및 최신 필터 적용) ---
def fetch_massive_infra_alpha():
    data = []
    # 중복을 피하기 위해 검색 범위를 넓히고 특정 기업 편중을 줄임
    queries = [
        "AI+datacenter+liquid+cooling+market+startups",
        "TSMC+advanced+packaging+supply+chain+news",
        "HBM4+HBM3E+semiconductor+manufacturing+partners",
        "AI+infrastructure+energy+power+grid+innovations",
        "Silicon+photonics+optical+interconnect+startups",
        "Edge+AI+hardware+chipset+breakthroughs",
        "NVIDIA+Blackwell+supply+chain+challenges" # 엔비디아는 하나로 축소
    ]
    headers = {"User-Agent": "Mozilla/5.0"}
    
    for q in queries:
        try:
            # &tbs=qdr:d 옵션으로 최근 24시간 이내의 뉴스만 필터링
            url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en&tbs=qdr:d"
            response = requests.get(url, headers=headers, timeout=15)
            root = ET.fromstring(response.content)
            
            for item in root.findall('.//item')[:10]:
                link = item.find('link').text
                # [중요] 노션에 이미 있는 데이터라면 리스트에 담지 않음
                if not is_already_processed(link):
                    data.append({'title': item.find('title').text, 'link': link})
                else:
                    print(f"⏭️ Skipping duplicate: {item.find('title').text[:30]}...")
        except: pass
        time.sleep(1)
    return data

# --- [Analysis] VC Analysis ---
def analyze_high_quality(title, link):
    prompt = f"""
    Analyze this for a Tier-1 VC Investment Report.
    Title: {title}
    Link: {link}
    STRICT RULES:
    1. Respond in JSON. 2. LANGUAGE: ENGLISH.
    3. Identify 2 relevant category tags (e.g., "Semiconductor", "Data Center", "Cooling", "Power", "Networking").
    JSON Structure:
    {{
        "entity_name": "Company name",
        "role": "Role in AI Ecosystem",
        "tech_analysis": "Technical moat analysis",
        "partners": "Major partners",
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
        return json.loads(completion.choices[0].message.content)
    except: return None

# --- [Load] Notion ---
def push_to_notion(data, link):
    try:
        notion_tags = [{"name": tag} for tag in data.get('tags', ["AI Infra"])]
        notion.pages.create(
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
        return True
    except: return False

# --- [Post] Ghost Admin API ---
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
        if res.status_code == 201:
            print(f"✅ Ghost Post Published: {title}")
        else:
            print(f"❌ Ghost Error: {res.json()}")
    except Exception as e:
        print(f"❌ Ghost Integration Error: {e}")

# --- [Image Finder] 회사 로고 이미지 자동 검색 ---
def find_company_logo(company_name):
    try:
        # DDG API를 통해 이미지 URL 확보 시도
        search_url = f"https://api.duckduckgo.com/?q={company_name} logo icon&format=json"
        res = requests.get(search_url, timeout=5).json()
        if res.get('Image'):
            return res['Image']
    except: pass
    return "https://via.placeholder.com/200?text=Company+Logo"

# --- [Report] 상/중/하 비교 리포트 생성 ---
def create_comparison_report(results):
    if not results: return
    
    all_tags = []
    for r in results: all_tags.extend(r.get('tags', []))
    target_cat = max(set(all_tags), key=all_tags.count) if all_tags else "AI Infrastructure"
    
    cat_items = [r for r in results if target_cat in r.get('tags', [])]
    cat_items.sort(key=lambda x: x['impact_score'], reverse=True)
    
    if len(cat_items) < 3: 
        print(f"⚠️ {target_cat} 카테고리에 비교할 데이터가 충분하지 않습니다 (현재 {len(cat_items)}개).")
        return
        
    high, mid, low = cat_items[0], cat_items[len(cat_items)//2], cat_items[-1]
    
    high_logo = find_company_logo(high['entity_name'])
    mid_logo = find_company_logo(mid['entity_name'])
    low_logo = find_company_logo(low['entity_name'])

    prompt = f"""
    Create a highly detailed, professional VC investment blog post in HTML format.
    The post must be at least A4 page equivalent in length (approx. 800-1000 words).
    Theme: Deep Dive into {target_cat} Market Trends and Investment Opportunities.
    
    Structure:
    1. <h2>Executive Summary: The Global Status of {target_cat}</h2>
    2. <h2>The Comparison: Market Leader vs Challenger vs Emerging</h2>
       - For each company, include: Entity Name, Role, Moat Analysis, and Investment Insight.
       - Use the provided image URLs in <img> tags.
    3. <h2>Macro Outlook: Industry Tailwinds and Challenges</h2>
    4. <h2>VC Conclusion: Strategic Takeaway</h2>
    
    Data:
    - Leader (Score {high['impact_score']}): {high['entity_name']} (Logo: {high_logo})
    - Challenger (Score {mid['impact_score']}): {mid['entity_name']} (Logo: {mid_logo})
    - Risky (Score {low['impact_score']}): {low['entity_name']} (Logo: {low_logo})
    
    STRICT RULES:
    - Pure HTML output only.
    - Elaborate deeply on business insights, industrial context, and global trends.
    """
    try:
        response = client.chat.completions.create(
            model=CURRENT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2500 
        )
        report_html = response.choices[0].message.content
        report_title = f"[Analysis] {target_cat} Deep-Dive: From Infrastructure to Alpha ({datetime.date.today()})"
        post_to_ghost(report_title, report_html)
    except Exception as e:
        print(f"❌ Report Generation Failed: {e}")

# --- Main ---
if __name__ == "__main__":
    print(f"🚀 AI Alpha Scraper v3 (Deduplication Enabled) Initiated.")
    raw_list = fetch_massive_infra_alpha()
    print(f"📦 Found {len(raw_list)} new unique candidates to analyze.")
    
    report_pool = []
    unique_links = set()
    success_count = 0
    
    for item in raw_list:
        if success_count >= 50: break
        if item['link'] in unique_links: continue # 중복 수집 방지
        
        print(f"[{success_count+1}/50] Analyzing: {item['title'][:50]}...")
        res = analyze_high_quality(item['title'], item['link'])
        
        if res and int(res.get('impact_score', 0)) >= 6:
            if push_to_notion(res, item['link']):
                report_pool.append(res)
                success_count += 1
                unique_links.add(item['link'])
                print(f"   ✅ Saved to Notion. 💤 Sleeping 8s...")
                time.sleep(8)
        else:
            time.sleep(1)

    if report_pool:
        print(f"📝 Creating In-depth Comparison Report (Target Pool: {len(report_pool)} items)...")
        create_comparison_report(report_pool)

    print(f"🏁 Mission Complete. {success_count} new leads added.")
