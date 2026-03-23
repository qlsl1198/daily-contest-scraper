import requests
from bs4 import BeautifulSoup
import datetime

def get_allcon_full_list():
    print("🚀 마스터, 올콘에서 기간 남은 모든 공모전을 수집 중입니다...")
    
    # 💡 영서햄이 주신 상세 리스트 주소 (마감임박순)
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

    # 💡 올콘의 실제 리스트 구조 분석 결과: .list-item 또는 table 내의 tr 구조일 수 있음
    # 가장 확실한 리스트 영역을 타겟팅합니다.
    contest_items = soup.select('div.list-type2 ul li') or soup.select('div.contest-list ul li') or soup.select('.list-box li')
    
    now = datetime.datetime.now()
    result_text = f"🏆 **{now.strftime('%Y-%m-%d')} 기준 마감 전 공모전 전체 리스트** 🏆\n"
    result_text += "*(현재 사이트에서 확인 가능한 모든 항목을 가져옵니다)*\n"
    result_text += "------------------------------------------\n"
    
    count = 0
    for item in contest_items:
        # 제목과 링크 찾기
        title_tag = item.select_one('p.title a') or item.select_one('dt.title a')
        # D-Day 정보 찾기
        dday_tag = item.select_one('span.d-day') or item.select_one('.dday')
        
        if title_tag:
            title = title_tag.text.strip()
            link = title_tag['href']
            if not link.startswith('http'):
                link = "https://www.all-con.co.kr" + link
            
            # D-Day 텍스트 추출 (없으면 '진행중'으로 표시)
            dday_text = dday_tag.text.strip() if dday_tag else "진행중"
            
            # '마감'이나 '종료'가 포함된 항목은 제외
            if "마감" in dday_text or "종료" in dday_text:
                continue
                
            result_text += f"{count+1}. **[{dday_text}]** {title} [🔗]({link})\n"
            count += 1
            
            # 너무 많으면 깃허브 Issue 본문 제한에 걸릴 수 있으니 상위 50개까지만!
            if count >= 50: break
                    
    if count == 0:
        result_text += "⚠️ 현재 조건에 맞는 공모전을 찾지 못했습니다. 사이트 구조를 재점검해야 합니다.\n"
    
    result_text += f"\n------------------------------------------\n"
    result_text += f"💡 총 {count}개의 공모전을 발견했습니다!"
    return result_text

# 1. 실행 및 파일 저장
final_report = get_allcon_full_list()
with open("issue_body.md", "w", encoding="utf-8") as f:
    f.write(final_report)

print(f"✅ 수집 완료 ({datetime.datetime.now()}) - 이제 깃허브가 글을 올릴 겁니다.")
