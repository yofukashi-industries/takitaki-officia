# -*- coding: utf-8 -*-
"""YouTubeチャンネルの最新動画を取得し、index.htmlのMUSIC欄を自動更新する。
GitHub Actionsから毎日実行される。標準ライブラリのみ使用。"""
import re
import html
import urllib.request
import xml.etree.ElementTree as ET

HANDLE = "takiutachannel"   # YouTubeの@ハンドル名
CHANNEL_ID = "UCK3Nz5qVqyHa-Y8_aIErl1A"  # 直接指定(空にするとHANDLEから自動解決)
MAX_VIDEOS = 3              # サイトに載せる最新動画の数
INDEX_FILE = "index.html"
START = "<!-- VIDEOS:START (この間はGitHub Actionsが自動更新するので手で編集しない) -->"
END = "<!-- VIDEOS:END -->"

UA = {"User-Agent": "Mozilla/5.0 (site-updater; +https://github.com)"}


def http_get(url: str) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def resolve_channel_id(handle: str) -> str:
    """@ハンドルのページからチャンネルID(UC...)を取り出す。
    正規URL(canonical)→externalId→channelIdの順で信頼度の高いものから試す。"""
    page = http_get(f"https://www.youtube.com/@{handle}")
    patterns = [
        r'rel="canonical" href="https://www\.youtube\.com/channel/(UC[0-9A-Za-z_-]{22})"',
        r'"externalId":"(UC[0-9A-Za-z_-]{22})"',
        r'"channelId":"(UC[0-9A-Za-z_-]{22})"',
    ]
    for p in patterns:
        m = re.search(p, page)
        if m:
            print(f"チャンネルID: {m.group(1)}")
            return m.group(1)
    raise RuntimeError("チャンネルIDが見つからない")


def fetch_videos(channel_id: str):
    """RSSフィードから (video_id, title, date) のリストを返す。"""
    xml_text = http_get(
        f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}")
    ns = {
        "a": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015",
    }
    root = ET.fromstring(xml_text)
    videos = []
    for entry in root.findall("a:entry", ns):
        vid = entry.find("yt:videoId", ns).text
        title = entry.find("a:title", ns).text or ""
        published = (entry.find("a:published", ns).text or "")[:10]  # YYYY-MM-DD
        date = published.replace("-", ".")
        videos.append((vid, title, date))
    return videos[:MAX_VIDEOS]


def build_cards(videos) -> str:
    cards = []
    for vid, title, date in videos:
        t = html.escape(title)
        cards.append(
            f'''      <a class="work-card" href="https://youtu.be/{vid}" target="_blank" rel="noopener">
        <div class="thumb"><img src="https://img.youtube.com/vi/{vid}/hqdefault.jpg" alt="{t}" loading="lazy"></div>
        <div class="work-body">
          <h3>{t}</h3>
          <p>{date} 公開</p>
        </div></a>''')
    return "\n".join(cards)


def main():
    channel_id = CHANNEL_ID or resolve_channel_id(HANDLE)
    print(f"使用チャンネルID: {channel_id}")
    videos = fetch_videos(channel_id)
    if not videos:
        print("動画が取得できなかったので変更なし")
        return

    with open(INDEX_FILE, encoding="utf-8") as f:
        page = f.read()

    if START not in page or END not in page:
        raise RuntimeError("index.htmlにマーカーが見つからない")

    before, rest = page.split(START, 1)
    _, after = rest.split(END, 1)
    new_page = before + START + "\n" + build_cards(videos) + "\n      " + END + after

    if new_page != page:
        with open(INDEX_FILE, "w", encoding="utf-8") as f:
            f.write(new_page)
        print(f"{len(videos)}本の動画で更新した")
    else:
        print("変更なし")


if __name__ == "__main__":
    main()
