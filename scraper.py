import datetime
import html as html_module
import os
import re
import xml.etree.ElementTree as ET
from urllib.parse import parse_qs, urljoin, urlparse
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

# 로컬 PC는 보통 맞지만, GitHub Actions는 TZ=UTC라 naive now()가 한국과 어긋남 → KST 고정
_TZ_KST = ZoneInfo("Asia/Seoul")


def _now_kst() -> datetime.datetime:
    return datetime.datetime.now(_TZ_KST)


def _format_collected_at(dt: datetime.datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M") + " (KST)"

WEVITY_BASE = "https://www.wevity.com/"
WEVITY_LIST_URL = "https://www.wevity.com/?c=find&s=1&gub=1"
# 목록은 gp=1,2,3… 페이지로 나뉨. 전부 순회 (기본 최대 50페이지).
WEVITY_MAX_PAGES = max(1, int(os.environ.get("WEVITY_MAX_PAGES", "50")))
# 0이면 개수 제한 없음(페이지 상한까지만). 이슈 본문이 매우 길어질 수 있음.
WEVITY_MAX_ITEMS = int(os.environ.get("WEVITY_MAX_ITEMS", "0"))


def _wevity_list_page_url(gp: int) -> str:
    return f"https://www.wevity.com/?c=find&s=1&gub=1&gp={gp}"
# 목록만 있는 모드(슬라이더/레이아웃이 다른 경우 대비)
WEVITY_LIST_FALLBACK_URL = (
    "https://www.wevity.com/?c=find&s=1&gub=1&gbn=list&mode=ing"
)
GOOGLE_RSS_URL = (
    "https://news.google.com/rss/search?q=%EA%B3%B5%EB%AA%A8%EC%A0%84+when:7d&hl=ko&gl=KR&ceid=KR:ko"
)

# requests 폴백용(일부 환경에서만 사용). 위비티는 WAF/봇 차단이 있어 curl_cffi(크롬 TLS 지문) 우선.
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.wevity.com/",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

# HTML 원문에서 <a href=...gbn=view...ix=...>제목</a> 추출 (BS4가 못 잡을 때 폴백)
WEVITY_ANCHOR_RE = re.compile(
    r'<a[^>]+href\s*=\s*["\']([^"\']*gbn=view[^"\']*ix=(\d+)[^"\']*)["\'][^>]*>([^<]+)</a>',
    re.IGNORECASE,
)

# Jina Reader 마크다운: [![Image N: 제목](썸네일)](상세링크)
JINA_MD_IMAGE_VIEW_RE = re.compile(
    r"Image\s+\d+:\s*([^\]]+)\]\([^)]+\)\]\((https://www\.wevity\.com/\?[^)]+gbn=view[^)]+ix=(\d+)[^)]*)\)",
    re.IGNORECASE,
)
JINA_MD_URL_ONLY_RE = re.compile(
    r"(https://www\.wevity\.com/\?[^)\s\"]+gbn=view[^)\s\"]+ix=(\d+)[^)\s\"]*)",
    re.IGNORECASE,
)


def _short_title(title: str, max_len: int = 35) -> str:
    title = title.strip()
    return (title[:max_len] + "..") if len(title) > max_len else title


def get_google_contests(collected_at: datetime.datetime | None = None) -> str:
    print("🚀 구글 뉴스 RSS에서 공모전 키워드를 수집합니다.")
    at = collected_at if collected_at is not None else _now_kst()

    try:
        response = requests.get(GOOGLE_RSS_URL, timeout=10)
        response.raise_for_status()
        # RSS는 XML이므로 HTML 파서를 쓰면 <link>가 빈 태그로 깨짐 → ElementTree 사용
        root = ET.fromstring(response.content)
    except Exception as e:
        return f"❌ 구글 접속 실패: {e}\n"

    items = root.findall(".//item")
    lines = [
        f"### 📰 구글 뉴스 (최근 7일)",
        f"*(수집 시각: {_format_collected_at(at)})*",
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
    return rows


def _merge_wevity_rows(
    *batches: list[tuple[str, str]],
    max_items: int | None = None,
) -> list[tuple[str, str]]:
    """여러 소스에서 온 (제목, URL)을 ix 기준으로 합침. max_items가 있으면 그만큼만."""
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
            if max_items is not None and len(out) >= max_items:
                return out
    return out


def _collect_wevity_rows_from_jina_markdown(md: str) -> list[tuple[str, str]]:
    """r.jina.ai 가 반환한 마크다운에서 공모전 링크 추출 (GitHub Actions IP 403 우회용)."""
    seen_ix: set[str] = set()
    rows: list[tuple[str, str]] = []
    for m in JINA_MD_IMAGE_VIEW_RE.finditer(md):
        title = re.sub(r"\s+", " ", m.group(1).strip())
        url = m.group(2).strip()
        ix = m.group(3)
        if not ix or ix in seen_ix:
            continue
        seen_ix.add(ix)
        rows.append((title, url))
    if len(rows) < 5:
        for m in JINA_MD_URL_ONLY_RE.finditer(md):
            url = m.group(1).strip()
            ix = m.group(2)
            if not ix or ix in seen_ix:
                continue
            seen_ix.add(ix)
            rows.append((f"위비티 상세 (ix={ix})", url))
    return rows


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
    return rows


def _fetch_wevity_page_with_requests(url: str, session: requests.Session | None = None) -> str:
    """urllib3 기본 TLS. session이 있으면 재사용(쿠키 유지)."""
    own = session is None
    if own:
        session = requests.Session()
        session.headers.update(REQUEST_HEADERS)
        session.get(WEVITY_BASE, timeout=20)
    r = session.get(
        url,
        timeout=25,
        headers={**REQUEST_HEADERS, "Referer": WEVITY_BASE.rstrip("/") + "/"},
    )
    r.raise_for_status()
    if r.encoding is None or r.encoding == "ISO-8859-1":
        r.encoding = r.apparent_encoding or "utf-8"
    return r.text


# Jina Reader는 wevity 목록에서 gp 쿼리를 반영하지 않고 동일 본문을 주는 경우가 많음 → 페이지네이션에 쓰면 안 됨.
WEVITY_CURL_IMPERSONATE = ("chrome120", "chrome110", "chrome107")


def _open_wevity_fetch_state() -> tuple[object | None, requests.Session]:
    """curl_cffi 세션(가능 시) + requests 세션. 목록 gp 루프에서 공유해 쿠키 유지."""
    curl_sess = None
    try:
        from curl_cffi import requests as curl_requests

        curl_sess = curl_requests.Session()
        curl_sess.get(WEVITY_BASE, impersonate="chrome120", timeout=25)
    except ImportError:
        pass
    except Exception as e:
        print(f"(위비티 curl 세션 초기화 실패, requests 위주로 시도: {e})")

    req_sess = requests.Session()
    req_sess.headers.update(REQUEST_HEADERS)
    try:
        req_sess.get(WEVITY_BASE, timeout=20)
    except Exception as e:
        print(f"(위비티 requests 세션 초기화: {e})")

    return curl_sess, req_sess


def _fetch_wevity_direct_with_state(url: str, curl_sess: object | None, req_sess: requests.Session) -> str:
    """
    위비티 직접 요청. datacenter IP에서는 403이 날 수 있음.
    curl_cffi(여러 Chrome TLS 지문) → 실패 시 requests.
    """
    last: Exception | None = None
    if curl_sess is not None:
        for imp in WEVITY_CURL_IMPERSONATE:
            try:
                r = curl_sess.get(
                    url,
                    impersonate=imp,
                    timeout=35,
                    headers={**REQUEST_HEADERS, "Referer": WEVITY_BASE.rstrip("/") + "/"},
                )
                r.raise_for_status()
                return r.text
            except Exception as e:
                last = e
        print(f"(위비티 curl_cffi 전 impersonate 실패: {last})")

    try:
        return _fetch_wevity_page_with_requests(url, session=req_sess)
    except Exception as e:
        if last is not None:
            raise last from e
        raise


def _fetch_wevity_via_jina_reader(target_url: str) -> str:
    """
    Jina AI Reader가 원격에서 페이지를 가져와 텍스트로 돌려줌.
    GitHub Actions IP가 위비티에 403으로 막힐 때 우회에 사용.
    """
    wrapped = "https://r.jina.ai/" + target_url
    r = requests.get(
        wrapped,
        timeout=90,
        headers={
            "User-Agent": REQUEST_HEADERS["User-Agent"],
            "Accept": "text/plain, text/markdown;q=0.9, */*;q=0.8",
        },
    )
    r.raise_for_status()
    return r.text


def _fetch_wevity_direct_or_jina(
    url: str,
    curl_sess: object | None,
    req_sess: requests.Session,
    *,
    allow_jina: bool,
) -> tuple[str, str]:
    """
    (본문, 'html' | 'jina').
    Jina는 wevity 목록에서 gp별로 다른 페이지를 주지 않는 경우가 있어,
    gp>=2일 때는 allow_jina=False로 두고 직접 HTML만 사용한다.
    """
    try:
        return _fetch_wevity_direct_with_state(url, curl_sess, req_sess), "html"
    except Exception as e:
        if not allow_jina:
            raise
        print(f"(직접 실패 → Jina Reader: {url[:72]}… — {e})")
        return _fetch_wevity_via_jina_reader(url), "jina"


def _parse_wevity_fetched_body(body: str, kind: str) -> list[tuple[str, str]]:
    if kind == "html":
        soup = BeautifulSoup(body, "html.parser")
        return _merge_wevity_rows(
            _collect_wevity_rows_from_soup(soup),
            _collect_wevity_rows_from_regex(body),
        )
    return _collect_wevity_rows_from_jina_markdown(body)


def get_wevity_contests(collected_at: datetime.datetime | None = None) -> str:
    print("🚀 위비티(wevity.com) 전체 공모전 목록을 수집합니다.")
    at = collected_at if collected_at is not None else _now_kst()

    seen_ix: set[str] = set()
    rows: list[tuple[str, str]] = []
    direct_err: Exception | None = None
    jina_used = False
    stopped_gp2_no_direct = False

    curl_sess, req_sess = _open_wevity_fetch_state()

    def append_unique(batch: list[tuple[str, str]]) -> tuple[int, bool]:
        """(이번에 새로 넣은 개수, 상한 도달 여부)"""
        added = 0
        for title, url in batch:
            ix = parse_qs(urlparse(url).query).get("ix", [None])[0]
            if not ix or ix in seen_ix:
                continue
            seen_ix.add(ix)
            rows.append((title, url))
            added += 1
            if WEVITY_MAX_ITEMS > 0 and len(rows) >= WEVITY_MAX_ITEMS:
                return added, True
        return added, False

    last_gp = 0
    for gp in range(1, WEVITY_MAX_PAGES + 1):
        if WEVITY_MAX_ITEMS > 0 and len(rows) >= WEVITY_MAX_ITEMS:
            break
        url = _wevity_list_page_url(gp)
        allow_jina = gp == 1
        try:
            body, kind = _fetch_wevity_direct_or_jina(
                url, curl_sess, req_sess, allow_jina=allow_jina
            )
        except Exception as e:
            if gp == 1:
                direct_err = e
                print(f"(gp={gp} 페이지 가져오기 실패: {e})")
            else:
                stopped_gp2_no_direct = True
                print(
                    f"(gp={gp} 직접 접속 실패 — Jina Reader는 목록 페이지마다 다른 gp를 "
                    f"반영하지 않아 사용하지 않음: {e})"
                )
            break
        if kind == "jina":
            jina_used = True
        last_gp = gp
        batch = _parse_wevity_fetched_body(body, kind)
        before = len(rows)
        _, hit_limit = append_unique(batch)
        added = len(rows) - before
        if hit_limit:
            break
        if gp > 1 and added == 0:
            break

    if len(rows) < 3:
        try:
            body, kind = _fetch_wevity_direct_or_jina(
                WEVITY_LIST_FALLBACK_URL,
                curl_sess,
                req_sess,
                allow_jina=True,
            )
            if kind == "jina":
                jina_used = True
            append_unique(_parse_wevity_fetched_body(body, kind))
        except Exception as ex:
            print(f"(접수중 폴백 URL 실패: {ex})")

    if not rows and direct_err is not None:
        return (
            f"❌ 위비티 접속 실패: {direct_err}\n"
            f"(직접·Jina Reader 모두에서 목록을 가져오지 못했습니다.)\n"
        )

    cap_note = ""
    if WEVITY_MAX_ITEMS > 0:
        cap_note = f" · 상한 {WEVITY_MAX_ITEMS}건"
    jina_note = ""
    if jina_used:
        jina_note = " · 1페이지는 Jina Reader 사용(직접 접속 실패 시)"
    if stopped_gp2_no_direct:
        jina_note += " · gp≥2는 직접 HTML만 시도(Jina는 페이지별 목록 미지원)"
    print(
        f"(위비티) gp 1~{last_gp or '?'} 페이지 순회 · "
        f"고유 공모전 {len(rows)}건{cap_note}{jina_note}"
    )

    lines = [
        f"### 🏅 위비티 공모전",
        f"*[전체 공모전]({WEVITY_LIST_URL}) · 수집 시각: {_format_collected_at(at)}*",
        f"*목록 페이지 `gp=1…{WEVITY_MAX_PAGES}` 순회 (실제 수집: ~{last_gp}페이지){cap_note}{jina_note}*",
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
    now = _now_kst()
    header = (
        f"# 🏆 **{now.strftime('%Y-%m-%d')} 공모전 레이더** 🏆\n"
        f"*구글 뉴스 RSS + 위비티 · 기준 시각: {_format_collected_at(now)}*\n"
        f"\n---\n\n"
    )
    body = get_google_contests(now) + "\n---\n\n" + get_wevity_contests(now)
    return header + body


final_report = build_report()
with open("issue_body.md", "w", encoding="utf-8") as f:
    f.write(final_report)

print("✅ 수집 완료! issue_body.md 를 확인하세요.")
