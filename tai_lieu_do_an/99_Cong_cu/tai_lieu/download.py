import json, os, sys, time, urllib.request

ROOT = sys.argv[1]
cat = json.load(open("catalog.json", encoding="utf-8"))
log = {}
todo = [p for p in cat["papers"] if p["pdf"]]
for i, p in enumerate(todo, 1):
    folder = os.path.join(ROOT, p["cat"])
    os.makedirs(folder, exist_ok=True)
    dest = os.path.join(folder, p["fname"])
    key = p["fname"]
    if os.path.exists(dest) and os.path.getsize(dest) > 10000:
        log[key] = "ok (da co)"
        print(f"[{i}/{len(todo)}] SKIP {key}", flush=True)
        continue
    status = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(p["pdf"], headers={"User-Agent": "Mozilla/5.0 (student literature review)"})
            data = urllib.request.urlopen(req, timeout=90).read()
            if data[:5] != b"%PDF-":
                status = f"loi: khong phai PDF ({data[:40]!r})"
                time.sleep(5)
                continue
            open(dest, "wb").write(data)
            status = f"ok ({len(data)//1024} KB)"
            break
        except Exception as e:
            status = f"loi: {e}"
            time.sleep(8)
    log[key] = status
    print(f"[{i}/{len(todo)}] {status} {key}", flush=True)
    time.sleep(3)
json.dump(log, open("download_log.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
ok = sum(1 for v in log.values() if v.startswith("ok"))
print(f"XONG: {ok}/{len(todo)} thanh cong")
