const d = require('docx');
const {Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow,
       TableCell, WidthType, ShadingType, BorderStyle, LevelFormat, Footer, PageNumber} = d;
const fs = require('fs');

const W = 9200;
const FONT = "Times New Roman";

function P(t, o){ o = o || {};
  return new Paragraph({ alignment: o.al || AlignmentType.JUSTIFIED,
    spacing: { after: o.after === undefined ? 100 : o.after, line: 290 },
    children: [ new TextRun({ text: t, font: FONT, size: o.size || 24,
                              bold: !!o.b, italics: !!o.i, color: o.color }) ] });
}
function H1(t){
  return new Paragraph({ heading: HeadingLevel.HEADING_1, spacing:{before:300, after:120},
    children:[new TextRun({text:t, font:FONT, bold:true, size:28, color:"1F3864"})]});
}
function SLIDE(num, title, time, src){
  return new Paragraph({ heading: HeadingLevel.HEADING_2,
    spacing:{before:340, after:60},
    border:{ bottom:{ style:BorderStyle.SINGLE, size:8, color:"1F3864", space:6 } },
    children:[
      new TextRun({text:"SLIDE "+num+"  —  "+title, font:FONT, bold:true, size:26, color:"1F3864"}),
      new TextRun({text:"     ["+time+"]", font:FONT, bold:true, size:22, color:"C00000"}),
      new TextRun({text:"     nguồn: "+src, font:FONT, size:20, color:"7F7F7F"})]});
}
function LBL(t){
  return new Paragraph({ spacing:{before:150, after:60},
    children:[new TextRun({text:t, font:FONT, bold:true, size:23, color:"7F7F7F"})]});
}
function B(t){
  return new Paragraph({ numbering: { reference: "bul", level: 0 },
    alignment: AlignmentType.JUSTIFIED, spacing: { after: 60, line: 280 },
    children: [ new TextRun({ text: t, font: FONT, size: 23 }) ] });
}
function SAY(t){
  return new Paragraph({ alignment: AlignmentType.JUSTIFIED,
    spacing:{after:110, line:320}, indent:{left:340},
    border:{ left:{ style:BorderStyle.SINGLE, size:12, color:"1F3864", space:10 } },
    children:[new TextRun({text:t, font:FONT, size:24})]});
}
function NOTE(t){
  return new Paragraph({ alignment: AlignmentType.JUSTIFIED,
    spacing:{before:80, after:100, line:290}, indent:{left:200},
    shading:{ type: ShadingType.CLEAR, fill:"FFF2CC" },
    children:[new TextRun({text:t, font:FONT, size:22, italics:true})]});
}
function cell(t, w, opts){ opts = opts || {};
  return new TableCell({ width: { size: w, type: WidthType.DXA },
    shading: opts.head ? { type: ShadingType.CLEAR, fill: "DCE6F1" } : undefined,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [ new Paragraph({ spacing:{after:0, line:280},
      children: [ new TextRun({ text: t, font: FONT, size: 22, bold: !!opts.head }) ] }) ] });
}
function T(headers, rows, widths){
  const hr = new TableRow({ tableHeader:true, children: headers.map((h,i)=>cell(h,widths[i],{head:true})) });
  const rs = rows.map(r => new TableRow({ children: r.map((c,i)=>cell(c,widths[i])) }));
  return new Table({ columnWidths: widths, width:{size:W,type:WidthType.DXA}, rows:[hr].concat(rs) });
}
function gap(){ return new Paragraph({ spacing:{after:140}, children:[new TextRun("")] }); }

const body = [];

body.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing:{after:60},
  children:[new TextRun({text:"KỊCH BẢN TRÌNH BÀY NHÓM", font:FONT, bold:true, size:32})]}));
body.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing:{after:80},
  children:[new TextRun({text:"Tấn công thanh khoản do cơ chế khuyến khích gây ra trong CLMM",
    font:FONT, bold:true, size:26, color:"1F3864"})]}));
body.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing:{after:300},
  border:{ bottom:{ style:BorderStyle.SINGLE, size:6, color:"999999", space:10 } },
  children:[new TextRun({text:"8 slide — 7 phút — một người trình bày (có hướng dẫn rút xuống 5 phút)",
    font:FONT, italics:true, size:23})]}));

body.push(P("Phần có viền xanh bên trái là lời nói, đọc được gần như nguyên văn. Phần gạch đầu dòng là nội dung đưa lên slide, không đọc lên. Ô vàng là ghi chú cho người nói.", {i:true, size:22}));

// ===== PHÂN BỔ =====
body.push(H1("Phân bổ thời gian"));
body.push(T(["Slide","Nội dung","Giây","Mốc đồng hồ","Nguồn"],
  [["1","Vấn đề và bài báo","32","0:00 – 0:32","Chung"],
   ["2","Nền tảng CLMM","52","0:32 – 1:24","Báo cáo A"],
   ["3","Hai tầng khuyến khích","49","1:24 – 2:13","A + Notion"],
   ["4","Diễn biến cuộc tấn công","74","2:13 – 3:27","Notion, Hình 1"],
   ["5","Bằng chứng thực nghiệm","61","3:27 – 4:28","Notion, Hình 2–4"],
   ["6","Nghịch lý LP lý trí","64","4:28 – 5:32","Notion + Báo cáo C"],
   ["7","Khoảng trống và hướng của nhóm","85","5:32 – 6:57","Báo cáo C"],
   ["8","Lộ trình","21","6:57 – 7:18","Chung"]],
  [800,3100,700,1800,2800]));
body.push(gap());
body.push(P("Tổng lời nói 1.090 âm tiết. Ở tốc độ nói tự nhiên 150 âm tiết một phút, bản đầy đủ chạy khoảng 7 phút 20 giây. Nếu nói nhanh hơn một chút hoặc bỏ bớt chỗ dừng thì về đúng 7 phút. Nếu chỉ được 5 phút, xem mục Cách rút xuống 5 phút ở cuối.", {b:true}));

// ===== SLIDE 1 =====
body.push(SLIDE(1, "Vấn đề và bài báo", "30 giây", "Chung"));
body.push(LBL("Nội dung trên slide"));
body.push(B("Tên bài báo, nhóm tác giả, hội nghị USENIX Security 2026"));
body.push(B("Một câu in đậm giữa slide: không có lỗi lập trình nào — lỗ hổng nằm trong chính chính sách khuyến mãi"));
body.push(B("Tên ba thành viên và phần phụ trách, cỡ chữ nhỏ ở góc"));
body.push(LBL("Lời nói"));
body.push(SAY("Nhóm em báo cáo về bài báo tại USENIX Security 2026, nhan đề Khai thác thanh khoản như một bề mặt tấn công."));
body.push(SAY("Phát hiện chính: các chương trình thưởng theo khối lượng giao dịch, vốn thiết kế để thu hút thanh khoản, lại tạo ra một bề mặt tấn công kinh tế. Đáng chú ý nhất là không có lỗi lập trình nào ở đây. Hợp đồng chạy đúng thiết kế. Lỗ hổng nằm trong chính chính sách khuyến mãi."));

// ===== SLIDE 2 =====
body.push(SLIDE(2, "Nền tảng CLMM", "60 giây", "Báo cáo A"));
body.push(LBL("Nội dung trên slide"));
body.push(B("Hình minh họa: trục giá chia thành tick, một position phủ một khoảng, trạng thái in-range và out-of-range"));
body.push(B("Bảng hai dòng: cùng 1.000 USDT — dải rộng 10% cho L ≈ 19.487; dải một tick cho L = 20.000.000"));
body.push(B("Một dòng in đậm: cùng số vốn, độ sâu gấp hơn một nghìn lần"));
body.push(LBL("Lời nói"));
body.push(SAY("Trước hết là nền tảng. Trong mô hình thanh khoản tập trung, người cung cấp thanh khoản được chọn một khoảng giá để đặt vốn, thay vì rải đều trên toàn miền giá. Trục giá chia thành các mốc gọi là tick, mỗi tick ứng với không phẩy không một phần trăm chênh lệch giá. Giá nằm trong khoảng thì vị thế thu phí, ra ngoài thì ngừng."));
body.push(SAY("Điểm quan trọng nhất: đại lượng thanh khoản không phải là số tiền. Nó đo mức đề kháng của giá trước áp lực giao dịch. Cùng một nghìn đô, đặt vào dải rộng mười phần trăm thì tạo ra thanh khoản khoảng mười chín nghìn. Nhưng dồn vào đúng một tick thì tạo ra hai mươi triệu, gấp hơn một nghìn lần."));
body.push(NOTE("Đây là con số gây ấn tượng nhất của cả bài. Nói chậm hai số 19.487 và 20 triệu, dừng một nhịp trước khi sang slide sau."));

// ===== SLIDE 3 =====
body.push(SLIDE(3, "Hai tầng khuyến khích", "45 giây", "Báo cáo A + Notion"));
body.push(LBL("Nội dung trên slide"));
body.push(B("Sơ đồ chuỗi dọc: σ trả cho trader theo khối lượng → sinh khối lượng V → phí f·V → chia cho LP theo L_i / L_tổng → APY hiển thị cao → LP nạn nhân nạp vốn"));
body.push(B("Đánh dấu tầng trên là ngoại sinh, nền tảng chi trả; tầng dưới là nội sinh, từ phí của bể"));
body.push(LBL("Lời nói"));
body.push(SAY("Cần phân biệt hai tầng khuyến khích, vì đây là chỗ dễ nhầm. Tầng thứ nhất là trợ cấp từ bên ngoài, do nền tảng chi trả, trả cho người giao dịch theo khối lượng và có trần. Ví dụ điển hình là chương trình tích điểm Binance Alpha. Tầng thứ hai là phí giao dịch của chính bể, chia cho người cung cấp thanh khoản theo tỷ trọng thanh khoản."));
body.push(SAY("Hai tầng nối thành một chuỗi: trợ cấp tạo ra khối lượng, khối lượng sinh ra phí, phí chia theo tỷ trọng tạo ra lợi suất hiển thị cao, lợi suất cao hút người cung cấp thanh khoản nạp vốn. Đây chính là đường dẫn mà kẻ tấn công khai thác."));

// ===== SLIDE 4 =====
body.push(SLIDE(4, "Diễn biến cuộc tấn công", "75 giây", "Notion, Hình 1"));
body.push(LBL("Nội dung trên slide"));
body.push(B("Hình 1 của bài báo: timeline bốn bước"));
body.push(B("Nhãn từng bước: Large Mint — Point Farmers — Victim LP Entry — Large Burn — Crash & Value Extraction"));
body.push(LBL("Lời nói"));
body.push(SAY("Cuộc tấn công diễn ra theo bốn bước. Bước một, dựng tường: kẻ tấn công nạp lượng lớn thanh khoản vào đúng một tick quanh giá hiện tại. Bể lập tức trông rất sâu, giao dịch gần như không trượt giá."));
body.push(SAY("Bước hai, thu hút người săn điểm. Vì chi phí giao dịch rẻ nhất thị trường, những người đang cày điểm đổ vào bể này, khối lượng tăng vọt và sinh ra phí."));
body.push(SAY("Bước ba, gài bẫy nạn nhân. Người cung cấp thanh khoản thấy lợi suất cao bất thường và nạp vốn vào cùng khoảng giá hẹp đó. Họ không phân biệt được giao dịch thật với giao dịch do trợ cấp đẻ ra."));
body.push(SAY("Bước bốn, rút và xả. Kẻ tấn công rút toàn bộ thanh khoản của mình, rồi bán mạnh token phụ để lấy token chính. Giá sụp, nạn nhân ôm toàn bộ tài sản đã mất giá."));
body.push(SAY("Xin nhấn mạnh bước rút. Nếu không rút, kẻ tấn công sẽ bán vào chính vị thế của mình, coi như bán cho chính mình. Rút ra thì toàn bộ cú xả đi qua vốn của nạn nhân."));
body.push(NOTE("Slide dài nhất. Nếu thấy trễ giờ, gộp bước hai và ba thành một câu."));

// ===== SLIDE 5 =====
body.push(SLIDE(5, "Bằng chứng thực nghiệm", "60 giây", "Notion, Hình 2–4"));
body.push(LBL("Nội dung trên slide"));
body.push(B("Hình 2: biểu đồ hộp biến động qua bốn giai đoạn Before, Prep, Attack, Post"));
body.push(B("Ba con số trung vị in to: 0,0119 — 0,1593 — 0,8843"));
body.push(B("Dòng số liệu: 29 sự kiện, 18 pool, 99 địa chỉ nạn nhân, 2,87 triệu USD"));
body.push(LBL("Lời nói"));
body.push(SAY("Bài báo kiểm chứng trên BNB Smart Chain trong mười tháng, với các bể thuộc chương trình Binance Alpha. Kết quả: hai mươi chín sự kiện tấn công trên mười tám bể, chín mươi chín địa chỉ nạn nhân, tổng thiệt hại hai phẩy tám bảy triệu đô."));
body.push(SAY("Hình bên trái là bằng chứng thuyết phục nhất, đo biến động giá qua bốn giai đoạn. Giai đoạn chuẩn bị, biến động thấp nhất, trung vị chỉ không phẩy không một một chín, vì bức tường ghim chặt giá. Sang giai đoạn tấn công, tăng lên không phẩy một năm chín ba khi tường bị rút. Sau tấn công, bùng nổ lên không phẩy tám tám bốn ba, gấp bảy mươi lần giai đoạn chuẩn bị."));
body.push(SAY("Hai hình còn lại cho thấy phân phối đuôi dày: phần lớn tổn thất tập trung vào một số ít nạn nhân và một vài vụ cực lớn."));

// ===== SLIDE 6 =====
body.push(SLIDE(6, "Nghịch lý LP lý trí", "60 giây", "Notion + Báo cáo C"));
body.push(LBL("Nội dung trên slide"));
body.push(B("Hàm lợi nhuận của nạn nhân: Π_V = f · Q · L_V / (L_A + L_V) − c_V · L_V"));
body.push(B("Phản ứng tối ưu: L_V* = max{0, √(f · Q · L_A / c_V) − L_A}"));
body.push(B("Điều kiện tham gia: Q > c_V · L_A / f"));
body.push(B("Một dòng đỏ in đậm: c_V đã bao gồm rủi ro sụp giá"));
body.push(LBL("Lời nói"));
body.push(SAY("Đây là phần lý thuyết cốt lõi. Người cung cấp thanh khoản chịu hai lực ngược nhau: phí thu được tăng theo quy luật giảm dần vì người vào sau làm loãng phần của mọi người, còn chi phí tăng tuyến tính. Lấy đạo hàm cho bằng không, ta được lượng thanh khoản tối ưu như trên slide."));
body.push(SAY("Điều đáng nói nằm ở ký hiệu c_V. Theo định nghĩa, nó đã bao gồm rủi ro sụp giá, nghĩa là ta giả định người cung cấp thanh khoản biết có kẻ tấn công và định giá đúng rủi ro đó. Vậy mà nghiệm vẫn dương, miễn là trần thưởng đủ lớn."));
body.push(SAY("Nói cách khác, nạn nhân không hề phi lý. Họ tính đúng và vẫn quyết định vào, vì phí thu trong nhiều ngày chuẩn bị đủ bù rủi ro. Hệ quả: nguyên nhân nằm ở tham số thiết kế, không nằm ở nhận thức người dùng. Giải pháp phải là sửa thiết kế."));
body.push(NOTE("Đây là slide quan trọng nhất về mặt học thuật. Đừng đọc công thức thành lời theo kiểu đánh vần ký hiệu — chỉ tay lên slide và giải thích ý nghĩa."));

// ===== SLIDE 7 =====
body.push(SLIDE(7, "Khoảng trống và hướng của nhóm", "75 giây", "Báo cáo C"));
body.push(LBL("Nội dung trên slide"));
body.push(B("Bốn biện pháp bài báo đề xuất, liệt kê một dòng mỗi cái"));
body.push(B("Trích nguyên văn: “the mitigations are design proposals rather than evaluations”"));
body.push(B("Sơ đồ simulator ba lớp: cơ chế — tác nhân — đo lường và can thiệp"));
body.push(B("Bốn chỉ số, tô sáng chi phí trợ cấp kèm ghi chú bài báo không đo"));
body.push(B("Công thức can thiệp: f → f · φ(w)"));
body.push(LBL("Lời nói"));
body.push(SAY("Bài báo đề xuất bốn biện pháp phòng thủ. Nhưng chính các tác giả viết rằng đây chỉ là đề xuất thiết kế, không phải kết quả đánh giá, và hướng tiếp theo là kiểm chứng bằng mô phỏng. Đó là khoảng trống nhóm em nhắm vào."));
body.push(SAY("Nhóm em xây một simulator ba lớp: cơ chế, tác nhân, và đo lường có điểm móc để bật tắt từng biện pháp phòng thủ. Điểm quan trọng: người cung cấp thanh khoản phải là tác nhân tối ưu hóa theo công thức ở slide trước, nếu không kết quả đánh giá sẽ vô nghĩa."));
body.push(SAY("Nhóm đo bốn chỉ số: thiệt hại nạn nhân, lợi nhuận kẻ tấn công, chi phí trợ cấp và thanh khoản của bể. Chi phí trợ cấp là chỉ số bài báo không đo, nó cho biết nền tảng đốt bao nhiêu tiền và bao nhiêu chảy vào túi kẻ tấn công."));
body.push(SAY("Hướng cải tiến nhóm chọn là phần thưởng nhận biết khoảng giá: điều chỉnh phần chia phí theo độ rộng khoảng, phạt nặng vị thế một tick. Chọn hướng này vì mô hình gốc cố định cấu hình một tick bằng giả định, nên độ rộng khoảng giá chưa tồn tại như một biến."));

// ===== SLIDE 8 =====
body.push(SLIDE(8, "Lộ trình", "15 giây", "Chung"));
body.push(LBL("Nội dung trên slide"));
body.push(B("Bốn giai đoạn dạng thanh tiến độ: động cơ một tick → quét tham số → mở rộng nhiều tick và range-aware → kết quả bổ sung"));
body.push(LBL("Lời nói"));
body.push(SAY("Nhóm đã hoàn thành nền tảng và phân tích bài báo. Bước tiếp theo là cài động cơ một tick để tái lập cuộc tấn công, quét tham số để vẽ bản đồ vùng an toàn, rồi mở rộng lên nhiều tick để đánh giá biện pháp cải tiến. Nhóm em xin hết."));

// ===== RÚT XUỐNG 5 PHÚT =====
body.push(H1("Cách rút xuống 5 phút"));
body.push(P("Nếu ban tổ chức chốt 5 phút thay vì 7, áp dụng đúng ba thao tác sau, còn lại giữ nguyên:", {b:false}));
body.push(T(["Thao tác","Chi tiết","Tiết kiệm"],
  [["Gộp slide 3 vào slide 2","Bỏ slide riêng, chỉ giữ lại sơ đồ chuỗi ở góc slide 2 và nói gọn: trợ cấp trả cho người giao dịch theo khối lượng, phí chia cho LP theo tỷ trọng thanh khoản","≈ 35 giây"],
   ["Rút gọn slide 4","Gộp bước hai và ba thành một câu, bỏ đoạn giải thích vì sao phải rút thanh khoản trước","≈ 25 giây"],
   ["Rút gọn slide 5","Bỏ đoạn nói về hai hình phân phối đuôi dày, chỉ giữ ba con số biến động và dòng số liệu","≈ 20 giây"]],
  [2400,4800,2000]));
body.push(gap());
body.push(P("Tuyệt đối không cắt slide 6 và slide 7. Slide 6 là phần học thuật mạnh nhất, slide 7 là phần nhóm đang được đánh giá.", {b:true}));

// ===== HỎI ĐÁP =====
body.push(H1("Chuẩn bị hỏi đáp"));
body.push(T(["Câu hỏi","Trả lời"],
  [["Phần thưởng trả cho ai, người cung cấp thanh khoản hay người giao dịch?",
    "Có hai tầng. Trợ cấp ngoại sinh của chương trình trả cho người giao dịch theo khối lượng. Phí giao dịch của bể thì chia cho người cung cấp thanh khoản theo tỷ trọng thanh khoản. Tầng trên tạo ra khối lượng, tầng dưới biến khối lượng đó thành lợi suất hiển thị."],
   ["Vì sao kẻ tấn công chọn đúng một tick?",
    "Có hai lý do cùng dẫn tới một tick. Thứ nhất, cùng một lượng vốn thì dải càng hẹp càng tạo ra thanh khoản lớn, nên giảm trượt giá mạnh nhất và hút người săn điểm. Thứ hai, tỷ trọng thanh khoản cao cũng làm tăng phần phí được chia. Nhóm em có nêu cả hai trong báo cáo."],
   ["Vì sao mô phỏng mà không dùng dữ liệu thật?",
    "Vì cần phản thực. Đánh giá một biện pháp phòng thủ đòi hỏi chạy cùng một kịch bản hai lần, có và không có biện pháp. Dữ liệu lịch sử không cho phép điều đó. Bài báo cũng gặp đúng hạn chế này và tự nhận nhóm đối chứng của họ không thiết lập được quan hệ nhân quả."],
   ["Làm sao biết simulator của nhóm chạy đúng?",
    "Nhóm có bộ tiêu chuẩn kiểm định lấy từ kết quả thực nghiệm của bài báo: chuẩn bị kéo dài theo ngày còn thu hoạch theo giờ, biến động thấp lúc chuẩn bị rồi bùng nổ sau tấn công, và quan trọng nhất là khối lượng phải tụt xuống dưới mức nền sau cú sập."],
   ["Hàm phạt theo độ rộng khoảng giá chọn thế nào?",
    "Nhóm không cố định một hàm. Nhóm sẽ quét một họ hàm và báo cáo đánh đổi giữa mức giảm thiệt hại và mức giảm hiệu quả sử dụng vốn của người cung cấp thanh khoản lành mạnh."],
   ["Đóng góp mới của nhóm so với bài báo là gì?",
    "Ba điểm. Một là đánh giá định lượng các biện pháp phòng thủ mà bài báo chỉ đề xuất. Hai là bổ sung chỉ số chi phí trợ cấp mà bài báo không đo. Ba là mở rộng mô hình sang biến độ rộng khoảng giá, vốn bị cố định bằng giả định trong bài gốc."],
   ["Nghiên cứu này có rủi ro đạo đức không?",
    "Toàn bộ thực hiện trên môi trường mô phỏng và dữ liệu lịch sử công khai, không triển khai, không tương tác với hệ thống đang vận hành. Cùng cách tiếp cận với phần cân nhắc đạo đức của bài báo gốc."]],
  [3200,6000]));

// ===== GHI CHÚ TẬP =====
body.push(H1("Ghi chú khi tập"));
body.push(B("Tập bấm giờ ít nhất ba lần. Mốc kiểm tra: hết slide 4 phải ở khoảng 3 phút 30 giây. Nếu quá 4 phút thì phải rút gọn slide 5."));
body.push(B("Ba con số cần đọc chậm và rõ: 20 triệu ở slide 2, và ba mốc biến động 0,0119 — 0,1593 — 0,8843 ở slide 5."));
body.push(B("Câu cần nhớ kỹ nhất, nên dừng một nhịp trước khi nói: nạn nhân duy lý, tính đúng rủi ro, vẫn quyết định vào."));
body.push(B("Không đọc công thức thành lời theo kiểu đánh vần từng ký hiệu. Chỉ tay lên slide và nói ý nghĩa của nó."));
body.push(B("Vì chỉ một người trình bày, nên nhắc tên và phần phụ trách của cả ba thành viên ở slide 1, rồi không nhắc lại nữa."));
body.push(B("Chuẩn bị sẵn một câu chốt dự phòng nếu bị nhắc hết giờ ở slide 7: nhóm em sẽ dừng ở đây, phần lộ trình chi tiết có trong báo cáo."));

const doc = new Document({
  numbering: { config: [ { reference: "bul", levels: [ { level: 0, format: LevelFormat.BULLET,
      text: "•", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 640, hanging: 320 } } } } ] } ] },
  sections: [{
    properties: { page: { margin: { top: 1250, right: 1200, bottom: 1250, left: 1200 } } },
    footers: { default: new Footer({ children: [ new Paragraph({ alignment: AlignmentType.CENTER,
      children: [ new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 20 }) ] }) ] }) },
    children: body
  }]
});

Packer.toBuffer(doc).then(b => { fs.writeFileSync("Kich_ban_trinh_bay_nhom.docx", b);
  console.log("OK", b.length, "bytes"); });
