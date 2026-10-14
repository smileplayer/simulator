import re, sys, time, json, urllib.request, html

IDS = sys.argv[1].split(",")
out = {}
for aid in IDS:
    url = f"https://arxiv.org/abs/{aid}"
    title = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (literature-review script)"})
            h = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
            m = re.search(r'<meta name="citation_title" content="([^"]+)"', h)
            d = re.search(r'<meta name="citation_date" content="([^"]+)"', h)
            a = re.findall(r'<meta name="citation_author" content="([^"]+)"', h)
            title = html.unescape(m.group(1)) if m else "?"
            out[aid] = {"title": title, "date": d.group(1) if d else "?", "authors": a[:3]}
            break
        except Exception as e:
            out[aid] = {"error": str(e)}
            time.sleep(6)
    print(aid, "|", out[aid].get("date", ""), "|", out[aid].get("title", out[aid].get("error")), flush=True)
    time.sleep(3)
json.dump(out, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
