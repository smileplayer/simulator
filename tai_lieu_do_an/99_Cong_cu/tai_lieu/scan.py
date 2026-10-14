import json, os, re, shutil, subprocess, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "01_Tai_lieu_tham_khao")
TMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "txt")
os.makedirs(TMP, exist_ok=True)
cat = json.load(open("catalog.json", encoding="utf-8"))
log = json.load(open("download_log.json", encoding="utf-8"))

GAP = re.compile(r"(future work|future research|future direction|we leave|left for future|leave .{0,30} (to|for) future|"
                 r"limitation|limited to|does not (consider|model|account|capture)|do not (consider|model|account|capture)|"
                 r"beyond the scope|out of scope|open (question|problem|challenge)|remains? (unclear|open|unexplored|an open)|"
                 r"not yet|underexplored|unexplored|no prior work|to the best of our knowledge|we assume|simplifying assumption|"
                 r"interesting direction|promising direction|could be extended|extension)", re.I)

def clean(t):
    t = t.replace("\r", "")
    t = re.sub(r"-\n(?=[a-z])", "", t)
    t = re.sub(r"[ \t]+", " ", t)
    return t

def section_cut(t):
    m = None
    for m in re.finditer(r"\n\s*(References|REFERENCES|Bibliography|BIBLIOGRAPHY)\s*\n", t):
        pass
    return t[:m.start()] if m and m.start() > len(t) * 0.4 else t

def abstract(t):
    head = t[:9000]
    m = re.search(r"abstract[\s.:—-]*", head, re.I)
    s = head[m.end():] if m else head[:3000]
    e = re.search(r"\n\s*(\d\.?\s*|I\.?\s*)?(Introduction|INTRODUCTION|Keywords|KEYWORDS|CCS Concepts|Index Terms)", s)
    s = s[:e.start()] if e and e.start() > 200 else s[:1600]
    return re.sub(r"\s+", " ", s).strip()[:1100]

def gap_sentences(t, k=10):
    body = re.sub(r"\s+", " ", t)
    sents = re.split(r"(?<=[.!?])\s+(?=[A-Z])", body)
    hits, seen = [], set()
    n = len(sents)
    for i, s in enumerate(sents):
        if 30 < len(s) < 420 and GAP.search(s):
            key = s[:60]
            if key in seen: continue
            seen.add(key)
            # weight sentences in the last 40% of the paper (conclusion / limitations)
            hits.append((0 if i > n * 0.6 else 1, i, s.strip()))
    hits.sort()
    return [h[2] for h in sorted(hits[:k], key=lambda x: x[1])]

def headed_sections(t):
    out = []
    for m in re.finditer(r"\n\s*(?:[0-9IVX]+(?:\.[0-9]+)*\.?\s+)?(Limitations?(?: and Future Work)?|Future Work|Future Directions?|"
                         r"Discussion|Conclusions?(?: and Future Work)?|Open (?:Problems|Questions|Challenges)|Threats to Validity)\s*\n", t):
        seg = re.sub(r"\s+", " ", t[m.end():m.end() + 1800]).strip()
        out.append((m.group(1), seg))
    keep = {}
    for h, s in out:
        keep[h.split()[0].lower()] = (h, s)   # last occurrence of each heading type
    return list(keep.values())

which = sys.argv[1].split(",") if len(sys.argv) > 1 else [c[0] for c in cat["cats"]]
for p in cat["papers"]:
    if p["cat"] not in which or not p["pdf"] or not str(log.get(p["fname"], "")).startswith("ok"):
        continue
    src = os.path.join(ROOT, p["cat"], p["fname"])
    tmp_pdf = os.path.join(TMP, "x.pdf")
    txt = os.path.join(TMP, p["fname"][:-4] + ".txt")
    if not os.path.exists(txt):
        shutil.copy(src, tmp_pdf)
        subprocess.run(["pdftotext", "-enc", "UTF-8", tmp_pdf, txt], check=False)
    t = clean(open(txt, encoding="utf-8", errors="replace").read())
    t = section_cut(t)
    print("=" * 100)
    print(f"[{p['cat'][:2]}] {'*'*p['prio']} {p['year']} {p['authors'].split(',')[0]} — {p['title']}")
    print("ABSTRACT:", abstract(t))
    for h, s in headed_sections(t):
        print(f"--- {h.upper()}: {s[:1300]}")
    g = gap_sentences(t)
    if g:
        print("--- CAU NOI VE GIOI HAN/HUONG TIEP:")
        for s in g: print("  •", s[:400])
