import requests
from bs4 import BeautifulSoup
import datetime

def get_campusmon_contests():
    print("🚀 마스터, 캠퍼스몬에서 공모전 정보를 안전하게 수집 중입니다...")
    
    # 캠퍼스몬 '전체 공모전' 리스트 페이지 (최신순)
    url = "https://campusmon.jobkorea.co.kr/Contest/Search?Pkid=0"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        return f"❌ 사이트 접속 실패: {e}"

    # 공모전 리스트 영역 추출 (캠퍼스몬 구조 반영)
    contest_list = soup.select('ul.list-default li')
    
    now = datetime.datetime.now()
    result_text = f"🏆 **{now.strftime('%Y-%m-%d')} 기준 최신 공모전 리포트** 🏆\n"
    result_text += "*(캠퍼스몬 기준 진행 중인 공모전 리스트입니다)*\n"
    result_text += "------------------------------------------\n"
    
    count = 0
    for contest in contest_list:
        title_tag = contest.select_one('span.tit a')
        dday_tag = contest.select_one('span.day') # D-Day 정보
        
        if title_tag and dday_tag:
            title = title_tag.text.strip()
            dday_text = dday_tag.text.strip() # 예: "D-25", "오늘마감", "상시"
            link = "https://campusmon.jobkorea.co.kr" + title_tag['href']
            
            # 마감된 공모전은 건너뛰기
            if "마감" in dday_text and dday_text != "오늘마감":
                continue
                
            result_text += f"{count+1}. **[{dday_text}]** {title[:28]}.. [🔗]({link})\n"
            count += 1
            
            # 너무 길면 잘릴 수 있으니 상위 20개 정도만 가져옵니다.
            if count >= 20: break
                    
    if count == 0:
        result_text += "현재 진행 중인 공모전을 찾지 못했습니다. 🧐\n"
    
    result_text += f"\n💡 총 {count}개의 공모전 발견!"
    return result_text

# 1. 실행 및 파일 저장
final_report = get_campusmon_contests()
with open("issue_body.md", "w", encoding="utf-8") as f:
    f.write(final_report)

print("✅ 파일 저장 완료! 이제 깃허브가 이 내용을 읽어서 글을 쓸 겁니다.")
