import requests
from bs4 import BeautifulSoup
import datetime

def get_allcon_new_contests():
    print("🚀 위비티 대신, 보안이 유연한 '올콘'에서 신규 정보를 가져옵니다...")
    
    # 올콘 신규 공모전 리스트 페이지
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

    # 올콘 리스트 추출
    contest_list = soup.select('ul.list-box li')
    
    now = datetime.datetime.now()
    result_text = f"🏆 **{now.strftime('%Y-%m-%d')} 신규 공모전 TOP 5** 🏆\n"
    result_text += "*(올콘 실시간 데이터를 기반으로 업데이트됩니다)*\n"
    result_text += "------------------------------------------\n"
    
    count = 0
    for contest in contest_list:
        title_tag = contest.select_one('p.title a')
        dday_tag = contest.select_one('span.d-day')
        
        if title_tag and dday_tag:
            title = title_tag.text.strip()
            dday = dday_tag.text.strip()
            link = title_tag['href']
            if not link.startswith('http'):
                link = "https://www.all-con.co.kr" + link
            
            # 마감된 건 제외하고 딱 5개만!
            if "마감" not in dday:
                result_text += f"{count+1}. **[{dday}]** {title[:28]}.. [🔗]({link})\n"
                count += 1
            
            if count >= 5: break
                    
    result_text += f"\n💡 총 {count}개의 신규 공모전 발견!"
    return result_text

# 파일 저장 실행
with open("issue_body.md", "w", encoding="utf-8") as f:
    f.write(get_allcon_new_contests())
