import os
import requests
import json
import time
from groq import Groq
from notion_client import Client

# --- 환경변수 로드 ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID")

client = Groq(api_key=GROQ_API_KEY)
notion = Client(auth=NOTION_API_KEY)

def get_best_model():
    try:
        models = client.models.list()
        ids = [m.id for m in models.data]
        for m in ids:
            if "70b" in m: return m
        return ids[0]
    except: return "llama-3.3-70b-versatile"

CURRENT_MODEL = get_best_model()

# --- [수집] 영문 멀티 소스 (Hacker News + DuckDuckGo News) ---
def fetch_high_value_news():
    combined_data = []
    # 1. AI 반도체 & 생성형 비디오 타겟 검색 (DuckDuckGo API 활용)
    queries = ["AI Semiconductor startup funding", "Generative Video AI new companies"]
    
    for q in queries:
        try:
            # DuckDuckGo 뉴스 검색 (영문 전용)
            url = f"https://api.duckduckgo.com/?q={q}&format=json"
            res = requests.get(url).json()
            if res.get('RelatedTopics'):
                for topic in res['RelatedTopics'][:5]:
                    if 'Text' in topic:
                        combined_data.append({'title': topic['Text'], 'link': topic['FirstURL'], 'tag': q})
        except: print(f"⚠️ {q} 검색 실패")

    # 2. Hacker News (최고 점수 IT 뉴스)
    try:
        hn_url = "http://hn.algolia.com/api/v1/search?query=AI&tags=story&numericFilters=points>50"
        res = requests.get(hn_url).json()
        for h in res['hits'][:10]:
            combined_data.append({'title': h['title'], 'link': h['url'], 'tag': 'High-Impact Tech'})
    except: print("⚠️ HN 수집 실패")

    return combined_data

# --- [가공] 프로 투자자급 딥 애널리시스 ---
def deep_analyze(title, link, tag):
    prompt = f"""
    당신은 실리콘밸리 Tier-1 VC의 파트너입니다. 아래 영문 정보를 바탕으로 한국 투자자들을 위한 독점 리포트를 작성하세요.
    
    정보: {title}
    태그: {tag}
    관련링크: {link}

    반드시 아래 JSON 형식으로만 답변하세요:
    {{
        "company_name": "핵심 기업/프로젝트명",
        "funding": "투자 라운드 및 규모 추정 (예: Series B / $200M)",
        "summary": "기술적 진입장벽과 핵심 경쟁력 분석 (한국어)",
        "bm": "향후 3년 내 예상 수익 모델 및 엑시트 가능성",
        "score": 1-10점 사이의 투자 매력도,
        "insight": "이 정보가 왜 지금 중요한가? (거시경제 및 산업 트렌드와 연결)"
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

# --- [적재] 노션 업로드 ---
def push_to_notion(data, link):
    notion.pages.create(
        parent={"database_id": NOTION_DATABASE_ID},
        properties={
            "회사명": {"title": [{"text": {"content": data['company_name']}}]},
            "투자규모": {"rich_text": [{"text": {"content": data['funding']}}]},
            "한줄요약": {"rich_text": [{"text": {"content": data['summary']}}]},
            "비즈니스모델": {"rich_text": [{"text": {"content": f"BM: {data['bm']} / 인사이트: {data['insight']}"}}]},
            "매력도": {"number": int(data['score'])},
            "원문링크": {"url": link}
        }
    )

if __name__ == "__main__":
    print(f"🕵️‍♂️ 글로벌 AI 섹터(반도체/비디오) 정밀 스캔 시작... (Model: {CURRENT_MODEL})")
    news_list = fetch_high_value_news()
    
    for news in news_list:
        if not news['link']: continue
        print(f"🔍 분석 중: {news['title'][:50]}...")
        analysis = deep_analyze(news['title'], news['link'], news['tag'])
        if analysis and analysis.get('score', 0) >= 7: # 7점 이상의 고가치 정보만 엄선
            push_to_notion(analysis, news['link'])
            print(f"✅ 유료급 정보 업로드 완료: {analysis['company_name']}")
        time.sleep(2)
