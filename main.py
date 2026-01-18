import os
import requests
import json
import time
import datetime
from bs4 import BeautifulSoup
from groq import Groq
from notion_client import Client

# --- 1. 환경변수 로드 (GitHub Secrets에서 가져옴) ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

# 클라이언트 초기화
groq_client = Groq(api_key=GROQ_API_KEY)
notion_client = Client(auth=NOTION_API_KEY)

# --- 2. [수집] TechCrunch AI 뉴스 크롤링 ---
def get_techcrunch_news():
    url = "https://techcrunch.com/category/artificial-intelligence/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    articles = []
    # TechCrunch 구조 (변경 가능성 있음, loop-card 클래스 기준)
    # 최신 5개만 가져오기
    for item in soup.select('.loop-card__title-link')[:5]: 
        title = item.get_text().strip()
        link = item['href']
        articles.append({'title': title, 'link': link})
    
    return articles

# --- 3. [가공] Groq (Llama3-70b) 요약 ---
def analyze_with_groq(title, link):
    prompt = f"""
    You are a professional VC analyst. Analyze the startup news below.
    Article: {title} ({link})
    
    Output purely in JSON format (Korean):
    {{
        "company_name": "회사명(영문)",
        "funding": "투자금액(예: $10M) 혹은 '정보없음'",
        "summary": "초등학생도 이해하는 1줄 요약(존댓말)",
        "bm": "수익 모델(돈 버는 법) 간략 설명",
        "score": "투자 매력도(1~10점)"
    }}
    """
    
    try:
        completion = groq_client.chat.completions.create(
            model="llama3-70b-8192", # Groq에서 가장 똑똑한 모델
            messages=[
                {"role": "system", "content": "You are a JSON generator."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"} # JSON 모드 강제
        )
        return json.loads(completion.choices[0].message.content)
    except Exception as e:
        print(f"Groq Error: {e}")
        return None

# --- 4. [적재] 노션 업로드 ---
def upload_to_notion(data, link):
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

# --- 실행 로직 ---
if __name__ == "__main__":
    print("🚀 뉴스 수집 시작...")
    news_list = get_techcrunch_news()
    
    for news in news_list:
        print(f"Processing: {news['title']}...")
        
        # Groq 분석
        ai_data = analyze_with_groq(news['title'], news['link'])
        
        if ai_data:
            # 노션 업로드
            upload_to_notion(ai_data, news['link'])
            print("✅ 업로드 완료")
        else:
            print("❌ 분석 실패")
            
        # Groq 무료 티어 배려 (너무 빠르면 막힐 수 있음)
        time.sleep(2) 
        
    print("🎉 오늘 업무 끝! (이제 노션 확인하세요)")
