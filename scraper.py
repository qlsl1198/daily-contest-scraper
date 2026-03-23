import os
from bs4 import BeautifulSoup
import datetime
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def get_dynamic_contests():
    print("🚀 마스터, 현업용 무기 '셀레니움'으로 동적 웹페이지를 렌더링합니다...")
    
    # 💡 1. 가상 브라우저(Headless Chrome) 세팅
    chrome_options = Options()
    chrome_options.add_argument("--headless") # 화면 없이 백그라운드 실행 (서버 필수)
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

    # 💡 2. 크롬 드라이버 자동 설치 및 브라우저 실행
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # 올콘 리스트 페이지 접속
    url = "https://www.all-con.co.kr/list/contest"
    driver.get(url)
    
    # 💡 3. 핵심: 자바스크립트가 화면에 데이터를 다 그릴 때까지 5초 대기!
    print("⏳ 데이터 렌더링 대기 중 (5초)...")
    time.sleep(5) 
    
    # 렌더링이 끝난 최종 완벽한 HTML 소스를 가져옵니다.
    html = driver.page_source
    driver.quit() # 메모리를 위해 브라우저 종료
    
    soup = BeautifulSoup(html, 'html.parser')
    
    now = datetime.datetime.now()
    result_text = f"🏆 **{now.strftime('%Y-%m-%d')} 기준 최신 공모전 리스트 (Selenium)** 🏆\n"
    result_text += "------------------------------------------\n"
    
    count = 0
    seen_links = set()
    
    # 렌더링 된 후의 a 태그 탐색
    for a in soup.find_all('a', href=True):
        if '/view/contest/' in a['href']:
            title = a.get_text(strip=True)
            # 쓰레기 데이터 걸러내기
            if len(title) > 5 and not title.isdigit():
                link = "https://www.all-con.co.kr" + a['href'] if not a['href'].startswith('http') else a['href']
                
                if link not in seen_links:
                    result_text += f"{count+1}. **[진행중]** {title} [🔗]({link})\n"
                    seen_links.add(link)
                    count += 1
                    
            if count >= 20: break # 깔끔하게 20개만
            
    if count == 0:
        result_text += "⚠️ 에러: 사이트 구조가 완전히 변경되었습니다.\n"
        
    result_text += f"\n------------------------------------------\n"
    result_text += f"💡 총 {count}개의 공모전 발견!"
    
    return result_text

# 파일 저장 실행
final_report = get_dynamic_contests()
with open("issue_body.md", "w", encoding="utf-8") as f:
    f.write(final_report)

print(f"✅ 셀레니움 스크래핑 완벽 종료! {datetime.datetime.now()}")
