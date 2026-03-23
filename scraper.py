import os
import requests
from bs4 import BeautifulSoup

def get_wevity_contests():
    print("마스터, 풍성한 리스트를 준비 중입니다...")
    url = "https://www.wevity.com/"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 공모전 리스트 추출
    contest_list = soup.select('.wevity-main-list li')
    
    import datetime
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    
    result_text = f"🏆 **{today} 공모전 데일리 리포트** 🏆\n"
    result_text += "*(최신 업데이트 및 진행 중인 공모전 Top 15)*\n"
    result_text += "------------------------------------------\n"
    
    # 5개에서 15개로 대폭 확장! (신규가 없어도 지난 며칠간의 데이터가 나옵니다)
    for i, contest in enumerate(contest_list[:15]):
        title_tag = contest.select_one('.tit a')
        # 위비티에서 기간/D-day 정보도 가져오기 (부실함을 막아주는 핵심!)
        dday_tag = contest.select_one('.day') 
        
        if title_tag:
            title = title_tag.text.strip()
            dday = dday_tag.text.strip() if dday_tag else "진행중"
            link = "https://www.wevity.com/" + title_tag['href']
            
            # [D-Day] 제목 [링크] 형태로 구성
            result_text += f"{i+1}. **[{dday}]** {title[:30]} [🔗]({link})\n"
            
    result_text += "\n------------------------------------------\n"
    result_text += "💡 상세 내용은 위비티 홈페이지를 확인하세요!"
    
    return result_text

def send_telegram(text):
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN') 
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    
    if not bot_token or not chat_id:
        print("로컬 테스트이거나 토큰이 없습니다. 텔레그램 발송을 건너뜁니다.")
        return

    print("텔레그램으로 메시지를 전송합니다...")
    url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'Markdown',
        'disable_web_page_preview': True
    }
    
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print("성공적으로 전송 완료했습니다, 마스터!")
    else:
        print(f"전송 실패 ㅠㅠ: {response.text}")

# 1. 공모전 데이터 긁어오기
scraped_data = get_wevity_contests()

# 2. 텔레그램으로 보내기
send_telegram(scraped_data)

# 3. 깃허브 웹(Issue)에 올리기 위해 마크다운 파일로 저장 (5점짜리 핵심!)
with open("issue_body.md", "w", encoding="utf-8") as f:
    f.write(scraped_data)
