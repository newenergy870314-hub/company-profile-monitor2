#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
산업통상부 조직도 + 주요인사 프로필 포털
CLEAN V1

원칙
- 산업통상부 공식 홈페이지를 1순위 원본으로 확인
- 홈페이지 수집 실패 시에도 fallback 데이터로 반드시 index.html 생성
- 조직도에서 인물 클릭 → 프로필 Modal
- root/index.html 직접 생성
- 별도 JS 파일/DB 없이 단일 정적 HTML 생성
"""

from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

KST = timezone(timedelta(hours=9))
NOW = datetime.now(KST)
TODAY = NOW.strftime("%Y.%m.%d")
BASE_DIR = Path(__file__).resolve().parent

OFFICIAL_HOME = "https://www.motir.go.kr/"
ORG_URL = "https://www.motir.go.kr/kor/26/headquarters"
MINISTER_URL = "https://www.motir.go.kr/kor/contents/70"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/155.0 Safari/537.36"
    )
}
TIMEOUT = 20


# ------------------------------------------------------------
# 1. 네가 원하는 화면에 필요한 핵심 조직 구조
#    공식 산업통상부 조직안내 기준으로 관리
# ------------------------------------------------------------
ORG = [
    {"id":"minister","parent":"","name":"장관","leader":"김정관","person":"kim","hot":True},

    {"id":"advisor","parent":"minister","name":"장관정책보좌관","leader":"","person":"","hot":False},
    {"id":"spokesperson","parent":"minister","name":"대변인","leader":"","person":"","hot":False},
    {"id":"audit","parent":"minister","name":"감사관","leader":"","person":"","hot":False},

    {"id":"vice","parent":"minister","name":"1차관","leader":"문신학","person":"moon","hot":True},
    {"id":"planning","parent":"vice","name":"기획조정실","leader":"","person":"","hot":False},
    {"id":"industry","parent":"vice","name":"산업정책실","leader":"","person":"","hot":False},
    {"id":"growth","parent":"vice","name":"산업성장실","leader":"","person":"","hot":False},
    {"id":"security","parent":"vice","name":"산업자원안보실","leader":"양기욱","person":"yang","hot":True},

    {"id":"trade","parent":"minister","name":"통상교섭본부장","leader":"여한구","person":"yeo","hot":True},
    {"id":"trade_policy","parent":"trade","name":"통상정책국","leader":"","person":"","hot":False},
    {"id":"trade_coop","parent":"trade","name":"통상협력국","leader":"","person":"","hot":False},
    {"id":"trade_neg","parent":"trade","name":"통상교섭실","leader":"","person":"","hot":False},

    {"id":"investment","parent":"trade","name":"무역투자실","leader":"강감찬","person":"kang","hot":True},
    {"id":"nuclear","parent":"investment","name":"원전전략기획관","leader":"김창희","person":"kimc","hot":True},
    {"id":"nuclear_export","parent":"nuclear","name":"원전수출진흥과","leader":"","person":"","hot":True},
    {"id":"nuclear_coop","parent":"nuclear","name":"원전수출협력과","leader":"","person":"","hot":True},
]


# ------------------------------------------------------------
# 2. 프로필 fallback
#    공식 홈페이지/사용자 기준자료를 바탕으로 관리
# ------------------------------------------------------------
PEOPLE = {
    "kim": {
        "name":"김정관",
        "title":"산업통상부 장관",
        "name_en":"Kim, Jung-kwan",
        "birth":"1968년생",
        "image_url":"",
        "profile_url":MINISTER_URL,
        "education":[
            "광주제일고등학교 졸업",
            "서울대학교 경제학과 학사",
            "미국 미주리대학교 경제학 박사",
        ],
        "career":[
            "산업통상부 장관",
            "두산에너빌리티 사장",
            "두산에너빌리티 부사장·마케팅부문장(CMO)",
            "두산경영연구원 대표이사",
            "제36회 행정고시",
        ],
        "remarks":[
            "산업·에너지 정책 및 원전 역할 관련 주요 발언",
            "원전 수출 경쟁력 및 해외시장 관련 주요 발언",
        ],
    },
    "moon": {
        "name":"문신학",
        "title":"산업통상부 1차관",
        "name_en":"Moon, Shin-hak",
        "birth":"1967년생",
        "image_url":"",
        "profile_url":"",
        "education":[
            "조선대학교부속고등학교 졸업",
            "서울대학교 경제학과 학사",
        ],
        "career":[
            "산업통상부 1차관",
            "산업통상자원부 대변인",
            "산업통상자원부 장관정책보좌관",
            "산업통상자원부 원전산업정책관",
            "제38회 행정고시",
        ],
        "remarks":[
            "산업정책 및 에너지정책 관련 주요 활동",
        ],
    },
    "yeo": {
        "name":"여한구",
        "title":"통상교섭본부장",
        "name_en":"Yeo, Han-koo",
        "birth":"1969년생",
        "image_url":"",
        "profile_url":"",
        "education":[
            "서울대학교 경영학과 학사",
            "서울대학교 행정대학원 행정학 석사",
            "미국 하버드대학교 케네디스쿨 행정학 석사",
            "미국 하버드대학교 경영대학원 경영학 석사",
        ],
        "career":[
            "산업통상부 통상교섭본부장",
            "미국 피터슨국제경제연구소 선임연구위원",
            "서울대학교 경영대학 초빙교수",
            "산업통상자원부 통상교섭본부장",
        ],
        "remarks":[
            "글로벌 통상환경 및 대외 협력 관련 주요 활동",
        ],
    },
    "yang": {
        "name":"양기욱",
        "title":"산업자원안보실장",
        "name_en":"Yang Ki-Uk",
        "birth":"1972년생",
        "image_url":"",
        "profile_url":"",
        "education":[
            "서울대학교 경제학과 학사",
            "미국 델라웨어대학교 에너지·환경정책학 석사",
        ],
        "career":[
            "산업통상부 산업자원안보실장",
            "산업통상자원부 원전전략기획관",
            "산업통상자원부 FTA정책관",
            "국무조정실 산업·과학·중기정책관",
        ],
        "remarks":[
            "에너지·산업 안보 및 원전 생태계 관련 주요 활동",
        ],
    },
    "kang": {
        "name":"강감찬",
        "title":"무역투자실장",
        "name_en":"Kang, Gam-Chan",
        "birth":"1973년생",
        "image_url":"",
        "profile_url":"",
        "education":[
            "서울대학교 경제학과 졸업",
            "미국 카네기멜론대학교 정보학 석사",
        ],
        "career":[
            "산업통상부 무역투자실장",
            "산업통상자원부 산업정책관",
            "산업통상자원부 무역안보정책관",
            "산업통상자원부 전략산업정책과장",
        ],
        "remarks":[
            "무역·투자 및 원전·SMR 수출 관련 주요 활동",
        ],
    },
    "kimc": {
        "name":"김창희",
        "title":"원전전략기획관",
        "name_en":"Kim Chang-hee",
        "birth":"1971년생",
        "image_url":"",
        "profile_url":"",
        "education":[
            "고려대학교 경영학과 학사",
        ],
        "career":[
            "산업통상부 원전전략기획관",
            "KOTRA 외국인투자지원센터 국장",
            "산업통상자원부 소재부품장비총괄과장",
            "산업통상자원부 기술안보과장",
        ],
        "remarks":[
            "원전 산업 및 원전 수출 관련 주요 업무",
        ],
    },
}


def clean(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def esc(s) -> str:
    return html.escape(str(s or ""))


def fetch(url: str) -> BeautifulSoup:
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")


def find_nearby_image(soup: BeautifulSoup, keyword: str, base_url: str) -> str:
    node = soup.find(string=re.compile(re.escape(keyword)))
    cur = node.parent if node else None
    for _ in range(7):
        if not cur:
            break
        img = cur.find("img")
        if img:
            src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
            if src:
                return urljoin(base_url, src)
        cur = cur.parent
    return ""


def verify_official_pages() -> dict:
    """
    수집은 '확인 + 일부 보강' 용도.
    사이트 구조가 바뀌어도 화면 생성 자체는 실패하지 않음.
    """
    result = {
        "org_ok": False,
        "minister_ok": False,
        "org_error": "",
        "minister_error": "",
    }

    try:
        soup = fetch(ORG_URL)
        text = clean(soup.get_text(" ", strip=True))
        # 핵심 조직명이 실제 공식 페이지에 있는지 확인
        essential = ["산업자원안보실", "통상교섭본부", "무역투자실", "원전전략기획관"]
        result["org_ok"] = sum(1 for x in essential if x in text) >= 2
    except Exception as e:
        result["org_error"] = str(e)

    try:
        soup = fetch(MINISTER_URL)
        text = clean(soup.get_text(" ", strip=True))
        result["minister_ok"] = "김정관" in text
        if result["minister_ok"]:
            img = find_nearby_image(soup, "김정관", MINISTER_URL)
            if img:
                PEOPLE["kim"]["image_url"] = img
    except Exception as e:
        result["minister_error"] = str(e)

    return result


def build_org(parent: str = "") -> str:
    children = [x for x in ORG if x["parent"] == parent]
    if not children:
        return ""

    out = ['<div class="org-level">']
    for n in children:
        clickable = bool(n["person"] and n["person"] in PEOPLE)
        classes = ["org-node"]
        if n["hot"]:
            classes.append("hot")
        if clickable:
            classes.append("clickable")

        attrs = ""
        if clickable:
            attrs = f' data-person="{esc(n["person"])}"'

        out.append(
            f'<div class="org-branch">'
            f'<button type="button" class="{" ".join(classes)}"{attrs}>'
            f'<div class="org-title">{esc(n["name"])}</div>'
            f'<div class="org-person">{esc(n["leader"])}</div>'
            f'{"<div class=click-hint>프로필 보기</div>" if clickable else ""}'
            f'</button>'
            f'{build_org(n["id"])}'
            f'</div>'
        )
    out.append("</div>")
    return "".join(out)


def build_html(status: dict) -> str:
    people_json = json.dumps(PEOPLE, ensure_ascii=False).replace("</", "<\\/")

    official_state = (
        "공식 홈페이지 확인 완료"
        if status["org_ok"]
        else "공식 홈페이지 확인 실패 · fallback 사용"
    )
    minister_state = (
        "장관 프로필 확인 완료"
        if status["minister_ok"]
        else "장관 프로필 fallback 사용"
    )

    org_html = build_org("")

    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>산업통상부 조직도 및 주요인사 프로필</title>
<style>
*{{box-sizing:border-box}}
html,body{{margin:0;padding:0}}
body{{font-family:"Malgun Gothic","Apple SD Gothic Neo",Arial,sans-serif;background:#eef2f6;color:#17202a}}

.topbar{{
  height:58px;background:#0b2c53;color:#fff;
  display:flex;align-items:center;justify-content:space-between;
  padding:0 20px;position:sticky;top:0;z-index:50
}}
.topbar b{{font-size:18px}}
.topbar span{{font-size:11px;color:#cfdeee}}

.wrap{{max-width:1180px;margin:20px auto;padding:0 14px}}

.hero{{
  display:flex;justify-content:space-between;align-items:flex-end;
  margin-bottom:14px
}}
.hero h1{{margin:4px 0;font-size:30px}}
.eyebrow{{font-size:12px;color:#687786;font-weight:800}}
.en{{font-size:13px;color:#73808d}}
.badges{{display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end}}
.badge{{font-size:11px;padding:6px 9px;border-radius:999px;background:#dceaf8;color:#174d82;font-weight:800}}

.paper{{
  background:#fff;border-radius:12px;padding:22px;
  box-shadow:0 2px 16px rgba(0,0,0,.07)
}}
.paper-head{{
  display:flex;justify-content:space-between;align-items:center;
  border-bottom:2px solid #8d969f;padding-bottom:9px;margin-bottom:14px
}}
.paper-title{{font-size:22px;font-weight:900}}
.date{{font-size:12px;color:#56616c}}

.guide{{
  background:#f3f7fa;border-left:4px solid #1b578d;
  padding:10px 12px;font-size:12px;margin-bottom:15px
}}
.guide b{{color:#174d82}}

.org-scroll{{overflow:auto;padding:6px 0 18px}}
.org-canvas{{min-width:1050px}}
.org-level{{
  display:flex;justify-content:center;align-items:flex-start;
  gap:16px;margin:14px 0
}}
.org-branch{{
  display:flex;flex-direction:column;align-items:center;min-width:135px
}}
.org-branch > .org-level{{
  border-top:2px solid #c9d1d9;padding-top:13px;position:relative
}}
.org-node{{
  width:150px;min-height:62px;border:1px solid #c7d0d8;
  border-radius:8px;background:#f7f8fa;padding:10px 8px;text-align:center;
  color:#17202a
}}
.org-node.hot{{background:#fff4b0;border:2px solid #e3b82c}}
.org-node.clickable{{
  cursor:pointer;touch-action:manipulation;
  -webkit-tap-highlight-color:rgba(23,77,130,.15)
}}
.org-node.clickable:hover{{background:#eaf4fd;border-color:#6fa3d1}}
.org-node.clickable:active{{transform:scale(.97);background:#dceeff}}
.org-title{{font-size:12px;font-weight:800}}
.org-person{{font-size:15px;font-weight:900;color:#174d82;margin-top:4px}}
.click-hint{{font-size:9px;color:#7a8793;margin-top:4px}}

.legend{{
  display:flex;gap:12px;align-items:center;flex-wrap:wrap;
  font-size:11px;color:#65717d;margin-top:4px
}}
.legend span{{display:inline-flex;align-items:center;gap:5px}}
.dot{{width:12px;height:12px;border-radius:3px;background:#fff4b0;border:1px solid #e3b82c}}

.source{{
  margin-top:17px;border-top:1px solid #e1e5e9;padding-top:12px;
  font-size:11px;color:#6c7782;line-height:1.7;word-break:break-all
}}

/* modal */
.modal-bg{{
  position:fixed;inset:0;background:rgba(8,23,40,.65);
  z-index:200;display:none;align-items:center;justify-content:center;padding:18px
}}
.modal-bg.open{{display:flex}}
.modal{{
  width:min(900px,96vw);max-height:92vh;background:#fff;
  border-radius:14px;overflow:auto;box-shadow:0 18px 70px rgba(0,0,0,.35)
}}
.modal-head{{
  position:sticky;top:0;z-index:2;background:#fff;border-bottom:1px solid #d8dde3;
  padding:14px 18px;display:flex;align-items:center;justify-content:space-between
}}
.modal-head strong{{font-size:19px}}
.close{{
  width:38px;height:38px;border:0;border-radius:50%;
  background:#eef2f6;font-size:23px;cursor:pointer
}}
.profile{{padding:18px}}
.profile-title{{font-size:28px;font-weight:900;margin:0 0 15px}}
.profile-title span{{font-size:18px;margin-left:8px}}
.identity{{display:grid;grid-template-columns:1fr 185px;gap:14px}}
.idtable{{display:grid;grid-template-columns:100px 1fr;border-top:1px solid #d2d7dc;border-left:1px solid #d2d7dc}}
.idtable>div{{border-right:1px solid #d2d7dc;border-bottom:1px solid #d2d7dc;padding:14px}}
.label{{background:#f5f5f5;font-weight:900;text-align:center}}
.photo{{
  width:185px;height:215px;object-fit:cover;border:1px solid #d2d7dc;
  background:#f3f5f7;display:flex;align-items:center;justify-content:center;
  color:#87919b;font-weight:800
}}
.row{{display:grid;grid-template-columns:100px 1fr;border-left:1px solid #d2d7dc;border-right:1px solid #d2d7dc;border-bottom:1px solid #d2d7dc}}
.row-label{{background:#f5f5f5;border-right:1px solid #d2d7dc;padding:12px;display:flex;align-items:center;justify-content:center;text-align:center;font-weight:900}}
.row-body{{padding:15px 18px;line-height:1.65}}
.row-body ul{{margin:0;padding-left:20px}}
.profile-note{{font-size:11px;color:#6b7680;margin-top:12px}}

@media(max-width:700px){{
  .topbar{{padding:0 12px}}
  .topbar b{{font-size:14px}}
  .wrap{{margin:10px auto;padding:0 8px}}
  .hero{{align-items:flex-start;flex-direction:column;gap:8px}}
  .hero h1{{font-size:24px}}
  .badges{{justify-content:flex-start}}
  .paper{{padding:14px;border-radius:8px}}
  .identity{{grid-template-columns:1fr 110px}}
  .photo{{width:110px;height:140px}}
  .idtable{{grid-template-columns:74px 1fr}}
  .row{{grid-template-columns:74px 1fr}}
  .profile-title{{font-size:22px}}
  .profile-title span{{display:block;margin:4px 0 0;font-size:15px}}
}}
</style>
</head>
<body>

<div class="topbar">
  <b>산업통상부 조직도 및 주요인사 프로필</b>
  <span>CLEAN V1 · {TODAY}</span>
</div>

<div class="wrap">
  <div class="hero">
    <div>
      <div class="eyebrow">정부기관 · 대한민국</div>
      <h1>산업통상부</h1>
      <div class="en">Ministry of Trade, Industry and Resources</div>
    </div>
    <div class="badges">
      <span class="badge">{esc(official_state)}</span>
      <span class="badge">{esc(minister_state)}</span>
    </div>
  </div>

  <section class="paper">
    <div class="paper-head">
      <div class="paper-title">산업통상부 조직도</div>
      <div class="date">기준 {TODAY}</div>
    </div>

    <div class="guide">
      노란색 주요 조직 중 <b>인물 이름이 표시된 직위</b>를 클릭하면
      페이지 이동이나 스크롤 없이 프로필이 바로 열립니다.
    </div>

    <div class="org-scroll">
      <div class="org-canvas">
        {org_html}
      </div>
    </div>

    <div class="legend">
      <span><i class="dot"></i> 주요 조직</span>
      <span>인물명 클릭 → 상세 프로필</span>
    </div>

    <div class="source">
      <div><b>공식 홈페이지</b> {esc(OFFICIAL_HOME)}</div>
      <div><b>조직안내</b> {esc(ORG_URL)}</div>
      <div><b>장관 소개</b> {esc(MINISTER_URL)}</div>
      <div><b>업데이트</b> {esc(NOW.isoformat(timespec="seconds"))}</div>
    </div>
  </section>
</div>

<div class="modal-bg" id="modalBg">
  <div class="modal" role="dialog" aria-modal="true">
    <div class="modal-head">
      <strong id="modalHead">주요인사 프로필</strong>
      <button type="button" class="close" id="closeBtn" aria-label="닫기">×</button>
    </div>
    <div class="profile" id="profileBody"></div>
  </div>
</div>

<script>
const PEOPLE = {people_json};

const modalBg = document.getElementById('modalBg');
const modalHead = document.getElementById('modalHead');
const profileBody = document.getElementById('profileBody');
const closeBtn = document.getElementById('closeBtn');

function eh(s) {{
  return String(s || '').replace(/[&<>"']/g, c => ({{
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'
  }}[c]));
}}

function listHtml(arr) {{
  if (!arr || !arr.length) {{
    return '<div style="color:#89939c">확인된 정보 없음</div>';
  }}
  return '<ul>' + arr.map(x => '<li>' + eh(x) + '</li>').join('') + '</ul>';
}}

function openProfile(id) {{
  const p = PEOPLE[id];
  if (!p) {{
    alert('프로필 정보를 찾지 못했습니다.');
    return;
  }}

  modalHead.textContent = p.name + ' ' + p.title;

  let photo = '<div class="photo">PHOTO</div>';
  if (p.image_url) {{
    photo = `<img class="photo" src="${{eh(p.image_url)}}" alt="${{eh(p.name)}}">`;
  }}

  const officialLink = p.profile_url
    ? `<a href="${{eh(p.profile_url)}}" target="_blank" rel="noopener">공식 프로필 보기</a>`
    : '공식 홈페이지/기준자료';

  profileBody.innerHTML = `
    <div class="profile-title">${{eh(p.name)}} <span>${{eh(p.title)}}</span></div>

    <div class="identity">
      <div class="idtable">
        <div class="label">성명</div>
        <div>${{eh(p.name)}} ${{p.name_en ? '(' + eh(p.name_en) + ')' : ''}} ${{p.birth ? '· ' + eh(p.birth) : ''}}</div>

        <div class="label">직책</div>
        <div>${{eh(p.title)}}</div>

        <div class="label">출처</div>
        <div>${{officialLink}}</div>
      </div>
      ${{photo}}
    </div>

    <div class="row">
      <div class="row-label">학력</div>
      <div class="row-body">${{listHtml(p.education)}}</div>
    </div>

    <div class="row">
      <div class="row-label">경력</div>
      <div class="row-body">${{listHtml(p.career)}}</div>
    </div>

    <div class="row">
      <div class="row-label">주요발언<br>·최근활동</div>
      <div class="row-body">${{listHtml(p.remarks)}}</div>
    </div>

    <div class="profile-note">
      ※ 공식 홈페이지를 우선으로 확인하며, 미공개 항목은 기준자료를 사용합니다.
    </div>
  `;

  modalBg.classList.add('open');
  document.body.style.overflow = 'hidden';
}}

function closeProfile() {{
  modalBg.classList.remove('open');
  document.body.style.overflow = '';
}}

/* 이벤트 위임: 새로 생성된 조직도에서도 클릭이 안정적으로 작동 */
document.addEventListener('click', function(e) {{
  const btn = e.target.closest('.org-node.clickable[data-person]');
  if (btn) {{
    e.preventDefault();
    e.stopPropagation();
    openProfile(btn.dataset.person);
    return;
  }}

  if (e.target === modalBg || e.target === closeBtn) {{
    closeProfile();
  }}
}}, {{passive:false}});

document.addEventListener('keydown', function(e) {{
  if (e.key === 'Escape') closeProfile();
}});

console.log('[MOTIR Portal] CLEAN V1 loaded');
</script>

</body>
</html>
"""


def main():
    print("=" * 60)
    print("MOTIR ORGANIZATION / PROFILE PORTAL - CLEAN V1")
    print("=" * 60)

    status = verify_official_pages()
    print("official org:", "OK" if status["org_ok"] else "FALLBACK")
    print("minister profile:", "OK" if status["minister_ok"] else "FALLBACK")

    page = build_html(status)
    out = BASE_DIR / "index.html"
    out.write_text(page, encoding="utf-8")

    print("generated:", out)
    print("size:", out.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
