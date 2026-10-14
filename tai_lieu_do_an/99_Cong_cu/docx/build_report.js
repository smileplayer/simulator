const d = require('docx');
const {Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow,
       TableCell, WidthType, ShadingType, BorderStyle, LevelFormat, Footer, PageNumber} = d;
const fs = require('fs');

const W = 9000;
const FONT = "Times New Roman";

function P(t, o){ o = o || {};
  return new Paragraph({ alignment: o.al || AlignmentType.JUSTIFIED,
    spacing: { after: o.after === undefined ? 120 : o.after, line: 300 },
    children: [ new TextRun({ text: t, font: FONT, size: o.size || 24,
                              bold: !!o.b, italics: !!o.i, color: o.color }) ] });
}
function H(t, lvl){
  return new Paragraph({ heading: lvl, spacing: { before: 260, after: 120 },
    children: [ new TextRun({ text: t, font: FONT, bold: true,
      size: lvl === HeadingLevel.HEADING_1 ? 28 : 25, color: "1F3864" }) ] });
}
function H1(t){ return H(t, HeadingLevel.HEADING_1); }
function H2(t){ return H(t, HeadingLevel.HEADING_2); }
function F(t){
  return new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 140, after: 140 },
    children: [ new TextRun({ text: t, font: "Cambria Math", size: 24, italics: true }) ] });
}
function B(t){
  return new Paragraph({ numbering: { reference: "bul", level: 0 },
    alignment: AlignmentType.JUSTIFIED, spacing: { after: 80, line: 300 },
    children: [ new TextRun({ text: t, font: FONT, size: 24 }) ] });
}
function cell(t, w, opts){ opts = opts || {};
  return new TableCell({ width: { size: w, type: WidthType.DXA },
    shading: opts.head ? { type: ShadingType.CLEAR, fill: "DCE6F1" } : undefined,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [ new Paragraph({ alignment: AlignmentType.LEFT, spacing:{after:0, line:280},
      children: [ new TextRun({ text: t, font: FONT, size: 22, bold: !!opts.head }) ] }) ] });
}
function T(headers, rows, widths){
  const hr = new TableRow({ tableHeader: true,
    children: headers.map((h,i) => cell(h, widths[i], {head:true})) });
  const rs = rows.map(r => new TableRow({ children: r.map((c,i) => cell(c, widths[i])) }));
  return new Table({ columnWidths: widths, width: { size: W, type: WidthType.DXA },
    rows: [hr].concat(rs) });
}
function gap(){ return new Paragraph({ spacing:{after:140}, children:[new TextRun("")] }); }

const body = [];

body.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing:{after:60},
  children:[new TextRun({text:"BÁO CÁO TIẾN ĐỘ LẦN 2", font:FONT, bold:true, size:32})]}));
body.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing:{after:240},
  children:[new TextRun({text:"Tái lập và đánh giá biện pháp phòng thủ trước tấn công thanh khoản do cơ chế khuyến khích gây ra trong CLMM",
    font:FONT, bold:true, size:26, color:"1F3864"})]}));
body.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing:{after:320},
  border:{ bottom:{ style:BorderStyle.SINGLE, size:6, color:"999999", space:10 } },
  children:[new TextRun({text:"Tài liệu tham chiếu chính: N. S. Lu, C. K. Lao, Y. Mao, X. Zhou, R. Jia, K. Y. Wang, “Liquidity Mining as an Attack Surface: Incentive-Induced Liquidity Attacks in Concentrated Liquidity Market Makers”, 35th USENIX Security Symposium, 2026.",
    font:FONT, size:20, italics:true})]}));

// ===== 1 =====
body.push(H1("1. Mục tiêu và phạm vi"));
body.push(P("Mục tiêu của đề tài là xây dựng một môi trường mô phỏng CLMM cho phép tái lập cuộc tấn công thanh khoản do cơ chế khuyến khích gây ra (incentive-induced liquidity attack), đo lường định lượng hậu quả kinh tế của cuộc tấn công, và đánh giá hiệu quả của các biện pháp phòng thủ. Điểm cuối cùng là trọng tâm: bài báo gốc đề xuất bốn biện pháp giảm thiểu nhưng không kiểm chứng biện pháp nào, và chính các tác giả xác định đây là hướng nghiên cứu cần tiếp tục."));
body.push(P("Phạm vi của giai đoạn hiện tại bao gồm ba nội dung: (i) hoàn thiện nền tảng lý thuyết về CLMM ở mức đủ để cài đặt; (ii) phân tích đầy đủ cơ chế tấn công và mô hình cân bằng kinh tế của bài báo; (iii) xác định kiến trúc simulator, bộ chỉ số đo lường và hướng cải tiến cụ thể."));
body.push(P("Nằm ngoài phạm vi: triển khai hợp đồng thông minh trên mạng thật, kiểm toán mã nguồn, và mọi hình thức tương tác với hệ thống đang vận hành. Toàn bộ nghiên cứu được thực hiện trên môi trường mô phỏng và dữ liệu lịch sử công khai."));

// ===== 2 =====
body.push(H1("2. Nền tảng CLMM"));
body.push(H2("2.1. Thanh khoản tập trung, position và tick"));
body.push(P("CLMM là biến thể của AMM cho phép nhà cung cấp thanh khoản (LP) tập trung vốn vào một khoảng giá xác định thay vì phân bổ trên toàn miền giá. Thanh khoản của LP được tổ chức thành các position, mỗi position gắn với một khoảng giá xác định bởi biên dưới và biên trên."));
body.push(P("Trục giá được rời rạc hóa thành các mốc gọi là tick, với quan hệ P(i) = 1,0001^i. Mỗi tick tương ứng đúng 0,01% chênh lệch giá. Khi giá nằm trong khoảng của position, position được xem là in-range và đóng góp vào active liquidity; khi giá ra ngoài khoảng, position trở thành out-of-range, ngừng thu phí và chỉ còn giữ một loại tài sản."));
body.push(P("Một position có tickUpper − tickLower = 1, gọi là position một tick, là dải hẹp nhất mà giao thức cho phép. Đây là cấu hình trung tâm của cuộc tấn công được nghiên cứu."));

body.push(H2("2.2. Vai trò của căn bậc hai của giá"));
body.push(P("Đặt z = √P. Với liquidity L = √(x·y), quan hệ giữa lượng token và giá trong một position in-range được biểu diễn bằng hai công thức:"));
body.push(F("Δy = L(√P − √Pₐ)          Δx = L(1/√P − 1/√Pᵦ)"));
body.push(P("trong đó P là giá hiện tại, Pₐ là biên dưới và Pᵦ là biên trên của position."));
body.push(P("Ý nghĩa quan trọng của phép đổi biến z = √P không nằm ở tính thẩm mỹ mà ở chỗ nó làm cho quan hệ giữa lượng token giao dịch và mức dịch chuyển giá trở thành tuyến tính. Trong phạm vi một tick, L là hằng số, do đó:"));
body.push(F("Δy = L · Δz        hay tương đương        Δz = Δy / L"));
body.push(P("Đây là cơ sở toán học cho toàn bộ phần lý thuyết của bài báo. Nhờ tính tuyến tính này, các bài toán tối ưu trong mô hình có nghiệm dạng đóng; nếu làm việc trực tiếp trên biến P, các phương trình trở thành phi tuyến và không thể chứng minh được các định lý ngưỡng."));
body.push(P("Hệ quả trực tiếp của công thức Δz = Δy/L là: L đóng vai trò đại lượng đo mức độ đề kháng của giá trước áp lực giao dịch. L càng lớn thì cùng một lệnh giao dịch càng làm giá dịch chuyển ít, tức trượt giá càng thấp."));

body.push(H2("2.3. Liquidity không đồng nhất với vốn"));
body.push(P("Liquidity L là một đại lượng toán học, không phải giá trị vốn tính bằng USD. Cùng một lượng vốn đặt vào các khoảng giá khác nhau tạo ra lượng liquidity khác nhau. Ví dụ định lượng sau minh họa mức chênh lệch. Giả sử LP có 1.000 USDT, nạp vào bể tại giá P₀ = 1 và đặt ngay dưới giá hiện tại, khi đó toàn bộ vốn nằm ở token1 và áp dụng y = L(z₀ − z_L):"));
body.push(T(["Khoảng giá của position","Độ rộng","z₀ − z_L","Liquidity L tạo ra"],
  [["[0,90 ; 1,00]","10%","0,051317","≈ 19.487"],
   ["[0,9999 ; 1,00]","0,01% (một tick)","0,000050","= 20.000.000"]],
  [3000,1600,1800,2600]));
body.push(gap());
body.push(P("Cùng 1.000 USDT nhưng liquidity chênh nhau hơn một nghìn lần. Đây chính là hiệu quả sử dụng vốn của CLMM, và cũng là lý do một tác nhân không cần vốn lớn vẫn có thể tạo ra độ sâu thị trường trông rất đáng tin cậy. Cái giá phải trả là position một tick trở thành out-of-range chỉ sau một biến động 0,01%."));

body.push(H2("2.4. Phí giao dịch và hiệu ứng pha loãng"));
body.push(P("Mỗi giao dịch swap chịu một khoản phí theo tỷ lệ f, phân bổ cho các LP có thanh khoản đang hoạt động theo tỷ lệ liquidity của họ. Ở mức trừu tượng đủ dùng cho mô hình, phí tích lũy trên mỗi đơn vị liquidity thỏa mãn:"));
body.push(F("phí trên mỗi đơn vị liquidity  ∝  khối lượng giao dịch / L_active"));
body.push(P("Hệ quả cần nhấn mạnh: với khối lượng giao dịch cố định, việc bổ sung thanh khoản làm loãng phần phí mà mỗi đơn vị liquidity nhận được. Nói cách khác, LP tham gia sau làm giảm lợi suất của chính mình và của những LP đã có mặt. Đây là cơ chế khiến bài toán tối ưu của LP có nghiệm hữu hạn, và là nền tảng của phân tích cân bằng ở mục 4."));
body.push(P("Các chi tiết cài đặt của Uniswap v3 như biến tích lũy fee growth toàn cục hay fee growth ngoài khoảng là kỹ thuật tối ưu chi phí tính toán trên chuỗi; mô hình kinh tế của bài báo không sử dụng đến, do đó không được đào sâu trong phạm vi đề tài."));

// ===== 3 =====
body.push(H1("3. Cơ chế tấn công thanh khoản do incentive gây ra"));
body.push(H2("3.1. Chương trình khuyến khích theo khối lượng giao dịch"));
body.push(P("Cần phân biệt rõ đối tượng nhận trợ cấp trong mô hình của bài báo. Trợ cấp không được trả cho LP theo lượng thanh khoản cung cấp, mà được trả cho người giao dịch theo khối lượng giao dịch phát sinh."));
body.push(P("Cụ thể, ký hiệu σ ∈ [0,1] là cường độ trợ cấp quy đổi ra tiền mặt tương đương, trả cho trader trên khối lượng giao dịch gộp, với trần Q; khối lượng vượt quá Q không được thưởng thêm. Phần thưởng này là ngoại sinh đối với bể: nó do nền tảng chi trả, không lấy từ phí giao dịch của bể. Ví dụ điển hình là chương trình Binance Alpha Points, trong đó người dùng tích điểm bằng cách giao dịch các token thuộc danh mục Alpha và dùng điểm để đủ điều kiện nhận airdrop hoặc suất phân phối token."));
body.push(P("Sự phân biệt này có ý nghĩa quyết định đối với thiết kế biện pháp phòng thủ và sẽ được đề cập lại ở mục 6.4."));

body.push(H2("3.2. Ba nhóm tác nhân"));
body.push(T(["Tác nhân","Mục tiêu","Đặc điểm quyết định"],
  [["Kẻ tấn công","Chuyển hóa lượng token0 đang nắm giữ thành token1","Chủ động tạo thanh khoản L_A để định hình điều kiện thị trường"],
   ["LP nạn nhân","Thu phí từ thanh khoản cung cấp","Không phân biệt được khối lượng giao dịch thật với khối lượng do trợ cấp tạo ra"],
   ["Trader được trợ cấp","Tích lũy phần thưởng theo khối lượng","Hoàn toàn thờ ơ với giá trị nội tại của token và với biến động giá"]],
  [1900,2800,4300]));
body.push(gap());
body.push(P("Đặc điểm của nhóm thứ ba là mấu chốt: họ tạo ra khối lượng giao dịch ở bất kỳ bể nào có trợ cấp vượt chi phí, bất kể khối lượng đó có lợi hay có hại cho những người tham gia khác. Do đó họ là một dòng lệnh có thể đặt hàng được, và kẻ tấn công thu hút được họ chỉ bằng cách giảm chi phí thực hiện, không cần liên lạc hay thỏa thuận với họ."));
body.push(P("Về năng lực, kẻ tấn công chỉ cần bốn quyền, và không quyền nào là bất thường: nạp và rút thanh khoản tùy ý; giao dịch trong bể; tham gia chương trình thưởng theo đúng luật công khai; và ảnh hưởng gián tiếp tới khối lượng giao dịch thông qua việc định hình độ sâu thị trường. Không cần lỗ hổng mã nguồn, không cần quyền quản trị, không cần kiểm soát thứ tự giao dịch. Ngoài ra, do các tham số σ và Q được công bố công khai, kẻ tấn công tính toán trước được khối lượng giao dịch sẽ phát sinh ứng với mỗi mức thanh khoản."));

body.push(H2("3.3. Bốn giai đoạn của cuộc tấn công"));
body.push(T(["Giai đoạn","Hành động","Cơ chế"],
  [["1. Dựng tường","Nạp thanh khoản L_A tập trung vào một tick quanh giá hiện tại","Độ sâu thị trường tăng vọt, chi phí thực hiện giảm mạnh"],
   ["2. Tạo khối lượng","Trader được trợ cấp bị thu hút bởi chi phí giao dịch thấp","Khối lượng tăng, sinh phí giao dịch, đẩy lợi suất hiển thị lên cao"],
   ["3. Nạp thanh khoản nạn nhân","LP quan sát lợi suất cao và nạp thanh khoản L_V","Lợi suất hiển thị là số liệu quá khứ, chưa tính hiệu ứng pha loãng"],
   ["4. Rút và bóc tách","Rút toàn bộ L_A, sau đó bán token0 qua thanh khoản còn lại","Giá sụp; nạn nhân giữ tài sản mất giá, kẻ tấn công thoát với token1"]],
  [2000,3500,3500]));
body.push(gap());
body.push(P("Bước rút thanh khoản trước khi bán là bắt buộc về mặt kinh tế. Nếu giữ nguyên L_A, tỷ lệ L_A/(L_A + L_V) của lượng bán sẽ được hấp thụ bởi chính vị thế của kẻ tấn công, tức là hắn bán cho chính mình và không thu được gì ngoài việc mất phí. Sau khi rút, toàn bộ lượng bán đi qua thanh khoản của nạn nhân."));
body.push(P("Về phía nạn nhân, một position in-range chứa token1 ở phần dưới giá hiện tại và token0 ở phần trên. Khi giá sụp xuyên qua biên dưới, toàn bộ token1 của nạn nhân bị mua hết bằng token0, và position trở thành out-of-range. Nạn nhân kết thúc với toàn bộ tài sản nằm ở token0 đã mất giá, đồng thời ngừng thu phí."));

body.push(H2("3.4. Kết quả đo lường thực nghiệm của bài báo"));
body.push(P("Bài báo quét toàn bộ các bể kiểu Uniswap v3 trên BNB Smart Chain trong mười tháng (01/2025 đến 10/2025), sử dụng log Mint, Burn, Swap kết hợp tín hiệu giá theo giờ ngoài chuỗi để xác thực."));
body.push(T(["Chỉ số","Giá trị"],
  [["Số sự kiện tấn công được xác thực","29 sự kiện trên 18 bể"],
   ["Thiệt hại của nạn nhân","2.874.406 USD, 99 địa chỉ, 13 sự kiện có thiệt hại"],
   ["Lợi nhuận của kẻ tấn công","23.884.128 USD, 149 địa chỉ, trong đó 131 địa chỉ có lãi"],
   ["Mức độ tập trung","Sự kiện lớn nhất chiếm 45,80%; năm sự kiện lớn nhất chiếm 86,64%"],
   ["Bất đối xứng thời gian","12/29 sự kiện chuẩn bị trên ba ngày; 18/29 sự kiện thu hoạch dưới 24 giờ"],
   ["Khối lượng sau cú sập","23/29 sự kiện tụt xuống dưới mức nền trước tấn công"],
   ["Nhóm đối chứng","Năm bể PancakeSwap ngoài chương trình khuyến khích: không phát hiện sự kiện nào"]],
  [3200,5800]));
body.push(gap());
body.push(P("Hai điểm cần lưu ý khi diễn giải. Thứ nhất, lợi nhuận của kẻ tấn công và thiệt hại của nạn nhân không phải một cặp có tổng bằng không: kẻ tấn công còn bóc tách qua các tick lân cận và các bên nằm ngoài tập nạn nhân được nhận diện, đồng thời có dòng tiền ngoại sinh từ trợ cấp bơm vào hệ thống. Thứ hai, con số 2,87 triệu USD là ước lượng cận dưới, vì không tính các bên bị ảnh hưởng khác như người nắm giữ token thông thường."));

// ===== 4 =====
body.push(H1("4. Vì sao LP duy lý vẫn tham gia"));
body.push(H2("4.1. Hành vi của trader được trợ cấp"));
body.push(P("Lợi ích ròng của một trader khi thực hiện khối lượng v trong cửa sổ đo được biểu diễn:"));
body.push(F("U_T(v) = σ · min{v, Q} − f · v − MC(v)"));
body.push(P("trong đó f là tỷ lệ phí của bể và MC(v) là chi phí thực hiện kỳ vọng, chủ yếu gồm trượt giá. Do trượt giá phụ thuộc vào L theo quan hệ Δz = Δy/L, hàm MC chính là mắt xích nối bức tường thanh khoản với dòng lệnh: L_A càng lớn thì MC càng nhỏ và khối lượng tối ưu càng cao."));
body.push(P("Xét đạo hàm tại vùng vượt trần, tức v > Q. Khi đó số hạng thưởng đã trở thành hằng số nên:"));
body.push(F("dU_T/dv = − f − MC′(v) < 0"));
body.push(P("Biểu thức này luôn âm. Do đó trader duy lý không bao giờ giao dịch vượt quá Q, và khối lượng cân bằng bị ghim tại trần. Đây là cơ sở của giả định trần bị ràng buộc trong bài báo, đồng thời là điểm mà biện pháp điều chỉnh trần khai thác."));

body.push(H2("4.2. Phản ứng tối ưu của LP"));
body.push(P("Với khối lượng được trợ cấp cố định tại Q, lợi nhuận của LP nạn nhân khi cung cấp thanh khoản L_V là:"));
body.push(F("Π_V(L_V) = f · Q · L_V / (L_A + L_V) − c_V · L_V"));
body.push(P("Số hạng thứ nhất là phí thu được, tăng theo quy luật giảm dần do hiệu ứng pha loãng; số hạng thứ hai là chi phí hiệu dụng c_V nhân với lượng thanh khoản, trong đó c_V bao gồm chi phí vốn, tổn thất tạm thời kỳ vọng và rủi ro sụp giá, và tăng tuyến tính. Lấy đạo hàm theo L_V rồi cho bằng không, thu được phản ứng tối ưu:"));
body.push(F("L_V* = max{ 0 ,  √( f · Q · L_A / c_V ) − L_A }"));
body.push(P("Điều kiện để LP quyết định tham gia, tức L_V* > 0, rút gọn thành:"));
body.push(F("Q  >  c_V · L_A / f"));

body.push(H2("4.3. Nghịch lý nạn nhân duy lý"));
body.push(P("Theo định nghĩa, c_V đã bao gồm rủi ro sụp giá. Nghĩa là công thức trên giả định LP biết có khả năng bị tấn công và đã định giá đúng rủi ro đó. Tuy vậy L_V* vẫn dương miễn là trần Q đủ lớn."));
body.push(P("Kết luận rút ra: việc LP tham gia không phải là sai lầm nhận thức mà là một quyết định có kỳ vọng dương. Phí thu được trong giai đoạn chuẩn bị, vốn kéo dài nhiều ngày, đủ bù cho rủi ro sụp giá. Nếu LP còn đánh giá thấp rủi ro thì c_V nhỏ hơn và lượng thanh khoản cung cấp còn lớn hơn nữa."));
body.push(P("Đây là điểm khiến bài báo mạnh hơn các nghiên cứu mô tả người dùng bị lừa: vì nạn nhân duy lý vẫn thua, nguyên nhân nằm ở tham số thiết kế của cơ chế chứ không nằm ở nhận thức của người dùng. Do đó biện pháp khắc phục phải là thay đổi thiết kế, không phải giáo dục người dùng."));
body.push(P("Hệ quả trực tiếp đối với đề tài: tác nhân LP trong simulator bắt buộc phải là tác nhân tối ưu hóa theo công thức ở mục 4.2. Nếu cài đặt LP như một tác nhân phản ứng cứng theo ngưỡng lợi suất, mọi kết quả đánh giá biện pháp phòng thủ sẽ mất giá trị, vì khi đó ta chỉ đang điều khiển một tham số do chính mình đặt ra."));

body.push(H2("4.4. Ngưỡng khả thi và ba vùng thiết kế"));
body.push(P("Về phía kẻ tấn công, lợi nhuận được phân tách thành bốn thành phần:"));
body.push(F("Π_A = f · V · L_A/(L_A + L_V)  +  U_dump  −  c_A · X_sold  −  κ"));
body.push(P("gồm phần thu phí, phần bóc tách từ cú sập, chi phí kho hàng và ma sát giao dịch. Hai thành phần đầu biến thiên ngược chiều theo L_V: nạn nhân tham gia càng nhiều thì phần phí càng bị pha loãng nhưng phần bóc tách càng lớn. Thành phần thứ hai chiếm ưu thế, nên chiến lược tối ưu là chấp nhận giảm thu phí để thu hút nhiều thanh khoản nạn nhân nhất có thể."));
body.push(P("Bài báo chứng minh tồn tại ngưỡng Q* sao cho tấn công có lợi hơn phương án bán trực tiếp khi và chỉ khi Q ≥ Q*. Kết hợp với ngưỡng trợ cấp, không gian thiết kế của nền tảng chia thành ba vùng:"));
body.push(T(["Vùng thiết kế","Điều kiện","Kết quả"],
  [["Bootstrap an toàn","σ dưới ngưỡng hoặc Q < Q*","Trợ cấp thu hút khối lượng mà không tạo điều kiện cho tấn công"],
   ["Tăng trưởng rủi ro","σ và Q đều vượt ngưỡng","Đạt chỉ tiêu khối lượng nhưng tấn công trở thành hành vi tối ưu"],
   ["Tối ưu có ràng buộc","Chủ động giữ σ dưới ngưỡng","Chấp nhận khối lượng thấp hơn để bảo vệ LP"]],
  [2200,2600,4200]));
body.push(gap());
body.push(P("Nếu chỉ tiêu khối lượng chỉ đạt được khi cả hai tham số vượt ngưỡng, nền tảng đối mặt với một đánh đổi ràng buộc: hoặc hạ chỉ tiêu, hoặc chấp nhận rủi ro tấn công. Ba vùng này chính là lưới thí nghiệm sẽ được sử dụng ở mục 6."));

// ===== 5 =====
body.push(H1("5. Khoảng trống nghiên cứu"));
body.push(P("Bài báo đề xuất bốn biện pháp giảm thiểu: hiệu chỉnh trần và phí; trì hoãn thời điểm trả thưởng; công bố thông tin rủi ro tại thời điểm LP nạp vốn; và áp dụng trần động kích hoạt theo tín hiệu bất thường."));
body.push(P("Tuy nhiên, trong phần giới hạn, các tác giả nêu rõ rằng các biện pháp này là đề xuất thiết kế chứ không phải kết quả đánh giá, do đó hiệu quả thực tế có thể khác. Hướng nghiên cứu tiếp theo được chính các tác giả đề xuất bao gồm việc đánh giá biện pháp giảm thiểu thông qua mô phỏng, phản thực lịch sử, hoặc nghiên cứu triển khai."));
body.push(P("Đề tài này nhắm trực tiếp vào khoảng trống đó. Lý do lựa chọn phương pháp mô phỏng thay vì phân tích dữ liệu lịch sử là yêu cầu về phản thực: để đánh giá một biện pháp phòng thủ, cần chạy cùng một kịch bản tấn công hai lần, có và không có biện pháp, rồi so sánh kết quả. Dữ liệu lịch sử không cung cấp được điều này. Bản thân bài báo cũng gặp hạn chế tương tự và phải sử dụng nhóm đối chứng theo bối cảnh, đồng thời tự nhận rằng so sánh đó không thiết lập được quan hệ nhân quả."));
body.push(P("Ngoài ra, bài báo đo thiệt hại của nạn nhân và lợi nhuận của kẻ tấn công nhưng không đo chi phí trợ cấp mà nền tảng bỏ ra. Đây là một chỉ số còn thiếu, và việc bổ sung nó cho phép đánh giá hiệu quả chi tiêu của chương trình khuyến khích từ góc nhìn của nhà thiết kế."));

// ===== 6 =====
body.push(H1("6. Kế hoạch triển khai"));
body.push(H2("6.1. Kiến trúc simulator"));
body.push(P("Hệ thống được tổ chức thành ba lớp:"));
body.push(B("Lớp cơ chế: động cơ CLMM cài đặt trên không gian z = √P, hỗ trợ tick, position theo khoảng giá, chuyển trạng thái in-range và out-of-range, thực thi swap và tích lũy phí theo tỷ lệ liquidity."));
body.push(B("Lớp tác nhân: kẻ tấn công, gồm lựa chọn L_A, thời điểm rút và quy tắc dừng khi bán; trader được trợ cấp, tối ưu hàm U_T với trần Q; LP nạn nhân, tối ưu hàm Π_V theo công thức ở mục 4.2."));
body.push(B("Lớp đo lường và can thiệp: thu thập bốn chỉ số, đồng thời cung cấp điểm móc để bật hoặc tắt từng biện pháp phòng thủ nhằm tạo ra cặp kịch bản phản thực."));
body.push(P("Giai đoạn đầu cài đặt động cơ một tick theo đúng giả định của bài báo. Giai đoạn sau mở rộng lên nhiều tick, điều bắt buộc phải có vì cú sập giá đi xuyên qua nhiều tick và vì hướng cải tiến được chọn cần đến biến độ rộng khoảng giá."));

body.push(H2("6.2. Bốn chỉ số đo lường"));
body.push(T(["Chỉ số","Cách đo","Ghi chú"],
  [["Thiệt hại nạn nhân","Giá trị token1 theo kịch bản phản thực giữ nguyên tài sản, trừ đi phần thực sự thu hồi và giá trị còn lại của token0","Đo theo đúng định nghĩa của bài báo để có thể đối chiếu"],
   ["Lợi nhuận kẻ tấn công","Dòng tiền token1 ròng trong cửa sổ từ lúc rút thanh khoản đến lúc giá sụp","Đo độc lập với thiệt hại nạn nhân"],
   ["Chi phí trợ cấp","Tổng σ · min{V, Q} trên toàn bộ quá trình mô phỏng","Bài báo không đo chỉ số này"],
   ["Thanh khoản bể","Active liquidity theo thời gian, so sánh trước và sau tấn công","Dùng để đo mức suy giảm sau tấn công"]],
  [2200,4300,2500]));
body.push(gap());
body.push(P("Từ chỉ số thứ ba có thể dẫn xuất hai đại lượng đánh giá hiệu quả chương trình khuyến khích: tỷ lệ thanh khoản thực giữ lại được trên mỗi đồng trợ cấp, và tỷ lệ rò rỉ, tức phần trợ cấp chuyển hóa thành lợi nhuận của kẻ tấn công."));

body.push(H2("6.3. Tiêu chuẩn kiểm định simulator"));
body.push(P("Trước khi đánh giá bất kỳ biện pháp phòng thủ nào, simulator phải tái lập được các dấu hiệu định tính mà bài báo quan sát được trên dữ liệu thật:"));
body.push(T(["Dấu hiệu","Tiêu chuẩn cần đạt"],
  [["Bất đối xứng thời gian","Giai đoạn chuẩn bị tính theo ngày, giai đoạn thu hoạch tính theo giờ"],
   ["Khối lượng giai đoạn chuẩn bị","Cao hơn mức nền nhưng tăng vừa phải, không đột biến"],
   ["Khối lượng giai đoạn tấn công","Phân tán, một số kịch bản vượt nhiều lần mức nền"],
   ["Khối lượng sau cú sập","Tụt xuống dưới mức nền trước tấn công"],
   ["Biến động giá","Thấp trong giai đoạn chuẩn bị, tăng vọt trong giai đoạn tấn công"],
   ["Dịch chuyển giá","Gần bằng không quanh lúc dựng tường, âm lớn sau khi rút thanh khoản"]],
  [3200,5800]));
body.push(gap());
body.push(P("Dấu hiệu quan trọng nhất là khối lượng tụt xuống dưới mức nền sau cú sập. Đạt được dấu hiệu này chứng tỏ dòng lệnh trong mô phỏng thực sự phụ thuộc vào bức tường thanh khoản, chứ không phải do được áp đặt bằng tay."));

body.push(H2("6.4. Hướng cải tiến: phần thưởng nhận biết khoảng giá"));
body.push(P("Trong bốn biện pháp mà bài báo đề xuất, ba biện pháp đầu chỉ cần định lượng hóa điều đã được nêu sẵn. Hướng được chọn cho đề tài là phần thưởng nhận biết khoảng giá (range-aware reward), vì đây là hướng duy nhất nằm ngoài mô hình của bài báo: mô hình gốc cố định cấu hình một tick bằng giả định, do đó độ rộng khoảng giá không tồn tại như một biến."));
body.push(P("Do trợ cấp trong mô hình gốc được trả cho trader, mà trader không có khoảng giá, cần xác định rõ đối tượng áp dụng. Đề tài lựa chọn phương án điều chỉnh phần chia phí giao dịch của LP theo độ rộng khoảng giá:"));
body.push(F("f  →  f · φ(w)     với φ là hàm tăng theo độ rộng khoảng w"));
body.push(P("Theo đó position một tick bị giảm mạnh phần phí được hưởng, trong khi position có khoảng giá rộng gần như không bị ảnh hưởng."));
body.push(P("Cơ chế tác động dự kiến có hai mặt. Thứ nhất, về mặt lượng: f hiệu dụng giảm làm L_V* giảm theo công thức ở mục 4.2. Thứ hai, và quan trọng hơn, về mặt chất: khi khoảng giá hẹp không còn được ưu đãi, thanh khoản của LP phân tán ra nhiều tick, nên chỉ một phần vốn nằm trên đường đi của cú sập. Nạn nhân chịu thiệt hại từng phần thay vì mất toàn bộ. Đây là cơ chế phòng thủ thay đổi hình dạng phân bố thanh khoản chứ không chỉ thay đổi khối lượng của nó."));
body.push(P("Rủi ro cần kiểm soát: việc thiết kế hàm φ phải được biện hộ, và cần đo tác dụng phụ lên LP lành mạnh, vì hạn chế khoảng giá hẹp cũng làm giảm hiệu quả sử dụng vốn của những người tham gia không có ý đồ xấu."));

// ===== 7 =====
body.push(H1("7. Tiến độ hiện tại và lộ trình"));
body.push(P("Đã hoàn thành: nền tảng CLMM ở mức đủ để cài đặt, bao gồm quan hệ giữa vốn, khoảng giá và liquidity, vai trò của phép đổi biến căn bậc hai, và hiệu ứng pha loãng phí; đọc và phân tích đầy đủ bài báo tham chiếu, bao gồm mô hình cân bằng, quy trình đo lường trên chuỗi và các giới hạn tự nhận của các tác giả; xác định khoảng trống nghiên cứu và lựa chọn hướng cải tiến."));
body.push(P("Lộ trình tiếp theo được chia thành bốn giai đoạn, sắp xếp sao cho luôn tồn tại một sản phẩm hoàn chỉnh ở mọi thời điểm và phần rủi ro cao nhất nằm ở cuối:"));
body.push(T(["Giai đoạn","Nội dung","Sản phẩm"],
  [["1","Động cơ một tick, ba lớp tác nhân, bốn chỉ số đo lường","Tái lập được cuộc tấn công, đạt bộ tiêu chuẩn kiểm định ở mục 6.3"],
   ["2","Quét tham số trợ cấp σ và trần Q","Bản đồ ba vùng thiết kế, xác định vị trí ngưỡng khả thi bằng thực nghiệm"],
   ["3","Mở rộng động cơ lên nhiều tick, cài đặt phần thưởng nhận biết khoảng giá","Kết quả đánh giá biện pháp phòng thủ, là phần đóng góp mới của đề tài"],
   ["4","Tùy nguồn lực: bộ phát hiện bất thường trực tuyến, hoặc quét chi phí hiệu dụng c_V","Kết quả bổ sung"]],
  [1200,4300,3500]));
body.push(gap());
body.push(P("Câu hỏi nghiên cứu cuối cùng mà đề tài hướng tới được phát biểu như sau: với một chương trình khuyến khích có tham số cho trước, cơ chế phân bổ phí nhận biết khoảng giá làm giảm thiệt hại của LP và lợi nhuận của kẻ tấn công ở mức nào, và cái giá phải trả về hiệu quả sử dụng vốn của những người tham gia lành mạnh là bao nhiêu."));

const doc = new Document({
  numbering: { config: [ { reference: "bul", levels: [ { level: 0, format: LevelFormat.BULLET,
      text: "•", alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 640, hanging: 320 } } } } ] } ] },
  sections: [{
    properties: { page: { margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    footers: { default: new Footer({ children: [ new Paragraph({ alignment: AlignmentType.CENTER,
      children: [ new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 20 }) ] }) ] }) },
    children: body
  }]
});

Packer.toBuffer(doc).then(b => { fs.writeFileSync("Bao_cao_lan_2.docx", b);
  console.log("OK", b.length, "bytes"); });
