import requests
from bs4 import BeautifulSoup
import datetime

def get_allcon_final_mission():
    print("🚀 마스터, 올콘의 모든 링크를 낱낱이 파헤쳐 공모전을 찾아냅니다...")
    
    # 영서햄이 주신 마감임박순 URL
    url = "https://www.all-con.co.kr/list/contest/1/1?sortname=cl_order&sortorder=asc&stx=&sfl=&t=1&ct=&sc=&tg="
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        return f"❌ 접속 실패: {e}"

    now = datetime.datetime.now()
    result_text = f"🏆 **{now.strftime('%Y-%m-%d')} 기준 마감 전 공모전 리포트** 🏆\n"
    result_text += "------------------------------------------\n"
    
    count = 0
    # 💡 핵심: 클래스명에 의존하지 않고, 모든 <a> 태그를 전수조사합니다.
    all_links = soup.find_all('a', href=True)
    
    # 중복 제거를 위한 세트
    seen_links = set()

    for a in all_links:
        href = a['href']
        # 공모전 상세 페이지 주소 패턴을 찾습니다.
        if '/view/contest/' in href:
            link = "https://www.all-con.co.kr" + href if not href.startswith('http') else href
            
            if link not in seen_links:
                title = a.text.strip()
                # 텍스트가 너무 짧거나 숫자로만 된 것(페이지 번호 등)은 거릅니다.
                if len(title) > 5 and not title.isdigit():
                    # 부모 요소나 주변에서 D-Day 정보를 찾아봅니다 (없으면 '진행중')
                    parent_text = a.find_parent().get_text() if a.find_parent() else ""
                    dday = "진행중"
                    if 'D-' in parent_text:
                        import re
                        match = re.search(r'D-\d+|D-Day', parent_text)
                        if match: dday = match.group()
                    
                    # 마감된 항목 제외
                    if "마감" in parent_text or "종료" in parent_text:
                        continue

                    result_text += f"{count+1}. **[{dday}]** {title} [🔗]({link})\n"
                    seen_links.add(link)
                    count += 1
            
            if count >= 30: break # 너무 많으면 자름

    if count == 0:
        result_text += "⚠️ 현재 사이트 구조 분석 중입니다. 잠시 후 다시 시도해 주세요. 🧐\n"
    
    result_text += f"\n------------------------------------------\n"
    result_text += f"💡 총 {count}개의 공모전을 발견했습니다!"
    return result_text

# 파일 저장
with open("issue_body.md", "w", encoding="utf-8") as f:
    f.write(get_allcon_final_mission())

print(f"✅ 수집 시도 완료 ({datetime.datetime.now()})")
