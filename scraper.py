import requests
from bs4 import BeautifulSoup
import datetime

def get_bulletproof_contests():
    print("🚀 마스터, 방화벽 없는 구글의 '공모전' 실시간 데이터를 타격합니다!")
    
    # 💡 깃허브를 절대 차단하지 않는 구글 뉴스 RSS (공모전 키워드, 최근 7일)
    url = "https://news.google.com/rss/search?q=%EA%B3%B5%EB%AA%A8%EC%A0%84+when:7d&hl=ko&gl=KR&ceid=KR:ko"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        # XML 데이터를 파싱합니다
        soup = BeautifulSoup(response.content, 'html.parser')
    except Exception as e:
        return f"❌ 구글 접속 실패 (이럴 확률은 0.1%입니다): {e}"

    # 뉴스 아이템(공모전 정보) 추출
    items = soup.find_all('item')
    
    now = datetime.datetime.now()
    result_text = f"🏆 **{now.strftime('%Y-%m-%d')} 실시간 공모전 레이더** 🏆\n"
    result_text += "*(구글 실시간 수집 데이터 기반)*\n"
    result_text += "------------------------------------------\n"
    
    count = 0
    for item in items:
        title_tag = item.find('title')
        link_tag = item.find('link')
        
        if title_tag and link_tag:
            title = title_tag.text.strip()
            link = link_tag.text.strip()
            
            # 언론사 이름 등 불필요한 뒤쪽 텍스트 잘라내기
            if " - " in title:
                title = title.rsplit(" - ", 1)[0]
                
            # 너무 긴 제목은 깔끔하게
            display_title = (title[:35] + '..') if len(title) > 35 else title
            
            result_text += f"{count+1}. 📌 {display_title} [🔗]({link})\n"
            count += 1
            
            if count >= 15: break # 깔끔하게 15개만!
            
    if count == 0:
        result_text += "오늘은 새로운 공모전 뉴스가 없습니다.\n"
        
    result_text += f"\n------------------------------------------\n"
    result_text += f"💡 총 {count}개의 따끈따끈한 공모전 소식을 가져왔습니다!"
    
    return result_text

# 파일 저장 실행
final_report = get_bulletproof_contests()
with open("issue_body.md", "w", encoding="utf-8") as f:
    f.write(final_report)

print(f"✅ 구글 스크래핑 완벽 종료! 깃허브 게시판을 확인하세요!")
