import requests
from bs4 import BeautifulSoup
import datetime
import time

def get_wevity_new_contests():
    print("🚀 마스터가 주신 '신규 리스트' 주소로 침투를 시도합니다...")
    
    # 💡 차단을 뚫기 위한 정교한 헤더 (실제 브라우저와 똑같이 세팅)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Referer': 'https://www.google.com/',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
    }

    # 영서햄이 주신 신규 리스트 전용 URL
    url = "https://www.wevity.com/?c=find&s=1&gub=&cidx=&gbn=list&mode=new"
    
    try:
        # 세션을 사용해 쿠키를 생성하며 접속
        session = requests.Session()
        session.get("https://www.wevity.com/", headers=headers, timeout=10)
        time.sleep(1) # 사람처럼 1초 쉬기
        
        response = session.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        return f"❌ 위비티 신규 리스트 접속 실패: {e}\n(여전히 깃허브 IP가 차단된 상태일 수 있습니다.)"

    # 신규 리스트 영역 추출
    contest_list = soup.select('.list_area li')
    
    now = datetime.datetime.now()
    result_text = f"🏆 **{now.strftime('%Y-%m-%d')} 신규 공모전 TOP 5** 🏆\n"
    result_text += "*(위비티 신규 리스트 기준 실시간 업데이트)*\n"
    result_text += "------------------------------------------\n"
    
    count = 0
    for contest in contest_list:
        title_tag = contest.select_one('.tit a')
        dday_tag = contest.select_one('.day')
        
        if title_tag and dday_tag:
            title = title_tag.text.strip()
            dday = dday_tag.text.strip()
            link = "https://www.wevity.com/" + title_tag['href']
            
            result_text += f"{count+1}. **[{dday}]** {title[:28]}.. [🔗]({link})\n"
            count += 1
            
            # 딱 5개만 가져오기
            if count >= 5: break
                    
    if count == 0:
        result_text += "신규 공모전을 찾지 못했습니다. (차단 혹은 사이트 구조 변경) 🧐\n"
    
    result_text += f"\n💡 총 {count}개의 신규 공모전을 발견했습니다!"
    return result_text

# 1. 실행 및 결과 파일 저장
final_report = get_wevity_new_contests()
with open("issue_body.md", "w", encoding="utf-8") as f:
    f.write(final_report)

print("✅ 신규 리스트 저장 완료! 깃허브 액션 결과를 기다립니다.")
