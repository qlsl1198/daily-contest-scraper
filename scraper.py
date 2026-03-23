import os # 맨 위 import 부분에 이거 하나 추가해주세요!
import requests
from bs4 import BeautifulSoup

# ... (get_wevity_contests 함수는 그대로 두세요) ...

def send_telegram(text):
    # 단호한 보안 패치: 코드가 아닌 깃허브 환경변수(Secrets)에서 값을 가져옵니다.
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

# --- (여기서부터 아래 두 줄만 새로 추가하세요!) ---
# 3. 깃허브 웹(Issue)에 올리기 위해 마크다운 파일로 저장
with open("issue_body.md", "w", encoding="utf-8") as f:
    f.write(scraped_data)