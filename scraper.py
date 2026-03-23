import os
import requests
from bs4 import BeautifulSoup
import datetime

def get_wevity_contests():
    print("마스터, 기간 남은 공모전을 싹 긁어모으는 중입니다...")
    
    # 💡 위비티 차단을 뚫기 위한 가짜 브라우저 설정
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    # 모든 공모전이 나오는 리스트 페이지
    url = "https://www.wevity.com/?c=find&s=1" 
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        return f"❌ 사이트 접속 실패: {e}"

    # 공모전 리스트 영역 추출 (위비티 구조에 맞게 수정)
    contest_list = soup.select('ul.list_area li')
    
    now = datetime.datetime.now()
    result_text = f"🏆 **{now.strftime('%Y-%m-%d')} 기준 마감 전 공모전 리스트** 🏆\n"
    result_text += "------------------------------------------\n"
    
    count = 0
    for contest in contest_list:
        title_tag = contest.select_one('.tit a')
        dday_tag = contest.select_one('.day') 
        
        if title_tag and dday_tag:
            title = title_tag.text.strip()
            dday_str = dday_tag.text.strip() # 예: "2026-04-15"
            link = "https://www.wevity.com/" + title_tag['href']
            
            # 날짜 비교 로직
            is_valid = False
            if "상시" in dday_str:
                is_valid = True
                d_day_text = "상시"
            else:
                try:
                    # 날짜 형식(YYYY-MM-DD)인지 확인하고 오늘보다 이후면 포함
                    end_date = datetime.datetime.strptime(dday_str, '%Y-%m-%d')
                    if end_date.date() >= now.date():
                        is_valid = True
                        delta = end_date.date() - now.date()
                        d_day_text = f"D-{delta.days}" if delta.days > 0 else "D-Day"
                except:
                    continue
            
            if is_valid:
                result_text += f"{count+1}. **[{d_day_text}]** {title} [🔗]({link})\n"
                count += 1
                    
    if count == 0:
        result_text += "현재 진행 중인 공모전이 없습니다. 🧐\n"
    
    result_text += "\n------------------------------------------\n"
    result_text += f"💡 총 {count}개의 공모전을 발견했습니다."
    
    return result_text

# 1. 공모전 데이터 수집
final_report = get_wevity_contests()

# 2. 깃허브 액션이 읽을 수 있도록 파일 저장 (가장 중요!)
with open("issue_body.md", "w", encoding="utf-8") as f:
    f.write(final_report)

print("파일 저장 완료! 이제 깃허브가 이 내용을 읽어서 글을 쓸 겁니다.")
