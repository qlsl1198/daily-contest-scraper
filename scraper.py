import datetime
import html as html_module
import re
import xml.etree.ElementTree as ET
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

WEVITY_BASE = "https://www.wevity.com/"
WEVITY_LIST_URL = "https://www.wevity.com/?c=find&s=1&gub=1"
# 목록만 있는 모드(슬라이더/레이아웃이 다른 경우 대비)
WEVITY_LIST_FALLBACK_URL = (
    "https://www.wevity.com/?c=find&s=1&gub=1&gbn=list&mode=ing"
)
GOOGLE_RSS_URL = (
    "https://news.google.com/rss/search?q=%EA%B3%B5%EB%AA%A8%EC%A0%84+when:7d&hl=ko&gl=KR&ceid=KR:ko"
)

# GitHub Actions 등에서 'compatible' UA는 빈 페이지/차단에 걸리는 경우가 있어 일반 브라우저 UA 사용
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://www.wevity.com/",
}

# HTML 원문에서 <a href=...gbn=view...ix=...>제목</a> 추출 (BS4가 못 잡을 때 폴백)
WEVITY_ANCHOR_RE = re.compile(
    r'<a[^>]+href\s*=\s*["\']([^"\']*gbn=view[^"\']*ix=(\d+)[^"\']*)["\'][^>]*>([^<]+)</a>',
    re.IGNORECASE,
)


def _short_title(title: str, max_len: int = 35) -> str:
    title = title.strip()
    return (title[:max_len] + "..") if len(title) > max_len else title


def get_google_contests() -> str:
    print("🚀 구글 뉴스 RSS에서 공모전 키워드를 수집합니다.")

    try:
        response = requests.get(GOOGLE_RSS_URL, timeout=10)
        response.raise_for_status()
        # RSS는 XML이므로 HTML 파서를 쓰면 <link>가 빈 태그로 깨짐 → ElementTree 사용
        root = ET.fromstring(response.content)
    except Exception as e:
        return f"❌ 구글 접속 실패: {e}\n"

    items = root.findall(".//item")
    now = datetime.datetime.now()
    lines = [
        f"### 📰 구글 뉴스 (최근 7일)",
        f"*(수집 시각: {now.strftime('%Y-%m-%d %H:%M')})*",
        "",
    ]

    count = 0
    for item in items:
        title_el = item.find("title")
        link_el = item.find("link")
        if title_el is None or link_el is None:
            continue
        title = (title_el.text or "").strip()
        link = (link_el.text or "").strip()
        if not title or not link:
            continue
        if " - " in title:
            title = title.rsplit(" - ", 1)[0]
        lines.append(f"{count + 1}. 📌 {_short_title(title)} [🔗]({link})")
        count += 1
        if count >= 15:
            break

    if count == 0:
        lines.append("해당 기간 새 뉴스가 없습니다.")
    lines.append("")
    lines.append(f"💡 구글: 총 **{count}**건")
    lines.append("")
    return "\n".join(lines)


def _collect_wevity_rows_from_soup(soup: BeautifulSoup) -> list[tuple[str, str]]:
    seen_ix: set[str] = set()
    rows: list[tuple[str, str]] = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if "gbn=view" not in href or "ix=" not in href:
            continue
        title = a.get_text(strip=True)
        if not title:
            continue
        full_url = urljoin(WEVITY_BASE, href)
        parsed = urlparse(full_url)
        ix = parse_qs(parsed.query).get("ix", [None])[0]
        if not ix or ix in seen_ix:
            continue
        seen_ix.add(ix)
        rows.append((title, full_url))
        if len(rows) >= 15:
            break
    return rows


def _merge_wevity_rows(*batches: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """여러 소스에서 온 (제목, URL)을 ix 기준으로 합치고 최대 15개까지."""
    seen_ix: set[str] = set()
    out: list[tuple[str, str]] = []
    for batch in batches:
        for title, url in batch:
            parsed = urlparse(url)
            ix = parse_qs(parsed.query).get("ix", [None])[0]
            if not ix or ix in seen_ix:
                continue
            seen_ix.add(ix)
            out.append((title, url))
            if len(out) >= 15:
                return out
    return out


def _collect_wevity_rows_from_regex(page_html: str) -> list[tuple[str, str]]:
    seen_ix: set[str] = set()
    rows: list[tuple[str, str]] = []
    for m in WEVITY_ANCHOR_RE.finditer(page_html):
        raw_href = html_module.unescape(m.group(1).strip())
        ix = m.group(2)
        title = html_module.unescape(m.group(3)).strip()
        title = re.sub(r"\s+", " ", title)
        if not ix or ix in seen_ix:
            continue
        if "gbn=view" not in raw_href or "ix=" not in raw_href:
            continue
        full_url = urljoin(WEVITY_BASE, raw_href)
        if not title:
            title = f"위비티 상세 (ix={ix})"
        seen_ix.add(ix)
        rows.append((title, full_url))
        if len(rows) >= 15:
            break
    return rows


def _fetch_wevity_page(url: str) -> str:
    session = requests.Session()
    session.headers.update(REQUEST_HEADERS)
    r = session.get(url, timeout=20)
    r.raise_for_status()
    if r.encoding is None or r.encoding == "ISO-8859-1":
        r.encoding = r.apparent_encoding or "utf-8"
    return r.text


def get_wevity_contests() -> str:
    print("🚀 위비티(wevity.com) 전체 공모전 목록을 수집합니다.")

    page_html = ""
    try:
        page_html = _fetch_wevity_page(WEVITY_LIST_URL)
    except Exception as e:
        return f"❌ 위비티 접속 실패: {e}\n"

    soup = BeautifulSoup(page_html, "html.parser")
    soup_rows = _collect_wevity_rows_from_soup(soup)
    regex_rows = _collect_wevity_rows_from_regex(page_html)
    rows = _merge_wevity_rows(soup_rows, regex_rows)

    if len(rows) < 3:
        try:
            alt_html = _fetch_wevity_page(WEVITY_LIST_FALLBACK_URL)
            alt_soup = BeautifulSoup(alt_html, "html.parser")
            alt_soup_rows = _collect_wevity_rows_from_soup(alt_soup)
            alt_regex_rows = _collect_wevity_rows_from_regex(alt_html)
            rows = _merge_wevity_rows(rows, alt_soup_rows, alt_regex_rows)
        except Exception as e:
            print(f"(폴백 URL 재시도 실패: {e})")

    print(
        f"(위비티) HTML 길이={len(page_html)} · 파싱된 항목 수={len(rows)} "
        f"(원문에 gbn=view 문자열: {'gbn=view' in page_html})"
    )

    now = datetime.datetime.now()
    lines = [
        f"### 🏅 위비티 공모전",
        f"*[전체 공모전]({WEVITY_LIST_URL}) · 수집 시각: {now.strftime('%Y-%m-%d %H:%M')}*",
        "",
    ]

    if not rows:
        lines.append("목록을 가져오지 못했습니다. (페이지 구조 변경 가능)")
    else:
        for i, (title, link) in enumerate(rows, start=1):
            lines.append(f"{i}. 📌 {_short_title(title)} [🔗]({link})")
        lines.append("")
        lines.append(f"💡 위비티: 총 **{len(rows)}**건")

    lines.append("")
    return "\n".join(lines)


def build_report() -> str:
    now = datetime.datetime.now()
    header = (
        f"# 🏆 **{now.strftime('%Y-%m-%d')} 공모전 레이더** 🏆\n"
        f"*구글 뉴스 RSS + 위비티*\n"
        f"\n---\n\n"
    )
    body = get_google_contests() + "\n---\n\n" + get_wevity_contests()
    return header + body


final_report = build_report()
with open("issue_body.md", "w", encoding="utf-8") as f:
    f.write(final_report)

print("✅ 수집 완료! issue_body.md 를 확인하세요.")
