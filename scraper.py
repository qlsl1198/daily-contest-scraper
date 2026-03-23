import requests
from bs4 import BeautifulSoup
import datetime
import re

def get_allcon_absolute_final():
    print("🚀 마스터, 올콘의 모든 텍스트를 쥐어짜서 공모전을 찾아냅니다...")
    
    url = "https://www.all-con.co.kr/list/contest/1/1?sortname=cl_order&sortorder=asc&stx=&sfl=&t=1&ct=&sc=&tg="
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://www.google.com/'
    }

    try:
        # 세션을 유지하며 접속
        session = requests.Session()
        response = session.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        
        # 인코딩 강제 설정 (한글 깨짐 방지)
        response.encoding = 'utf-8' 
        soup = BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        return f"❌ 접속 실패: {e}"

    now = datetime.datetime.now()
    result_text = f"🏆 **{now.strftime('%Y-%m-%d')} 공모전 리스트 (올콘)** 🏆\n"
    result_text += "------------------------------------------\n"
    
    # 💡 전략: 모든 <a> 태그 중에서 '/view/contest/'가 들어간 걸 찾되, 
    # 이번엔 부모 요소를 싹 다 뒤져서 'D-' 글자를 무조건 찾아냅니다.
    count = 0
    seen_links = set()

    # 모든 리스트 아이템 후보군 (li, tr, div 등)
    candidates = soup.find_all(['li', 'tr', 'div'], class_=re.compile(r'item|list|con|box'))

    for item in candidates:
        a_tag = item.find('a', href=True)
        if a_tag and '/view/contest/' in a_tag['href']:
            link = "https://www.all-con.co.kr" + a_tag['href'] if not a_tag['href'].startswith('http') else a_tag['href']
            
            if link not in seen_links:
                title = a_tag.get_text(strip=True)
                
                # 제목이 너무 짧으면 무시
                if len(title) < 5: continue
                
                full_text = item.get_text(separator=' ', strip=True)
                
                # 마감된 건 과감히 버림
                if "마감" in full_text or "종료" in full_text: continue
                
                # D-Day 추출
                dday_match = re.search(r'D-\d+|D-Day|오늘마감|진행중', full_text)
                dday = dday_match.group() if dday_match else "확인필요"
                
                result_text += f"{count+1}. **[{dday}]** {title} [🔗]({link})\n"
                seen_links.add(link)
                count += 1
            
            if count >= 30: break

    # 💡 만약 위 방법도 실패하면? 진짜 마지막 수단: 텍스트 무관하게 모든 공모전 링크 다 긁기
    if count == 0:
        for a in soup.find_all('a', href=True):
            if '/view/contest/' in a['href']:
                title = a.get_text(strip=True)
                if len(title) > 5:
                    link = "https://www.all-con.co.kr" + a['href'] if not a['href'].startswith('http') else a['href']
                    if link not in seen_links:
                        result_text += f"{count+1}. **[진행중]** {title} [🔗]({link})\n"
                        seen_links.add(link)
                        count += 1
                if count >= 20: break

    result_text += f"\n------------------------------------------\n"
    result_text += f"💡 총 {count}개의 공모전 발견!"
    return result_text

# 파일 저장
with open("issue_body.md", "w", encoding="utf-8") as f:
    f.write(get_allcon_absolute_final())
