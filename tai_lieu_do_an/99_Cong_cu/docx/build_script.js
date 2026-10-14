const d = require('docx');
const {Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow,
       TableCell, WidthType, ShadingType, BorderStyle, LevelFormat, Footer, PageNumber} = d;
const fs = require('fs');

const W = 9000;
const FONT = "Times New Roman";

function P(t, o){ o = o || {};
  return new Paragraph({ alignment: o.al || AlignmentType.JUSTIFIED,
    spacing: { after: o.after === undefined ? 100 : o.after, line: 290 },
    children: [ new TextRun({ text: t, font: FONT, size: o.size || 24,
                              bold: !!o.b, italics: !!o.i, color: o.color }) ] });
}
function H1(t){
  return new Paragraph({ heading: HeadingLevel.HEADING_1, spacing:{before:280, after:120},
    children:[new TextRun({text:t, font:FONT, bold:true, size:28, color:"1F3864"})]});
}
function SLIDE(num, title, time){
  return new Paragraph({ heading: HeadingLevel.HEADING_2,
    spacing:{before:320, after:60},
    border:{ bottom:{ style:BorderStyle.SINGLE, size:8, color:"1F3864", space:6 } },
    children:[
      new TextRun({text:"SLIDE "+num+" — "+title, font:FONT, bold:true, size:26, color:"1F3864"}),
      new TextRun({text:"     ["+time+"]", font:FONT, bold:true, size:22, color:"C00000"})]});
}
function LBL(t){
  return new Paragraph({ spacing:{before:140, after:60},
    children:[new TextRun({text:t, font:FONT, bold:true, size:23, color:"7F7F7F"})]});
}
function B(t){
  return new Paragraph({ numbering: { reference: "bul", level: 0 },
    alignment: AlignmentType.JUSTIFIED, spacing: { after: 60, line: 280 },
    children: [ new TextRun({ text: t, font: FONT, size: 23 }) ] });
}
function SAY(t){
  return new Paragraph({ alignment: AlignmentType.JUSTIFIED,
    spacing:{after:100, line:320}, indent:{left:340},
    border:{ left:{ style:BorderStyle.SINGLE, size:12, color:"1F3864", space:10 } },
    children:[new TextRun({text:t, font:FONT, size:24})]});
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
  children:[new TextRun({text:"KỊCH BẢN TRÌNH BÀY 5 PHÚT", font:FONT, bold:true, size:32})]}));
body.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing:{after:280},
  border:{ bottom:{ style:BorderStyle.SINGLE, size:6, color:"999999", space:10 } },
  children:[new TextRun({text:"Tấn công thanh khoản do cơ chế khuyến khích gây ra trong CLMM — báo cáo tiến độ và hướng cải tiến",
    font:FONT, italics:true, size:24, color:"1F3864"})]}));

body.push(P("Sáu slide. Phần được gạch chân màu xanh là lời nói, có thể đọc gần như nguyên văn. Phần gạch đầu dòng là nội dung đưa lên slide, không đọc lên.", {i:true, size:22}));

// ===== BẢNG PHÂN BỔ =====
body.push(H1("Phân bổ thời gian"));
body.push(T(["Slide","Nội dung","Thời lượng","Mốc đồng hồ"],
  [["1","Bài toán","40 giây","0:00 – 0:40"],
   ["2","Nền tảng CLMM","50 giây","0:40 – 1:30"],
   ["3","Vì sao LP duy lý vẫn vào bẫy","60 giây","1:30 – 2:30"],
   ["4","Khoảng trống nghiên cứu","40 giây","2:30 – 3:10"],
   ["5","Kế hoạch triển khai và hướng cải tiến","90 giây","3:10 – 4:40"],
   ["6","Tiến độ và lộ trình","20 giây","4:40 – 5:00"]],
  [900,4200,1700,2200]));
body.push(gap());
body.push(P("Nguyên tắc: nếu bị trễ, cắt slide 2 chứ tuyệt đối không cắt slide 5. Slide 5 là phần người nghe cần nhất.", {b:true}));

// ===== SLIDE 1 =====
body.push(SLIDE(1, "Bài toán", "40 giây"));
body.push(LBL("Nội dung trên slide"));
body.push(B("Tiêu đề bài báo, tác giả, hội nghị USENIX Security 2026"));
body.push(B("Một hình: bốn giai đoạn tấn công theo trục thời gian"));
body.push(B("Ba con số: 29 sự kiện — 2,87 triệu USD thiệt hại — 23,8 triệu USD lợi nhuận"));
body.push(LBL("Lời nói"));
body.push(SAY("Em báo cáo về hướng đề tài dựa trên bài báo tại USENIX Security năm 2026. Bài báo chỉ ra rằng các chương trình khuyến khích giao dịch trên sàn phi tập trung, vốn được thiết kế để thu hút thanh khoản, lại tạo ra một bề mặt tấn công kinh tế."));
body.push(SAY("Kịch bản gồm bốn bước: kẻ tấn công dựng một bức tường thanh khoản cực dày, thu hút người giao dịch đang săn phần thưởng, dụ các nhà cung cấp thanh khoản khác nạp vốn theo, rồi rút tường và xả token làm giá sụp."));
body.push(SAY("Điểm đáng chú ý nhất: không có lỗi lập trình nào ở đây. Hợp đồng chạy đúng thiết kế. Lỗ hổng nằm trong chính chính sách khuyến mãi. Bài báo đo được hai mươi chín vụ trên BNB Smart Chain, gây thiệt hại hai phẩy tám bảy triệu đô cho nạn nhân."));

// ===== SLIDE 2 =====
body.push(SLIDE(2, "Nền tảng CLMM — chỉ ba ý", "50 giây"));
body.push(LBL("Nội dung trên slide"));
body.push(B("Công thức: Δz = Δy / L"));
body.push(B("Bảng hai dòng: cùng 1.000 USDT, dải 10% cho L ≈ 19.487; dải một tick cho L = 20.000.000"));
body.push(B("Một câu kết in đậm: cùng số vốn, độ sâu gấp hơn một nghìn lần"));
body.push(LBL("Lời nói"));
body.push(SAY("Em xin tóm tắt ba ý nền tảng. Thứ nhất, trong CLMM người ta làm việc trên căn bậc hai của giá, vì khi đó quan hệ giữa lượng token giao dịch và mức dịch chuyển giá là tuyến tính, nhờ đó các bài toán tối ưu mới có nghiệm dạng đóng."));
body.push(SAY("Thứ hai, liquidity L không phải là số tiền. Nó đo mức đề kháng của giá trước áp lực giao dịch."));
body.push(SAY("Thứ ba, và đây là ý quan trọng nhất: cùng một nghìn đô, nếu đặt vào dải giá rộng mười phần trăm thì tạo ra liquidity khoảng mười chín nghìn; nhưng nếu dồn vào một tick, tức dải rộng không phẩy không một phần trăm, thì tạo ra hai mươi triệu. Chênh nhau hơn một nghìn lần. Đây chính là cách kẻ tấn công dựng được bức tường trông đồ sộ mà không cần vốn lớn."));

// ===== SLIDE 3 =====
body.push(SLIDE(3, "Vì sao LP duy lý vẫn vào bẫy", "60 giây"));
body.push(LBL("Nội dung trên slide"));
body.push(B("Hàm mục tiêu: Π_V(L_V) = f · Q · L_V / (L_A + L_V) − c_V · L_V"));
body.push(B("Nghiệm: L_V* = max{0, √(f · Q · L_A / c_V) − L_A}"));
body.push(B("Điều kiện tham gia: Q > c_V · L_A / f"));
body.push(B("Một dòng in đậm màu đỏ: c_V đã bao gồm rủi ro sụp giá"));
body.push(LBL("Lời nói"));
body.push(SAY("Đây là phần cốt lõi. Nhà cung cấp thanh khoản có hai lực kéo ngược nhau: thu phí, và chịu chi phí cùng rủi ro. Phí tăng theo quy luật giảm dần vì người vào sau làm loãng phần của mọi người, còn chi phí thì tăng tuyến tính. Lấy đạo hàm cho bằng không, ta được lượng thanh khoản tối ưu như trên slide."));
body.push(SAY("Điều đáng nói nằm ở ký hiệu c_V. Theo định nghĩa, nó đã bao gồm rủi ro bị sụp giá. Nghĩa là ta đang giả định nhà cung cấp thanh khoản biết có kẻ tấn công và đã định giá đúng rủi ro đó. Vậy mà nghiệm vẫn dương, miễn là trần thưởng Q đủ lớn."));
body.push(SAY("Nói cách khác, nạn nhân không hề phi lý. Họ tính đúng và vẫn quyết định vào, vì phí thu được trong nhiều ngày chuẩn bị đủ bù cho rủi ro. Hệ quả rất quan trọng: nguyên nhân nằm ở tham số thiết kế của cơ chế, không nằm ở nhận thức người dùng. Cho nên giải pháp phải là sửa thiết kế, không phải giáo dục người dùng."));

// ===== SLIDE 4 =====
body.push(SLIDE(4, "Khoảng trống nghiên cứu", "40 giây"));
body.push(LBL("Nội dung trên slide"));
body.push(B("Bốn biện pháp bài báo đề xuất, liệt kê ngắn"));
body.push(B("Trích nguyên văn từ phần giới hạn: “the mitigations are design proposals rather than evaluations”"));
body.push(B("Trích tiếp: “evaluating mitigations through simulation, historical counterfactuals, or deployment studies”"));
body.push(LBL("Lời nói"));
body.push(SAY("Bài báo đề xuất bốn biện pháp phòng thủ. Nhưng trong phần giới hạn, chính các tác giả viết rằng đây chỉ là đề xuất thiết kế, không phải kết quả đánh giá, và hướng nghiên cứu tiếp theo là đánh giá chúng bằng mô phỏng."));
body.push(SAY("Tức là bài báo chứng minh cuộc tấn công tồn tại, đề xuất cách chống, nhưng chưa kiểm chứng cách chống nào có hiệu quả. Đó chính là chỗ đề tài của em bước vào."));

// ===== SLIDE 5 =====
body.push(SLIDE(5, "Kế hoạch triển khai và hướng cải tiến", "90 giây"));
body.push(LBL("Nội dung trên slide"));
body.push(B("Sơ đồ ba lớp: cơ chế — tác nhân — đo lường và can thiệp"));
body.push(B("Bốn chỉ số, đánh dấu chi phí trợ cấp là chỉ số bài báo không đo"));
body.push(B("Công thức can thiệp: f → f · φ(w)"));
body.push(LBL("Lời nói"));
body.push(SAY("Em sẽ xây một simulator CLMM gồm ba lớp. Lớp cơ chế là động cơ tick và căn bậc hai của giá. Lớp tác nhân gồm ba loại: kẻ tấn công, người giao dịch săn thưởng, và nhà cung cấp thanh khoản. Xin nhấn mạnh: nhà cung cấp thanh khoản phải là tác nhân tối ưu hóa theo đúng công thức ở slide trước. Nếu cài đặt họ như một tác nhân phản ứng cứng thì mọi kết quả đánh giá sẽ vô nghĩa, vì khi đó em chỉ đang điều khiển một tham số do chính mình đặt ra."));
body.push(SAY("Em đo bốn chỉ số: thiệt hại nạn nhân, lợi nhuận kẻ tấn công, chi phí trợ cấp, và thanh khoản của bể. Trong đó chi phí trợ cấp là chỉ số bài báo không đo. Bổ sung nó cho phép trả lời câu hỏi từ góc nhìn nền tảng: đốt bao nhiêu tiền trợ cấp, và bao nhiêu phần trong đó chảy thẳng vào túi kẻ tấn công."));
body.push(SAY("Hướng cải tiến em chọn là phần thưởng nhận biết khoảng giá. Lý do chọn hướng này: mô hình của bài báo cố định cấu hình một tick bằng giả định, nên độ rộng khoảng giá không tồn tại như một biến. Đây là hướng duy nhất nằm ngoài mô hình gốc."));
body.push(SAY("Cụ thể, em điều chỉnh phần chia phí của nhà cung cấp thanh khoản theo độ rộng khoảng giá: position một tick bị phạt nặng, position rộng gần như không ảnh hưởng. Tác động kỳ vọng có hai mặt. Về lượng, thanh khoản nạn nhân giảm. Về chất, và đây mới là điểm thú vị, thanh khoản phân tán ra nhiều tick nên chỉ một phần vốn nằm trên đường đi của cú sập, nạn nhân chịu thiệt hại từng phần thay vì mất toàn bộ."));

// ===== SLIDE 6 =====
body.push(SLIDE(6, "Tiến độ và lộ trình", "20 giây"));
body.push(LBL("Nội dung trên slide"));
body.push(B("Đã xong: nền tảng CLMM, đọc hiểu đầy đủ bài báo, xác định hướng cải tiến"));
body.push(B("Bốn giai đoạn tiếp theo, dạng thanh tiến độ"));
body.push(LBL("Lời nói"));
body.push(SAY("Hiện tại em đã hoàn thành nền tảng và phân tích đầy đủ bài báo. Bước tiếp theo là cài động cơ một tick và tái lập được cuộc tấn công, sau đó quét tham số để vẽ bản đồ vùng an toàn, rồi mở rộng lên nhiều tick để đánh giá biện pháp cải tiến. Em xin hết."));

// ===== HỎI ĐÁP =====
body.push(H1("Chuẩn bị hỏi đáp"));
body.push(P("Sáu câu hỏi có xác suất cao nhất, kèm câu trả lời ngắn gọn.", {i:true}));
body.push(gap());
body.push(T(["Câu hỏi","Trả lời"],
  [["Phần thưởng trả cho ai — LP hay người giao dịch?",
    "Trong bài báo, trợ cấp trả cho người giao dịch theo khối lượng, không trả cho LP. Vì người giao dịch không có khoảng giá, nên cơ chế nhận biết khoảng giá của em áp lên phần chia phí giao dịch của LP, chứ không áp lên khoản trợ cấp."],
   ["Vì sao mô phỏng mà không dùng dữ liệu thật?",
    "Vì cần phản thực. Đánh giá một biện pháp phòng thủ đòi hỏi chạy cùng một kịch bản hai lần, có và không có biện pháp. Dữ liệu lịch sử không cho phép điều đó. Bài báo cũng gặp đúng hạn chế này và tự nhận nhóm đối chứng của họ không thiết lập được nhân quả."],
   ["Làm sao biết simulator của em đúng?",
    "Em có bộ tiêu chuẩn kiểm định lấy từ kết quả thực nghiệm của bài báo: chuẩn bị theo ngày và thu hoạch theo giờ, biến động thấp lúc chuẩn bị rồi tăng vọt lúc tấn công, và quan trọng nhất là khối lượng phải tụt xuống dưới mức nền sau cú sập."],
   ["Hàm phạt theo độ rộng khoảng giá chọn thế nào?",
    "Em không cố định một hàm. Em sẽ quét một họ hàm và báo cáo đánh đổi giữa mức giảm thiệt hại và mức giảm hiệu quả sử dụng vốn của LP lành mạnh."],
   ["Đóng góp mới so với bài báo là gì?",
    "Ba điểm: đánh giá định lượng biện pháp phòng thủ mà bài báo chỉ đề xuất; bổ sung chỉ số chi phí trợ cấp mà bài báo không đo; và mở rộng mô hình sang biến độ rộng khoảng giá, vốn bị cố định bằng giả định trong bài gốc."],
   ["Có rủi ro đạo đức không?",
    "Nghiên cứu hoàn toàn trên môi trường mô phỏng và dữ liệu lịch sử công khai, không triển khai, không tương tác với hệ thống đang vận hành. Cùng cách tiếp cận với phần cân nhắc đạo đức của bài báo gốc."]],
  [3000,6000]));

body.push(H1("Ghi chú khi tập"));
body.push(B("Tổng lời nói khoảng 700 từ. Tốc độ nói tiếng Việt tự nhiên là 140 đến 150 từ một phút, vừa đúng 5 phút."));
body.push(B("Tập bấm giờ ít nhất ba lần. Mốc cần kiểm tra: hết slide 3 phải ở khoảng 2 phút 30 giây."));
body.push(B("Slide 3 và slide 5 là hai slide quan trọng nhất. Nếu thiếu thời gian, rút gọn slide 2, không rút slide 5."));
body.push(B("Không đọc công thức thành lời theo kiểu đánh vần ký hiệu. Chỉ chỉ tay lên slide và giải thích ý nghĩa."));
body.push(B("Câu cần nhớ kỹ nhất, nên nói chậm và rõ: nạn nhân duy lý, tính đúng rủi ro, vẫn quyết định vào."));

const doc = new Document({
  numbering: { config: [ { reference: "bul", levels: [ { level: 0, format: LevelFormat.BULLET,
      text: "•", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 640, hanging: 320 } } } } ] } ] },
  sections: [{
    properties: { page: { margin: { top: 1300, right: 1300, bottom: 1300, left: 1300 } } },
    footers: { default: new Footer({ children: [ new Paragraph({ alignment: AlignmentType.CENTER,
      children: [ new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 20 }) ] }) ] }) },
    children: body
  }]
});

Packer.toBuffer(doc).then(b => { fs.writeFileSync("Kich_ban_trinh_bay_5_phut.docx", b);
  console.log("OK", b.length, "bytes"); });
