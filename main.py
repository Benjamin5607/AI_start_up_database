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

# --- [Collection] Google News RSS ---
def fetch_massive_infra_alpha():
    data = []
    queries = [
        "NVIDIA+Blackwell+supply+chain",
        "AI+Data+Center+liquid+cooling+solutions",
        "TSMC+CoWoS+packaging+partners",
        "Semiconductor+startup+funding+news",
        "AI+infrastructure+power+grid+SMR",
        "Silicon+photonics+AI+networking"
    ]
    headers = {"User-Agent": "Mozilla/5.0"}
    for q in queries:
        try:
            url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
            response = requests.get(url, headers=headers, timeout=15)
            root = ET.fromstring(response.content)
            for item in root.findall('.//item')[:10]:
                data.append({'title': item.find('title').text, 'link': item.find('link').text})
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

# --- [Post] Ghost Admin API 연동 ---
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
    # Google Custom Search API 같은 것을 사용해야 정확하지만,
    # 여기서는 간단하게 DuckDuckGo Images를 활용합니다.
    try:
        search_url = f"https://api.duckduckgo.com/?q={company_name} logo&iax=images&ia=images&format=json"
        res = requests.get(search_url, timeout=5).json()
        if res.get('Image'):
            return res['Image'] # 첫 번째 이미지 URL 반환
    except: pass
    return "https://via.placeholder.com/150?text=Logo+NotFound" # 기본 이미지

# --- [Report] 상/중/하 비교 리포트 생성 ---
def create_comparison_report(results):
    if not results: return
    
    all_tags = []
    for r in results: all_tags.extend(r.get('tags', []))
    target_cat = max(set(all_tags), key=all_tags.count) if all_tags else "AI Infrastructure"
    
    cat_items = [r for r in results if target_cat in r.get('tags', [])]
    cat_items.sort(key=lambda x: x['impact_score'], reverse=True)
    
    if len(cat_items) < 3: return
    high, mid, low = cat_items[0], cat_items[len(cat_items)//2], cat_items[-1]
    
    # 이미지 URL 가져오기
    high_logo = find_company_logo(high['entity_name'])
    mid_logo = find_company_logo(mid['entity_name'])
    low_logo = find_company_logo(low['entity_name'])

    prompt = f"""
    Create a highly detailed, professional VC investment blog post in HTML format.
    The post must be at least A4 page equivalent in length (approx. 800-1000 words).
    Theme: Deep Dive into {target_cat} Market Trends and Investment Opportunities.
    
    Structure the post with:
    1.  <h2>Introduction: The Current Landscape of {target_cat} in AI Infrastructure</h2> - Explain its global significance and current industry status.
    2.  <h2>Featured Companies: A Head-to-Head Comparison</h2> - Use the provided data to compare the three companies.
        - Include each company's name, their logo image (provided as an <img> tag), impact score, role, technical moat, partners, and investment insight.
        - Detail their business insights and current market standing.
    3.  <h2>Global Outlook & Strategic Takeaways for Investors</h2> - Provide a macro perspective, future trends, and actionable investment advice.
    4.  <h2>Conclusion</h2>
    
    Company Details:
    - High Performer (Score {high['impact_score']}): {high['entity_name']} - Role: {high['role']}, Moat: {high['tech_analysis']}, Partners: {high['partners']}, Insight: {high['investment_insight']}
    - Challenger (Score {mid['impact_score']}): {mid['entity_name']} - Role: {mid['role']}, Moat: {mid['tech_analysis']}, Partners: {mid['partners']}, Insight: {mid['investment_insight']}
    - Emerging/Risky (Score {low['impact_score']}): {low['entity_name']} - Role: {low['role']}, Moat: {low['tech_analysis']}, Partners: {low['partners']}, Insight: {low['investment_insight']}
    
    Embed the logo images directly into the HTML within each company's section:
    - High Performer Logo: <img src="{high_logo}" alt="{high['entity_name']} Logo" style="width:150px; height:auto; display:block; margin: 10px 0;">
    - Challenger Logo: <img src="{mid_logo}" alt="{mid['entity_name']} Logo" style="width:150px; height:auto; display:block; margin: 10px 0;">
    - Emerging/Risky Logo: <img src="{low_logo}" alt="{low['entity_name']} Logo" style="width:150px; height:auto; display:block; margin: 10px 0;">

    Language: Professional, in-depth English. Ensure the output is pure HTML.
    """
    try:
        response = client.chat.completions.create(
            model=CURRENT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000 # A4 한 장 분량을 위해 토큰 수를 늘림
        )
        report_html = response.choices[0].message.content
        report_title = f"[Exclusive Analysis] {target_cat}: Leaders, Challengers & Future Trends ({datetime.date.today()})"
        post_to_ghost(report_title, report_html)
    except Exception as e:
        print(f"❌ Report Generation Failed: {e}")

# --- Main ---
if __name__ == "__main__":
    print(f"🚀 AI Alpha Scraper & Publisher Initiated.")
    raw_list = fetch_massive_infra_alpha()
    
    report_pool = []
    unique_links = set()
    success_count = 0
    
    for item in raw_list:
        if success_count >= 50: break
        if not item['link'] or item['link'] in unique_links: continue
        
        print(f"[{success_count+1}/50] Analyzing: {item['title'][:50]}...")
        res = analyze_high_quality(item['title'], item['link'])
        
        if res and int(res.get('impact_score', 0)) >= 6:
            if push_to_notion(res, item['link']):
                report_pool.append(res)
                success_count += 1
                unique_links.add(item['link'])
                print(f"   ✅ Added & Sleeping 8s...")
                time.sleep(8)
        else:
            time.sleep(1)

    if report_pool:
        print("📝 Creating In-depth Comparison Report for Ghost (with Images)...")
        create_comparison_report(report_pool)

    print(f"🏁 Mission Complete. {success_count} leads in Notion + 1 Rich Ghost Post.")
