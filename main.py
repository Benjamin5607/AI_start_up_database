import os
import requests
import json
import time
import datetime
from bs4 import BeautifulSoup
from groq import Groq
from notion_client import Client

# --- 환경변수 ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

groq_client = Groq(api_key=GROQ_API_KEY)
notion_client = Client(auth=NOTION_API_KEY)

# --- [핵심] 현재 살아있는 모델 자동 감지 ---
def get_alive_model():
    try:
        models = groq_client.models.list()
        available_models = [m.id for m in models.data]
        
        # 1순위: 70b (똑똑한 놈)이면서 최신(3.x)
        for m in available_models:
            if "70b" in m and "llama-3" in m:
                print(f"🤖 모델 자동 선택됨: {m}")
                return m
        # 2순위: 70b 아무거나
        for m in available_models:
            if "70b" in m:
                print(f"🤖 모델 자동 선택됨(대타): {m}")
                return m
        # 3순위: 그냥 아무거나
        return available_models[0]
    except:
        return "llama-3.3-70b-versatile" # 비상용 하드코딩

CURRENT_MODEL = get_alive_model()

# --- [수집] TechCrunch (기존 방식 유지 - 라이브러리 추가 필요없음) ---
def get_techcrunch_news():
    url = "https://techcrunch.com/category/artificial-intelligence/"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    articles = []
    # TechCrunch 구조 (loop-card 기준)
    for item in soup.select('.loop-card__title-link')[:3]: 
        title = item.get_text().strip()
        link = item['href']
        articles.append({'title': title, 'link': link})
    
    return articles

# --- [가공] Groq ---
def analyze_with_groq(title, link):
    prompt = f"""
    Analyze this startup news for a VC investor.
    Title: {title}
    Link: {link}
    
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
            model=CURRENT_MODEL, # 👈 자동 선택된 모델 사용
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
    print(f"🚀 뉴스 수집기 가동 (Model: {CURRENT_MODEL})")
    news_list = get_techcrunch_news()
    
    if not news_list:
        print("⚠️ 뉴스를 못 찾았습니다. (사이트 구조 변경 가능성)")
    
    for news in news_list:
        print(f"Processing: {news['title']}...")
        ai_data = analyze_with_groq(news['title'], news['link'])
        if ai_data:
            upload_to_notion(ai_data, news['link'])
        time.sleep(2)
