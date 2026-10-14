import re, sys, zipfile

src = sys.argv[1]
dst = sys.argv[2]
z = zipfile.ZipFile(src)
x = z.read('word/document.xml').decode('utf-8')

out = []
# walk document in order, emitting paragraphs and table rows
for m in re.finditer(r'<w:tbl>.*?</w:tbl>|<w:p\b.*?</w:p>|<w:p\b[^>]*/>', x, re.S):
    blk = m.group(0)
    if blk.startswith('<w:tbl'):
        out.append('--- TABLE ---')
        for row in re.findall(r'<w:tr\b.*?</w:tr>', blk, re.S):
            cells = []
            for c in re.findall(r'<w:tc>.*?</w:tc>', row, re.S):
                t = ''.join(re.findall(r'<w:t[^>]*>(.*?)</w:t>', c, re.S))
                cells.append(t.strip())
            out.append(' | '.join(cells))
        out.append('--- END TABLE ---')
    else:
        st = re.search(r'w:val="([^"]*[Hh]eading[^"]*|[^"]*Title[^"]*)"', blk)
        t = ''.join(re.findall(r'<w:t[^>]*>(.*?)</w:t>', blk, re.S))
        t = t.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        if t.strip():
            out.append(('<' + st.group(1) + '> ' if st else '') + t)

open(dst, 'w', encoding='utf-8').write('\n'.join(out))
print('tables:', x.count('<w:tbl>'), '| blocks:', len(out))
