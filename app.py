import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from notion_client import Client
import datetime

# 1. 설정 (API 키 등)
NOTION_API_KEY = "내_노션_API_키"
NOTION_DATABASE_ID = "내_노션_DB_아이디"
OPENAI_API_KEY = "내_GPT_API_키"

client = Client(auth=NOTION_API_KEY)
gpt = OpenAI(api_key=OPENAI_API_KEY)

# 2. [수집] TechCrunch AI 카테고리 크롤링 (예시)
def get_ai_news():
    url = "https://techcrunch.com/category/artificial-intelligence/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    articles = []
    # TechCrunch 구조에 맞춰 기사 제목/링크 추출 (사이트 구조 변경 시 수정 필요)
    for item in soup.select('.post-block__title a')[:5]: # 상위 5개만
        title = item.get_text().strip()
        link = item['href']
        articles.append({'title': title, 'link': link})
    
    return articles

# 3. [가공] GPT에게 요약 및 데이터 구조화 시키기
def summarize_article(title, link):
    prompt = f"""
    아래 기사 제목을 보고, 이 스타트업에 대한 정보를 다음 JSON 형식으로 추출 및 번역해줘.
    기사 링크: {link}
    기사 제목: {title}
    
    형식:
    {{
        "회사명": "회사 이름 (영문)",
        "투자규모": "투자 금액 (없으면 '정보 없음')",
        "한줄요약": "이 회사가 뭐 하는 곳인지 초등학생도 이해하게 한국어로 1줄 요약",
        "비즈니스모델": "어떻게 돈을 버는 구조인지 한국어로 설명"
    }}
    """
    
    response = gpt.chat.completions.create(
        model="gpt-4o-mini", # 싸고 빠름
        messages=[{"role": "user", "content": prompt}]
    )
    
    return response.choices[0].message.content

# 4. [적재] 노션 데이터베이스에 꽂아넣기
def upload_to_notion(data, link):
    client.pages.create(
        parent={"database_id": NOTION_DATABASE_ID},
        properties={
            "회사명": {"title": [{"text": {"content": data['회사명']}}]},
            "투자규모": {"rich_text": [{"text": {"content": data['투자규모']}}]},
            "한줄요약": {"rich_text": [{"text": {"content": data['한줄요약']}}]},
            "핵심 BM": {"rich_text": [{"text": {"content": data['비즈니스모델']}}]},
            "날짜": {"date": {"start": datetime.date.today().isoformat()}},
            "원문링크": {"url": link}
        }
    )

# --- 실행 파이프라인 ---
if __name__ == "__main__":
    print("1. 뉴스 수집 중...")
    news_list = get_ai_news()
    
    for news in news_list:
        print(f"2. {news['title']} 분석 중...")
        # 실제로는 여기서 GPT 비용 절감을 위해 중복 체크 로직 추가 권장
        ai_summary_json = summarize_article(news['title'], news['link'])
        
        # GPT가 준 문자열을 딕셔너리로 변환 (eval이나 json.loads 사용)
        import json
        data = json.loads(ai_summary_json)
        
        print("3. 노션 업로드 중...")
        upload_to_notion(data, news['link'])
        
    print("✅ 오늘치 업데이트 완료! 이제 노션 확인해보세요.")
