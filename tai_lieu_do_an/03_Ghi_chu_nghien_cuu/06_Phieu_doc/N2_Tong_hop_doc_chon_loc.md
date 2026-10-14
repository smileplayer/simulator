# Nhóm 2 — Đọc chọn lọc (11 bài)

Đọc ngày 10/10/2026: tóm tắt, phần đóng góp, các định nghĩa / kết quả chính (tìm theo từ khóa trong toàn văn) và phần kết luận / giới hạn. **Không** đọc hết từng bài. Mỗi bài có: nội dung chính → dùng vào đâu trong đồ án → câu trích gợi ý.

Văn bản trích (pypdf, đúng thứ tự cột) để tra lại nằm trên máy ở `~/t2/` của phiên bash (không nằm trong thư mục đồ án; tạo lại bằng pypdf nếu cần).

---

## A. Đo lường thiệt hại / lợi nhuận của LP — dùng trực tiếp cho phần B (metrics)

### 1. Milionis, Moallemi, Roughgarden, Zhang — *Automated Market Making and Loss-Versus-Rebalancing* (arXiv 2208.06046; bản trong thư mục là v6 ghi "current version 03/05/2026" — nội dung đã viết lại so với bản 2022, khi trích nên ghi rõ phiên bản)
- **Chính:** so sánh LP với **danh mục tái cân bằng** giao dịch cùng lượng nhưng ở giá thị trường. `LVR_t = R_t − V_t` (R: giá trị danh mục tái cân bằng, V: giá trị bể); `LVR_t = ∫ ℓ(σ_s, P_s) ds` với `ℓ(σ,P) = σ²P²/2 · |x*'(P)|` ≥ 0 — LVR luôn không âm, không giảm, bằng đúng lợi nhuận của arbitrageur. Bản mới (v6) đóng khung lại thành phân rã lợi nhuận LP = phần **beta** (rủi ro thị trường) + phần **alpha** (phí − lỗ cho arbitrageur); trên bể Uniswap v2 ETH-USDC > 99,991% phương sai lợi nhuận LP đến từ beta.
- **Ví dụ 4 (vị thế v3 một khoảng):** `ℓ(σ,P) = Lσ²√P / 4` — bằng với v2 cùng L, nhưng giá trị vị thế nhỏ hơn nên **LVR trên mỗi đô-la → ∞ khi khoảng hẹp lại**. Con số mẫu: σ = 5%/ngày → bể v2 mất ≈ σ²/8 = 3,125 bp/ngày.
- **Dùng cho đồ án:** (i) giải thích vì sao vị thế một tick của nạn nhân cực kỳ nhạy với biến động (LVR/đô-la lớn) → nền lý thuyết cho thiệt hại nạn nhân ở pha Attack/Post; (ii) cân nhắc báo thêm thiệt hại nạn nhân **"so với tái cân bằng"** bên cạnh "so với giữ token" để tách phần do rủi ro thị trường; (iii) Trotti et al. dẫn rằng với một giao dịch đơn, price impact ≡ LVR.
- **Câu trích:** *LVR [Milionis et al.] đo khoản lỗ của LP cho arbitrageur so với danh mục tái cân bằng; với vị thế thanh khoản tập trung, LVR trên mỗi đô-la vốn tăng không giới hạn khi khoảng giá hẹp lại.*

### 2. Heimbach, Schertenleib, Wattenhofer — *Risks and Returns of Uniswap V3 Liquidity Providers* (AFT 2022)
- **Chính:** công thức giải tích cho **tổn thất tạm thời (IL)** của vị thế v3; IL **tăng nhanh hơn** khi thanh khoản tập trung. Phân tích dữ liệu các bể lớn: lợi nhuận và rủi ro vị thế khác nhau cực lớn ngay trong cùng bể; bể ổn định có chiến lược đơn giản có lãi nhưng lãi nhỏ; lãi lớn chỉ đạt được khi chấp nhận rủi ro cao và quản lý chủ động → "cuộc chơi của người chuyên nghiệp, LP nhỏ lẻ khó có cơ hội". Tương quan biến động – khối lượng > 0,75 trong một bể nhưng không giữa các bể.
- **Dùng cho đồ án:** định nghĩa IL chuẩn để so sánh với số đo thiệt hại nạn nhân; lập luận "nạn nhân là LP nhỏ lẻ không đủ tinh vi" của bài gốc có hậu thuẫn thực nghiệm.
- **Câu trích:** *Heimbach et al. chỉ ra tổn thất tạm thời tăng nhanh hơn khi thanh khoản càng tập trung và lợi nhuận cao trên v3 đòi hỏi quản lý chủ động, khiến LP nhỏ lẻ chịu bất lợi.*

### 3. Fritsch & Canidio — *Measuring Arbitrage Losses and Profitability of AMM Liquidity* (WWW 2024 Companion; arXiv 2404.05803) — bài gốc trích (Ref 27)
- **Chính:** đo LVR trên nhiều bể Uniswap v2/v3 lớn: **lỗ cho arbitrageur vượt phí kiếm được** ở nhiều bể lớn nhất; **bể v2 có lãi cho LP thụ động hơn bể v3 tương ứng**; block nhanh hơn (100 ms vs 12 s) giảm LVR 20–70% tùy cặp. Phương pháp: giả định bể luôn được tái cân bằng về giá thị trường mỗi block.
- **Dùng cho đồ án:** bằng chứng LP thụ động trên v3 vốn đã thiệt → nạn nhân dễ bị hút bởi lợi suất trợ cấp cao; cách đo "phí − LVR" là mẫu tính **lãi ròng của LP** trong metrics.
- **Câu trích:** *Fritsch và Canidio đo được rằng trên nhiều bể Uniswap lớn, lỗ cho arbitrageur vượt phí của LP, và bể v3 kém sinh lời cho LP thụ động hơn bể v2.*

---

## B. Định vị cuộc tấn công trong bức tranh tấn công DeFi

### 4. Zhou, Xiong, Ernstberger, Chaliasos, Wang, Wang, Qin, Wattenhofer, Song, Gervais — *SoK: Decentralized Finance (DeFi) Attacks* (IEEE S&P 2023)
- **Chính:** khung tham chiếu **5 tầng** (mạng NET, đồng thuận CON, hợp đồng thông minh SC, giao thức PRO, phụ trợ AUX) + mô hình đe dọa theo mục tiêu / hiểu biết / năng lực; 77 bài học thuật, 30 báo cáo audit, 181 sự cố (04/2018–04/2022), tổng thiệt hại ≥ 3,24 tỷ USD. Sự cố tầng SC 42%, PRO 40%; công cụ phòng thủ chỉ phủ 52% loại sự cố PRO. Tầng PRO có mục **"cơ chế khuyến khích"** (airdrop token quản trị cho LP) như một bề mặt tấn công. 56% tấn công không nguyên tử → có thời gian cứu.
- **Bài gốc trích bài này** (Ref 57).
- **Dùng cho đồ án:** đặt tấn công do khuyến khích vào **tầng PRO — thiết kế khuyến khích**, không phải lỗi hợp đồng; **không nguyên tử, kéo dài nhiều ngày** → có "cửa sổ giải cứu" → lý lẽ cho cảnh báo rủi ro / phát hiện sớm (GĐ2, GĐ4).
- **Câu trích:** *Theo khung tham chiếu của Zhou et al., tấn công thanh khoản do khuyến khích thuộc tầng giao thức (thiết kế cơ chế khuyến khích) và không nguyên tử — kéo dài nhiều ngày — khác các tấn công flash-loan nguyên tử.*

### 5. Ma & Crapis — *The Cost of Permissionless Liquidity Provision in Automated Market Makers* (arXiv 2402.18256, Ethereum Foundation, 2024)
- **Chính:** trò chơi N LP thụ động đối xứng + trader co giãn / không co giãn. **Quy tắc chia phí pro-rata khiến LP cạnh tranh gửi thanh khoản thừa** → nhiều vốn chịu lựa chọn bất lợi (LVR) hơn mức tối ưu. **Price of anarchy (trên lợi nhuận LP) = O(N)** — tổn thất phúc lợi tăng tuyến tính theo số LP; nhưng tính cả trader co giãn thì PoA tổng = O(1) (thanh khoản thừa có lợi cho trader). Thiết kế AMM giảm cường độ arbitrage trên mỗi đơn vị thanh khoản giúp trader nhưng **không** giúp LP.
- **Dùng cho đồ án:** cùng gốc "chia phí pro-rata gây cạnh tranh có hại" như nghịch lý JIT và tường một tick; củng cố rằng **thay đổi quy tắc chia phí** (range-aware) là đòn bẩy thiết kế đúng chỗ. Cũng nhắc: đánh giá biện pháp phải tách phúc lợi LP và phúc lợi trader — đúng như bộ chỉ số tách từng bên.
- **Câu trích:** *Ma và Crapis chứng minh quy tắc chia phí pro-rata khiến các LP thụ động cạnh tranh cung cấp thanh khoản thừa, với tổn thất phúc lợi của LP tăng tuyến tính theo số LP.*

---

## C. Farmer và trợ cấp — hiểu tác nhân thứ ba

### 6. Messias, Yaish, Livshits — *Airdrops: Giving Money Away Is Harder Than It Seems* (bản 07/2025)
- **Chính:** đo 9 airdrop lớn trên Ethereum/L2: tới **65,75% (Lido), 58,67% (1inch), 48,21% (Optimism)** token bị bán ngay trong 1 bước sau khi nhận; nguyên nhân chính là **"airdrop farmer"** tối ưu hóa điều kiện nhận thưởng mà không đóng góp. Case Arbitrum: phí giao dịch tăng tạm thời rồi giảm, số giao dịch / địa chỉ giảm. Khuyến nghị: thưởng tỷ lệ với chi phí, tiêu chí tinh hơn, airdrop nhiều vòng, "lockdrop".
- **Dùng cho đồ án:** bằng chứng thực nghiệm rằng **farmer phản ứng tối ưu với luật thưởng và bán ngay** — biện hộ cho farmer agent tối ưu `U_T` và cho biện pháp **trả thưởng trễ** (≈ lockdrop) ở RQ2.
- **Câu trích:** *Messias et al. cho thấy phần lớn token airdrop bị bán ngay sau khi nhận, do các farmer tối ưu hóa điều kiện nhận thưởng mà không tạo hoạt động thực.*

### 7. Yaish & Livshits — *TierDrop: Harnessing Airdrop Farmers for User Growth* (2024)
- **Chính:** mô hình hai nền tảng cạnh tranh, hai tầng người dùng (thật / farmer); **có lúc tối ưu doanh thu khi cố ý thưởng một phần cho farmer** (farmer tạo hoạt động → hiệu ứng mạng), kể cả khi lọc được farmer miễn phí. Airdrop cố định dễ thua lỗ khi farmer tạo nhiều sybil; **chia theo tỷ lệ ngân sách giới hạn tổn thất**. Kết quả tổng quát cho "mọi cơ chế khuyến khích dựa trên hoạt động".
- **Giả định quan trọng:** farmer **không gây hại cho người khác** ngoài việc lấy phần thưởng.
- **Dùng cho đồ án:** bài gốc cho thấy chính giao dịch của farmer là kênh hút LP nạn nhân rồi gây biến động → phá giả định trên. Đặt TierDrop để **nói rõ khác biệt**: nhóm đo ngoại ứng của farmer lên LP. Ý "ngân sách tỷ lệ giới hạn tổn thất" ↔ biện pháp **trần thưởng** `Q`.
- **Câu trích:** *TierDrop lập luận nền tảng có thể hưởng lợi từ việc thưởng cho farmer vì họ tạo hoạt động; phân tích này giả định farmer không gây ngoại ứng cho người tham gia khác — giả định không còn đúng khi hoạt động của farmer diễn ra trong một bể CLMM có tường thanh khoản của kẻ tấn công.*

### 8. Gogol, Schneider, Tessone, Livshits — *Liquidity Fragmentation or Optimization? Analyzing AMMs Across Ethereum and Rollups* (arXiv 2410.10324, 2025)
- **Chính:** tối ưu Lagrange phân bổ thanh khoản giữa Ethereum và L2 lấy staking làm mốc; ở cân bằng lợi suất LP hội tụ về lãi staking. **Độ co giãn khối lượng theo TVL:** trên chuỗi lâu đời (Ethereum, Arbitrum, Optimism) TVL tăng **không** kéo khối lượng tăng; chuỗi mới (Base, ZKsync) co giãn dương. Bể Ethereum bị "thừa vốn", thường lãi thấp hơn staking; > 66% thanh khoản Ethereum nên chuyển sang L2/staking.
- **Dùng cho đồ án:** ủng hộ giả định nền "khối lượng không tự tăng theo thanh khoản" → khối lượng tăng vọt trong vụ tấn công là do **trợ cấp**, không do tường làm bể sâu hơn. Dùng khi thiết kế luồng lệnh nền (không cho khối lượng nền phụ thuộc mạnh vào L) và khi giải thích dấu hiệu "Attack > 5× nền".
- **Câu trích:** *Gogol et al. ước lượng rằng trên các chuỗi lâu đời, tăng TVL không đi kèm tăng khối lượng giao dịch.*

---

## D. Simulator và phát hiện — phương pháp

### 9. Urusov, Berezovskiy, Yanovich — *Backtesting Framework for Concentrated Liquidity Market Makers on Uniswap V3* (Blockchain: Research and Applications, 2024)
- **Chính:** backtester CLMM dùng **mô hình tham số xấp xỉ phân bố thanh khoản** để ước phần thưởng (phí) của bể; dữ liệu 2023 nhiều loại bể (altcoin, stablecoin, USDC/ETH, nhiều mức phí); **sai số ước phần thưởng < 1%**. Có phần nền toán CLMM (IL theo chiều giá). Hướng tiếp: ước doanh thu LP và chiến lược động tối ưu.
- **Dùng cho đồ án:** tiền lệ backtester có kiểm định sai số với dữ liệu thật → có thể trích **bên cạnh** Tarantelli (vì Tarantelli là bản tự đăng). Không có tác nhân chiến lược, không trợ cấp.
- **Câu trích:** *Urusov et al. xây backtester cho Uniswap v3 với phân bố thanh khoản xấp xỉ tham số, ước phần thưởng của bể với sai số dưới 1% trên dữ liệu 2023.*

### 10. Chaudhary & Pinna — *A multi-asset, agent-based approach applied to DeFi lending protocol modelling* (2022)
- **Chính:** ABM nhiều tài sản cho giao thức cho vay (0VIX): mô phỏng thanh lý theo biến động giá thật (COVID 20/02/2020) và giả lập; quét tham số giao thức (LTV thanh lý, thưởng thanh lý); kết luận rủi ro vỡ nợ < 0,1% kể cả khi biến động tăng 10×. **Giới hạn tự nêu:** người dùng thụ động, không tái phân bổ danh mục; chỉ chạy ≤ 1 ngày.
- **Dùng cho đồ án:** thêm một tiền lệ "ABM để chọn tham số giao thức DeFi" (cùng StableSims); giới hạn "tác nhân thụ động" của họ minh họa đúng khoảng trống A (thiếu tác nhân chiến lược).
- **Câu trích:** *Chaudhary và Pinna dùng mô phỏng tác nhân để quét tham số thanh lý của một giao thức cho vay, nhưng giả định người dùng thụ động.*

### 11. RajabiNekoo, Rasoul, Farhadi, Zamanifar — *SILS: Strategic Influence on Liquidity Stability and Whale Detection in Concentrated-Liquidity DEXs* (preprint 07/2025)
- **Chính:** xác định LP "cá voi" theo **tác động chức năng** thay vì quy mô vốn: hồ sơ thanh khoản có trọng số thời gian mũ (ETWL) + phát hiện bất thường không giám sát + **LSIS** — chỉ số **phản thực** đo mức suy giảm thị trường (biến động giá) nếu LP đó rút. Phát hiện được "cá voi ngủ đông nhưng then chốt" mà phương pháp cũ bỏ sót. Ứng dụng: lớp oracle bảo vệ, tín hiệu cho trader. Hướng tiếp: khả năng mở rộng (chi phí tính toán cao), tối ưu tham số.
- **Không** có bối cảnh khuyến khích hay tấn công; preprint, chưa phản biện.
- **Dùng cho đồ án:** gần nhất với ý "phát hiện tường trước khi rút" (GĐ4, nếu làm). LSIS ≈ "nếu tường `L_A` rút thì giá trượt bao nhiêu" — có thể tính trực tiếp trong simulator như một **chỉ báo cảnh báo rủi ro** cho RQ2.
- **Câu trích:** *SILS định nghĩa tầm quan trọng của một LP bằng chỉ số phản thực về mức mất ổn định nếu LP đó rút thanh khoản; khung này chưa được áp dụng cho bối cảnh thanh khoản do trợ cấp.*

---

## Tóm tắt dùng nhanh khi viết Related Work

| Đoạn trong Related Work | Bài nhóm 2 dùng |
|---|---|
| Thiệt hại của LP thụ động trên CLMM | Milionis (LVR), Heimbach (IL), Fritsch & Canidio (LVR > phí) |
| Quy tắc chia phí pro-rata gây cạnh tranh có hại | Ma & Crapis (+ Capponi et al., Tang et al. ở nhóm 1) |
| Farmer và thiết kế khuyến khích | Messias et al., TierDrop (+ izumi ở nhóm 1) |
| Khối lượng do trợ cấp chứ không do độ sâu | Gogol et al. |
| Vị trí trong phân loại tấn công DeFi | Zhou et al. SoK |
| Simulator / ABM cho DeFi | Urusov et al., Chaudhary & Pinna (+ Tarantelli, StableSims ở nhóm 1) |
| Phát hiện LP có tác động hệ thống | SILS |
