import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote
import re

OC = "chetera"
BASE = "http://www.law.go.kr"

def get_law_list_from_api(query):
    exact_query = f'\"{query}\"'
    encoded_query = quote(exact_query)
    page = 1
    laws = []

    while True:
        url = f"{BASE}/DRF/lawSearch.do?OC={OC}&target=law&type=XML&display=100&page={page}&search=2&knd=A0002&query={encoded_query}"
        res = requests.get(url, timeout=10)
        res.encoding = 'utf-8'
        if res.status_code != 200:
            break

        root = ET.fromstring(res.content)
        found = 0
        for law in root.findall("law"):
            name = law.findtext("법령명한글", "").strip()
            mst = law.findtext("법령일련번호", "")
            detail = law.findtext("법령상세링크", "")
            full_link = BASE + detail
            laws.append({"법령명": name, "MST": mst, "URL": full_link})
            found += 1

        if found < 100:
            break
        page += 1

    return laws

def get_law_text_by_mst(mst):
    url = f"{BASE}/DRF/lawService.do?OC={OC}&target=law&MST={mst}&type=XML"
    try:
        res = requests.get(url, timeout=10)
        res.encoding = 'utf-8'
        if res.status_code == 200:
            return res.content
    except Exception as e:
        print(f"[오류] 본문 요청 실패 (MST={mst}):", e)
    return None

def clean(text):
    return re.sub(r"\s+", "", text or "")

def highlight_if_contains(text, keyword):
    if keyword in clean(text):
        return re.sub(f"({re.escape(keyword)})", r"<span style='color:red'>\1</span>", text or "")
    return text or ""

def get_highlighted_articles(mst, keyword):
    xml_data = get_law_text_by_mst(mst)
    if not xml_data:
        return "⚠️ 본문을 불러올 수 없습니다."

    tree = ET.fromstring(xml_data)
    articles = tree.findall(".//조문")
    results = []

    for article in articles:
        jo = article.findtext("조번호", "").strip()
        title = article.findtext("조문제목", "") or ""
        content = article.findtext("조문내용", "") or ""
        항들 = article.findall("항")

        조문_출력대상 = False
        항_텍스트들 = []

        for hang in 항들:
            ha = hang.findtext("항번호", "").strip()
            text = hang.findtext("항내용", "") or ""
            if keyword in clean(text):
                조문_출력대상 = True
            항_텍스트들.append((ha, text))

        if keyword in clean(content) or keyword in clean(title):
            조문_출력대상 = True

        if 조문_출력대상:
            output = f"<br><strong>📌 제{jo}조 {highlight_if_contains(title, keyword)}</strong><br>"
            output += f"{highlight_if_contains(content, keyword)}<br>"
            for ha, text in 항_텍스트들:
                항출력 = highlight_if_contains(text, keyword)
                output += f"제{ha}항: {항출력}<br>"
            results.append(output)

    if not results:
        return "🔍 해당 단어를 포함한 조문이 없습니다."
    return "".join(results)
