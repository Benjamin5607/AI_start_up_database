import os
import requests
import json
import time
import datetime
from groq import Groq
from notion_client import Client

# --- 환경변수 ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

groq_client = Groq(api_key=GROQ_API_KEY)
notion_client = Client(auth=NOTION_API_KEY)

# --- [모델 선택] 자동 감지 ---
def get_alive_model():
    try:
        models = groq_client.models.list()
        available_models = [m.id for m in models.data]
        for m in available_models:
            if "70b" in m and "llama-3" in m: return m # 1순위
        return available_models[0] # 아무거나
    except:
        return "llama-3.3-70b-versatile"

CURRENT_MODEL = get_alive_model()

# --- [수집] Hacker News (Algolia API 사용 - 엄청 빠름) ---
def get_hn_ai_news():
    # 'AI', 'LLM', 'GPT' 키워드로 최근 24시간 내 핫한 글 검색
    # hitsPerPage=15 -> 15개 긁어오기
    url = "http://hn.algolia.com/api/v1/search_by_date?query=AI OR LLM OR GPT&tags=story&hitsPerPage=15"
    response = requests.get(url)
    data = response.json()
    
    articles = []
    print(f"🔍 Hacker News 검색 결과: {len(data['hits'])}개 발견")
    
    for item in data['hits']:
        title = item.get('title')
        url = item.get('url')
        points = item.get('points', 0)
        
        # URL 없는 토론글은 제외하고, 반응(점수)이 좀 있는 것만 필터링
        if url and points is not None: 
            articles.append({'title': title, 'link': url, 'points': points})
    
    return articles

# --- [가공] Groq (냉철한 투자자 모드) ---
def analyze_with_groq(title, link, points):
    prompt = f"""
    You are a cynical VC analyst. Evaluate this early-stage tech/news from Hacker News.
    Title: {title}
    Link: {link}
    Hacker News Score: {points} (High score means high dev interest)
    
    Output strictly JSON (Korean):
    {{
        "company_name": "Product/Company Name (Eng)",
        "funding": "Unknown (Assume 'Early Stage')",
        "summary": "What is this? (Explain simply for non-techies)",
        "bm": "How can this make money? (Be creative)",
        "score": Score 1-10 (Based on business potential, not just tech hype)
    }}
    """
    try:
        completion = groq_client.chat.completions.create(
            model=CURRENT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(completion.choices[0].message.content)
    except Exception as e:
        print(f"❌ Groq Error: {e}")
        return None

# --- [적재] 노션 ---
def upload_to_notion(data, link):
    try:
        notion_client.pages.create(
            parent={"database_id": NOTION_DATABASE_ID},
            properties={
                "회사명": {"title": [{"text": {"content": data.get("company_name", "Unknown")}}]},
                # HN은 초기라 투자금액이 없는 경우가 많음 -> 'Early Stage'로 통일
                "투자규모": {"rich_text": [{"text": {"content": data.get("funding", "-")}}]},
                "한줄요약": {"rich_text": [{"text": {"content": data.get("summary", "-")}}]},
                "비즈니스모델": {"rich_text": [{"text": {"content": data.get("bm", "-")}}]},
                "매력도": {"number": int(data.get("score", 0))},
                "날짜": {"date": {"start": datetime.date.today().isoformat()}},
                "원문링크": {"url": link}
            }
        )
        print(f"✅ 노션 업로드 성공: {data.get('company_name')}")
    except Exception as e:
        print(f"❌ 노션 업로드 실패: {e}")

# --- 실행 ---
if __name__ == "__main__":
    print(f"🚀 HN Alpha 수집기 가동 (Model: {CURRENT_MODEL})")
    news_list = get_hn_ai_news()
    
    if not news_list:
        print("⚠️ 검색 결과 없음")
    
    for news in news_list:
        print(f"Processing: {news['title']} (Score: {news['points']})...")
        ai_data = analyze_with_groq(news['title'], news['link'], news['points'])
        if ai_data:
            upload_to_notion(ai_data, news['link'])
        # 무료 API 매너 타임 (너무 빠르면 막힘)
        time.sleep(1.5)
