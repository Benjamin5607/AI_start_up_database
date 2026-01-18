import os
import feedparser
import json
import time
import datetime
from groq import Groq
from notion_client import Client
from bs4 import BeautifulSoup

# --- 환경변수 ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

groq_client = Groq(api_key=GROQ_API_KEY)
notion_client = Client(auth=NOTION_API_KEY)

# --- [핵심] 현재 살아있는 모델 중 짱 센 놈 데려오기 ---
def get_alive_model():
    try:
        models = groq_client.models.list()
        # 사용 가능한 모델 리스트 확보
        available_models = [m.id for m in models.data]
        
        # 1순위: 70b (똑똑한 놈)이면서 최신(3.x)인 놈 찾기
        for m in available_models:
            if "70b" in m and "llama-3" in m:
                print(f"🤖 모델 자동 선택됨: {m}")
                return m
        
        # 2순위: 70b 아무거나
        for m in available_models:
            if "70b" in m:
                print(f"🤖 모델 자동 선택됨(대타): {m}")
                return m
                
        # 3순위: 에라 모르겠다 아무거나 (보통 8b)
        fallback = available_models[0]
        print(f"🤖 모델 자동 선택됨(최후의 수단): {fallback}")
        return fallback
        
    except Exception as e:
        print(f"⚠️ 모델 목록 조회 실패, 기본값 사용: {e}")
        return "llama-3.3-70b-versatile" # 최후의 보루

# 전역 변수로 모델 확정
CURRENT_MODEL = get_alive_model()

# --- [수집] TechCrunch RSS ---
def get_techcrunch_rss():
    rss_url = "https://techcrunch.com/category/artificial-intelligence/feed/"
    feed = feedparser.parse(rss_url)
    
    articles = []
    print(f"🔍 RSS 검색 결과: {len(feed.entries)}개의 기사 발견")
    
    for entry in feed.entries[:3]: 
        title = entry.title
        link = entry.link
        summary_text = BeautifulSoup(entry.description, "html.parser").get_text()
        articles.append({'title': title, 'link': link, 'content': summary_text})
    
    return articles

# --- [가공] Groq ---
def analyze_with_groq(title, content):
    prompt = f"""
    Analyze this startup news for a VC investor.
    Title: {title}
    Content Snippet: {content}
    
    Output strictly JSON (Korean):
    {{
        "company_name": "회사명(영문)",
        "funding": "투자금액(예: $10M) 없으면 '정보없음'",
        "summary": "1줄 요약(존댓말)",
        "bm": "수익 모델",
        "score": 1 to 10
    }}
    """
    try:
        completion = groq_client.chat.completions.create(
            model=CURRENT_MODEL, # 👈 아까 선발한 그 놈 들어감
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(completion.choices[0].message.content)
    except Exception as e:
        print(f"❌ Groq Error ({CURRENT_MODEL}): {e}")
        return None

# --- [적재] 노션 ---
def upload_to_notion(data, link):
    try:
        notion_client.pages.create(
            parent={"database_id": NOTION_DATABASE_ID},
            properties={
                "회사명": {"title": [{"text": {"content": data.get("company_name", "Unknown")}}]},
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
    print(f"🚀 뉴스 수집기 가동 (Selected Model: {CURRENT_MODEL})...")
    news_list = get_techcrunch_rss()
    
    if not news_list:
        print("⚠️ 뉴스를 못 찾았습니다.")
    
    for news in news_list:
        print(f"Processing: {news['title']}...")
        ai_data = analyze_with_groq(news['title'], news['content'])
        if ai_data:
            upload_to_notion(ai_data, news['link'])
        time.sleep(2)
