const d = require('docx');
const {Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow, TableCell,
       WidthType, ShadingType, BorderStyle, LevelFormat, Footer, PageNumber, PageOrientation,
       ExternalHyperlink} = d;
const fs = require('fs');
const path = require('path');

const LIT = process.argv[2];          // folder chứa catalog.json + download_log.json
const OUT = process.argv[3];          // file docx đầu ra
const cat = JSON.parse(fs.readFileSync(path.join(LIT, 'catalog.json'), 'utf8'));
let dl = {};
try { dl = JSON.parse(fs.readFileSync(path.join(LIT, 'download_log.json'), 'utf8')); } catch (e) {}

const FONT = "Times New Roman";
const W = 15000;
const STAR = {3: "★★★", 2: "★★", 1: "★"};

function run(t, o){ o=o||{}; return new TextRun({text:t, font:FONT, size:o.size||22, bold:!!o.b, italics:!!o.i, color:o.color}); }
function P(t, o){ o=o||{};
  return new Paragraph({alignment:o.al||AlignmentType.JUSTIFIED, spacing:{after:o.after===undefined?100:o.after, line:280},
    children:[run(t,o)]}); }
function H1(t){ return new Paragraph({heading:HeadingLevel.HEADING_1, spacing:{before:300, after:120},
    children:[new TextRun({text:t, font:FONT, bold:true, size:28, color:"1F3864"})]}); }
function H2(t){ return new Paragraph({heading:HeadingLevel.HEADING_2, spacing:{before:240, after:80},
    children:[new TextRun({text:t, font:FONT, bold:true, size:25, color:"1F3864"})]}); }
function B(t){ return new Paragraph({numbering:{reference:"bul", level:0}, spacing:{after:60, line:280},
    alignment:AlignmentType.JUSTIFIED, children:[run(t)]}); }
function link(text, url){ return new ExternalHyperlink({link:url, children:[new TextRun({text, font:FONT, size:19, style:"Hyperlink", color:"0563C1", underline:{}})]}); }

function cellP(children, w, o){ o=o||{};
  return new TableCell({width:{size:w, type:WidthType.DXA},
    shading: o.head ? {type:ShadingType.CLEAR, fill:"DCE6F1"} : (o.fill ? {type:ShadingType.CLEAR, fill:o.fill} : undefined),
    margins:{top:50, bottom:50, left:80, right:80},
    children: children.map(ch => new Paragraph({spacing:{after:0, line:260}, children: Array.isArray(ch)?ch:[ch]}))}); }
function cellT(t, w, o){ o=o||{}; return cellP([run(t,{size:o.size||19, b:!!o.head||!!o.b, color:o.color})], w, o); }
function table(headers, rows, widths){
  const hr = new TableRow({tableHeader:true, children: headers.map((h,i)=>cellT(h, widths[i], {head:true}))});
  return new Table({columnWidths:widths, width:{size:W, type:WidthType.DXA}, rows:[hr].concat(rows)}); }
function gap(){ return new Paragraph({spacing:{after:120}, children:[run("")]}); }

const papers = cat.papers;
const isOk = p => p.pdf && dl[p.fname] && String(dl[p.fname]).startsWith("ok");
const nOk = papers.filter(isOk).length;
const nPdf = papers.filter(p=>p.pdf).length;

const body = [];
body.push(new Paragraph({alignment:AlignmentType.CENTER, spacing:{after:60},
  children:[new TextRun({text:"DANH MỤC TÀI LIỆU NGHIÊN CỨU", font:FONT, bold:true, size:34})]}));
body.push(new Paragraph({alignment:AlignmentType.CENTER, spacing:{after:80},
  children:[new TextRun({text:"Tấn công thanh khoản do cơ chế khuyến khích trong CLMM và hướng thưởng nhận biết khoảng giá", font:FONT, bold:true, size:26, color:"1F3864"})]}));
body.push(new Paragraph({alignment:AlignmentType.CENTER, spacing:{after:280},
  border:{bottom:{style:BorderStyle.SINGLE, size:6, color:"999999", space:10}},
  children:[run(`Lập ngày 04/10/2026  ·  ${papers.length} mục  ·  ${nOk}/${nPdf} bản PDF mở đã tải  ·  bao phủ đủ 57/57 tài liệu tham khảo của bài gốc`, {i:true, size:21})]}));

// ===== 1. Cách dùng
body.push(H1("1. Cách dùng danh mục"));
body.push(B("Mức ưu tiên: ★★★ đọc ngay, phục vụ trực tiếp các giai đoạn GĐ1–GĐ3 của simulator; ★★ nên đọc; ★ tham khảo khi cần."));
body.push(B("Cột [Ref] là số thứ tự trong danh mục tham khảo của bài gốc (Lu et al., USENIX Security 2026). Ô trống nghĩa là bài nằm ngoài danh mục đó, được tìm thêm cho hướng của nhóm."));
body.push(B("Cột Tệp/Nguồn: “PDF” mở thẳng tệp đã tải trong thư mục con (file danh mục này phải nằm ở thư mục gốc); “Trang gốc” mở trang nguồn trên mạng."));
body.push(B("Chỉ tải bản mở: arXiv, IACR ePrint, Zenodo, tạp chí truy cập mở và whitepaper chính thức. Bài trả phí chỉ ghi nguồn để tra bằng Google Scholar hoặc thư viện trường."));
body.push(gap());
body.push(table(["Thư mục", "Chủ đề", "Vai trò với đề tài", "Số mục"],
  cat.cats.map(c => new TableRow({children:[
    cellT(c[0], 3600, {b:true}), cellT(c[1], 3000), cellT(c[2], 7600),
    cellT(String(papers.filter(p=>p.cat===c[0]).length), 800)]})),
  [3600, 3000, 7600, 800]));

// ===== 2. Lộ trình đọc
body.push(H1("2. Lộ trình đọc đề xuất theo giai đoạn"));
body.push(P("Không cần đọc hết 100 mục. Bảng dưới là thứ tự đọc khoảng 15 bài cốt lõi, khớp với kế hoạch bốn giai đoạn của simulator."));
const road = [
 ["Trước GĐ1 — dựng engine", "Uniswap v3 Core (whitepaper) → Fritsch 2021 → Tarantelli 2026 (simulator kiểm định)", "Nắm đặc tả tick, √P, cross-tick, fee growth; lấy cách kiểm định trên dữ liệu mainnet làm chuẩn cho engine."],
 ["GĐ1 — tác nhân và chi phí", "Milionis et al. 2022 (LVR) → Heimbach et al. 2022 → Fritsch & Canidio 2024", "Đặt chi phí c_V của LP có cơ sở; có dữ liệu hành vi LP thật để kiểm định victim agent."],
 ["GĐ2 — đánh giá biện pháp của bài gốc", "Kirillov & Chung 2022 (StableSims) → Zhou et al. SoK DeFi Attacks", "Học khuôn dùng mô phỏng tác nhân để chọn tham số khuyến khích; định vị cuộc tấn công trong phân loại tấn công DeFi."],
 ["GĐ3 — thưởng nhận biết khoảng giá", "Tang et al. 2025 → izumi 2021 → Paradigm 2021 → Merkl → Xiong et al. 2023 (JIT) → Trotti et al. 2025", "Nền lý thuyết LP chọn độ rộng; toàn bộ prior art về thưởng theo khoảng giá; JIT là cùng nguyên thủy vị thế siêu hẹp và có số liệu pha loãng để hiệu chỉnh."],
 ["GĐ4 — phát hiện bất thường (nếu còn thời gian)", "RajabiNekoo et al. 2025 (SILS) → Yaremus et al. 2025 → Shoaei et al. 2026", "Phát hiện rút thanh khoản trong CLMM; tín hiệu dựa trên TVL; cách tránh rò rỉ dữ liệu tương lai khi huấn luyện."],
];
body.push(table(["Giai đoạn", "Đọc theo thứ tự", "Để làm gì"],
  road.map(r => new TableRow({children:[cellT(r[0], 3000, {b:true}), cellT(r[1], 5800), cellT(r[2], 6200)]})),
  [3000, 5800, 6200]));

// ===== 3. Prior art vs gap
body.push(H1("3. Bản đồ prior art và khoảng trống"));
body.push(P("Tổng hợp từ đợt tra cứu: mảnh nào đã có người làm, và chỗ nào vẫn còn trống cho đề tài."));
const gaps = [
 ["Cơ chế CLMM và simulator", "Có, kể cả simulator đã kiểm định trên dữ liệu mainnet", "Uniswap v3; Tarantelli 2026", "Chưa simulator nào có trợ cấp, kẻ tấn công và nạn nhân"],
 ["Lý thuyết LP chọn độ rộng khoảng giá", "Có", "Tang et al. 2025", "Không có trợ cấp, không có tấn công"],
 ["Vị thế siêu hẹp và pha loãng phí", "Có, dưới tên JIT liquidity", "Xiong et al. 2023; Trotti et al. 2025; Capponi et al. 2023", "JIT diễn ra trong một giao dịch, không dụ nạn nhân, không có trợ cấp"],
 ["Thưởng theo khoảng giá", "Có, cả trong thực tế lẫn học thuật", "Merkl (loại trừ vị thế siêu hẹp); izumi 2021 (thưởng theo bin)", "Chưa từng được đánh giá như biện pháp an ninh trước cuộc tấn công này"],
 ["Dùng mô phỏng để chọn tham số khuyến khích", "Có phương pháp", "StableSims 2022 (MakerDAO)", "Chưa áp vào CLMM hay cuộc tấn công này"],
 ["Đánh giá định lượng bốn biện pháp của bài gốc", "Chưa có", "—", "Còn trống hoàn toàn — đóng góp chính của GĐ2"],
 ["Điều kiện hàm phạt φ phải siêu tuyến tính", "Chưa thấy ai phát biểu", "—", "Đóng góp riêng của nhóm ở GĐ3"],
];
body.push(table(["Mảnh", "Đã có chưa", "Ai làm", "Còn trống"],
  gaps.map((r,i) => new TableRow({children:[cellT(r[0], 3400, {b:true}), cellT(r[1], 3000), cellT(r[2], 4000),
    cellT(r[3], 4600, {fill: i>=5 ? "E2EFDA" : undefined})]})),
  [3400, 3000, 4000, 4600]));

// ===== 4. Ghi chú
body.push(H1("4. Ghi chú khi tra cứu"));
body.push(B("Chưa tìm thấy công trình nào trích dẫn bài gốc. Bài đăng tháng 08/2026 nên còn quá mới; nên tra lại trên Google Scholar mục “Cited by” sau vài tháng."));
body.push(B("Bài gốc không trích dẫn nhóm JIT, Merkl, izumi và bài Paradigm, dù cùng chủ đề vị thế siêu hẹp và thưởng theo khoảng giá. Nên đưa cả bốn vào phần Related Work của nhóm."));
body.push(B("Ruizhe Jia, đồng tác giả bài gốc, cũng là đồng tác giả bài “The Paradox of Just-in-Time Liquidity” (thư mục 04)."));
body.push(B("Weizhao Tang là tác giả của cả bài lý thuyết trò chơi [45] lẫn bài phân tích chiến lược JIT — hai bài nối trực tiếp với nhau, nên đọc liền."));
body.push(B("Các số liệu JIT như 36.671 vụ và mức pha loãng 85% lấy từ bản tóm tắt; cần đối chiếu trực tiếp với PDF trong thư mục 04 trước khi trích vào báo cáo."));
body.push(B("Mã nguồn có thể dùng ngay: CLMM-game (đi kèm bài [45]), Uniswap-V3-Simulator, uniswap-simulator — xem thư mục 07."));

// ===== 5. Bảng chi tiết theo nhóm
body.push(H1("5. Danh mục chi tiết theo nhóm"));
const widths = [700, 650, 2300, 3800, 1900, 4150, 1500];
cat.cats.forEach((c, ci) => {
  body.push(H2(`${c[0]} — ${c[1]}`));
  body.push(P(c[2], {i:true, size:21}));
  const items = papers.filter(p=>p.cat===c[0]).sort((a,b)=> b.prio-a.prio || b.year-a.year);
  const rows = items.map(p => {
    const src = [];
    if (isOk(p)) src.push([link("PDF", `${p.cat}/${p.fname}`)]);
    else if (p.pdf) src.push([run("Tải tay qua trình duyệt", {size:17, color:"C00000"})]);
    if (p.link) src.push([link("Trang gốc", p.link)]);
    if (!src.length) src.push([run("Tra Scholar", {size:18, i:true})]);
    const titleRun = [run(p.title, {size:19, b: p.prio===3})];
    return new TableRow({children:[
      cellT(STAR[p.prio], widths[0], {color: p.prio===3 ? "C00000" : undefined}),
      cellT(String(p.year), widths[1]),
      cellT(p.authors, widths[2]),
      cellP([titleRun, [run(p.ref ? `[Ref ${p.ref}]` : "", {size:17, color:"7F7F7F"})]], widths[3]),
      cellT(p.venue, widths[4]),
      cellT(p.why, widths[5]),
      cellP(src, widths[6]),
    ]});
  });
  body.push(table(["Ưu tiên", "Năm", "Tác giả", "Tên bài", "Nơi đăng", "Vì sao liên quan", "Tệp / Nguồn"], rows, widths));
});

const doc = new Document({
  numbering:{config:[{reference:"bul", levels:[{level:0, format:LevelFormat.BULLET, text:"•", alignment:AlignmentType.LEFT,
    style:{paragraph:{indent:{left:600, hanging:300}}}}]}]},
  sections:[{
    properties:{page:{size:{width:11906, height:16838, orientation:PageOrientation.LANDSCAPE},
      margin:{top:900, right:900, bottom:900, left:900}}},
    footers:{default:new Footer({children:[new Paragraph({alignment:AlignmentType.CENTER,
      children:[new TextRun({children:[PageNumber.CURRENT], font:FONT, size:18})]})]})},
    children: body
  }]
});
Packer.toBuffer(doc).then(b => { fs.writeFileSync(OUT, b); console.log("OK", b.length, "bytes ->", OUT); });
