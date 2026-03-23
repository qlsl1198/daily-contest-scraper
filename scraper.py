import requests
from bs4 import BeautifulSoup
import datetime

def get_allcon_perfect_list():
    print("🚀 마스터, 올콘의 모든 리스트 패턴을 정밀 스캔 중입니다...")
    
    # 영서햄이 주신 마감임박순 상세 URL
    url = "https://www.all-con.co.kr/list/contest/1/1?sortname=cl_order&sortorder=asc&stx=&sfl=&t=1&ct=&sc=&tg="
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        return f"❌ 올콘 접속 실패: {e}"

    # 💡 핵심: 올콘은 리스트를 'table'의 'tr'로 관리하거나 'div.list-box'로 관리함
    # 모든 가능성 있는 리스트 요소를 다 가져옵니다.
    items = soup.select('tr') or soup.select('li.list-item') or soup.select('.list-box li')
    
    now = datetime.datetime.now()
    result_text = f"🏆 **{now.strftime('%Y-%m-%d')} 기준 마감 전 공모전 리스트** 🏆\n"
    result_text += "------------------------------------------\n"
    
    count = 0
    for item in items:
        # 제목 태그 찾기 (다양한 클래스 대응)
        title_tag = item.select_one('.title a') or item.select_one('dt.title a') or item.select_one('p.title a')
        # D-Day 태그 찾기
        dday_tag = item.select_one('.d-day') or item.select_one('.day') or item.select_one('span.dday')
        
        if title_tag:
            title = title_tag.text.strip()
            # D-Day가 없으면 텍스트 전체에서 D-로 시작하는 걸 찾음
            dday = dday_tag.text.strip() if dday_tag else "진행중"
            
            # 햄이 보여주신 '접수예정'이나 '마감' 필터링
            if "마감" in dday or "종료" in dday:
                continue
                
            link = title_tag['href']
            if not link.startswith('http'):
                link = "https://www.all-con.co.kr" + link
            
            result_text += f"{count+1}. **[{dday}]** {title} [🔗]({link})\n"
            count += 1
            
            if count >= 50: break # 너무 많으면 자름
                    
    if count == 0:
        # 💡 만약 위 방법으로도 안 잡히면 최후의 수단: 모든 a 태그 중 공모전 링크 형태인 것만 추출
        all_links = soup.find_all('a', href=True)
        for a in all_links:
            if '/view/contest/' in a['href']:
                title = a.text.strip()
                if len(title) > 5: # 제목다운 것만
                    link = "https://www.all-con.co.kr" + a['href'] if not a['href'].startswith('http') else a['href']
                    result_text += f"{count+1}. **[진행중]** {title} [🔗]({link})\n"
                    count += 1
                    if count >= 30: break

    result_text += f"\n------------------------------------------\n"
    result_text += f"💡 총 {count}개의 공모전을 발견했습니다!"
    return result_text

# 파일 저장
with open("issue_body.md", "w", encoding="utf-8") as f:
    f.write(get_allcon_perfect_list())

print(f"✅ 수집 완료! {datetime.datetime.now()}")
