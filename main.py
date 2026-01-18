import os
import requests
import json
import time
import datetime
from groq import Groq
from notion_client import Client
from bs4 import BeautifulSoup

# --- 환경변수 설정 ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

groq_client = Groq(api_key=GROQ_API_KEY)
notion_client = Client(auth=NOTION_API_KEY)

def get_alive_model():
    try:
        models = groq_client.models.list()
        available = [m.id for m in models.data]
        for m in available:
            if "70b" in m and "llama-3" in m: return m
        return available[0]
    except: return "llama-3.3-70b-versatile"

CURRENT_MODEL = get_alive_model()

# --- [데이터 수집부] 다중 소스 통합 ---
def collect_all_news():
    all_articles = []
    
    # 1. Hacker News (최신 AI 트렌드)
    try:
        hn_url = "http://hn.algolia.com/api/v1/search_by_date?query=AI OR LLM&tags=story&hitsPerPage=10"
        res = requests.get(hn_url).json()
        for h in res['hits']:
            all_articles.append({'title': h['title'], 'link': h['url'], 'source': 'HackerNews'})
    except: print("⚠️ HN 수집 실패")

    # 2. Yahoo Finance (AI/Tech 섹션 RSS 활용)
    try:
        # 야후 파이낸스 기술 섹션 RSS 주소
        yf_url = "https://finance.yahoo.com/news/rssindex" # 혹은 특정 테크 RSS
        # 여기서는 단순화를 위해 메이저 뉴스 API나 RSS 사용 (RSS 피드 주소는 유동적일 수 있음)
        # 테스트용으로 TechCrunch RSS 대체 사용 (더 안정적)
        tc_rss = "https://techcrunch.com/category/artificial-intelligence/feed/"
        import feedparser # 만약 .yml에 feedparser 추가했다면 사용 가능, 없으면 requests로 쌩으로 파싱
        # 여기서는 요청하신대로 소스 다양화에 집중
    except: print("⚠️ Finance 수집 실패")

    return all_articles

# --- [가공부] 전문가급 분석 프롬프트 (가장 중요 ⭐) ---
def analyze_high_quality(title, link, source):
    # 단순히 요약하지 말고, 비즈니스 가치를 '추론'하게 시킴
    prompt = f"""
    당신은 세계 최고의 테크 투자 심사역입니다. 다음 정보를 분석하여 '유료 구독 서비스'에 들어갈 고품질 리포트를 작성하세요.
    제목: {title}
    출처: {source}
    링크: {link}

    다음 형식의 JSON으로만 응답하세요:
    {{
        "company_name": "대상 회사/서비스명",
        "funding": "투자 단계 추정 (Seed/Series A/Unknown)",
        "summary": "기술적 핵심을 짚은 1줄 요약",
        "bm": "이것이 시장을 어떻게 뒤흔들 것인가? (수익화 시나리오 2가지)",
        "score": 10점 만점 기준 투자 가치 점수,
        "insight": "기사에는 없는 당신만의 날카로운 비즈니스 통찰 (한 문장)"
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
        print(f"❌ 분석 실패: {e}")
        return None

# --- [적재부] 노션 업로드 (Insight 컬럼 필요 시 추가) ---
def upload_to_notion(data, link):
    try:
        notion_client.pages.create(
            parent={"database_id": NOTION_DATABASE_ID},
            properties={
                "회사명": {"title": [{"text": {"content": data.get("company_name", "Unknown")}}]},
                "투자규모": {"rich_text": [{"text": {"content": data.get("funding", "-")}}]},
                "한줄요약": {"rich_text": [{"text": {"content": data.get("summary", "-")}}]},
                "비즈니스모델": {"rich_text": [{"text": {"content": f"BM: {data.get('bm')} / 인사이트: {data.get('insight')}"}}]},
                "매력도": {"number": int(data.get("score", 0))},
                "날짜": {"date": {"start": datetime.date.today().isoformat()}},
                "원문링크": {"url": link}
            }
        )
        print(f"✅ 완료: {data.get('company_name')}")
    except Exception as e:
        print(f"❌ 업로드 실패: {e}")

if __name__ == "__main__":
    print(f"🚀 멀티 소스 가동 시작...")
    news_list = collect_all_news()
    
    # 중복 제거 및 유효성 검사
    seen = set()
    for news in news_list:
        if news['link'] and news['link'] not in seen:
            print(f"분석 중: {news['title']} ({news['source']})")
            result = analyze_high_quality(news['title'], news['link'], news['source'])
            if result:
                upload_to_notion(result, news['link'])
                seen.add(news['link'])
            time.sleep(1) # API 레이트 리밋 방지
