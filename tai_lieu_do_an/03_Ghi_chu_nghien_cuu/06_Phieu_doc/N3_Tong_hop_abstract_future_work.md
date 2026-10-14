# Nhóm 3 — Chỉ đọc tóm tắt + hướng tiếp theo / giới hạn (39 bài)

Đọc ngày 10/10/2026: trích tóm tắt và đoạn kết luận / thảo luận / "future work" từ toàn văn (pypdf), kết hợp đợt quét 04/10 (`du_lieu_tho/scan_*.txt`). Mỗi bài: **một dòng nội dung**, **một dòng hướng mở / giới hạn**, **cách dùng** trong đồ án. "Ref n" = số thứ tự trong danh mục tham khảo của bài gốc (Lu et al.); "—" = bài gốc không trích.

Nguyên tắc khi viết Related Work: nhóm này chỉ cần **trích gộp** theo đoạn (một câu cho cả cụm), không phân tích từng bài.

---

## 1. Nền tảng AMM / CLMM (thư mục 01)

| Bài | Nội dung (1 dòng) | Hướng mở / giới hạn | Dùng ở đâu |
|---|---|---|---|
| Adams et al. 2021 — *Uniswap v3 Core* (whitepaper) — — | Đặc tả CLMM: tick, √P, L, feeGrowthOutside/Inside, vị thế `(owner, tickLower, tickUpper)`. | — | Trích khi định nghĩa CLMM; **tài liệu kỹ thuật chính của engine (A)**, mục 6 (tick, cross-tick, phí theo vị thế). |
| Adams et al. 2024 — *Uniswap v4 Core* — — | Hook trước/sau hành động của bể, singleton, flash accounting, phí động, "donate" cho LP trong khoảng. | — | Một câu: **hook v4 là kênh triển khai thực tế cho range-aware / trả thưởng trễ** mà không cần đổi lõi. |
| Fritsch 2021 — *Concentrated Liquidity in AMMs* (CCS DeFi Workshop) — Ref 26 | So sánh lợi nhuận phí trước/sau v3; đánh giá chiến lược CL cơ bản. | Thanh khoản tập trung làm **giảm mạnh doanh thu phí của LP thụ động**; người hưởng chính có thể là trader. Cần dữ liệu dài hơn. | Nền: LP thụ động thiệt trên v3. |
| Loesch et al. 2021 — *Impermanent Loss in Uniswap v3* — — | 17 bể v3 (43% TVL): tổng phí 199,3M USD < tổng IL 260,1M USD → LP gộp lại thua giữ token 60,8M USD; 49,5% LP có lợi nhuận âm (số đã kiểm toàn văn). | **IL lấn át phí**; LP > 1 tháng: IL ≈ 1,1× phí, LP ≤ 1 ngày: 1,8× phí; chỉ LP trong-block (flash) không lỗ. | Nền: vì sao LP nhỏ lẻ dễ bị hút bởi lợi suất trợ cấp cao. |
| Xu, Paruch, Cousaert, Feng 2021 — *SoK: DEX with AMM* (ACM CSUR 2023) — Ref 55 | Khung trạng thái chung cho AMM; so sánh Uniswap/Balancer/Curve/DODO; phân loại rủi ro & tấn công. | Mở rộng phân loại bảo mật AMM. | Trích khi giới thiệu AMM. |
| Bergault et al. 2022 — *AMM: Mean-Variance Analysis of LPs Payoffs* — — | So LP với giữ tài sản theo khung trung bình–phương sai; AMM có oracle cải thiện hiệu quả. | Oracle phải thiết kế kỹ để không mở vector tấn công mới. | Không cần trích; có thể một câu về đánh giá hiệu quả LP. |
| Adams et al. 2024 — *Layer 2 be or Layer not 2 be* — — | v3 trên L2: gas rẻ, block nhanh → LP hiệu quả vốn hơn, nhiều arbitrage hơn. | Block 2 s có thể còn quá dài. | Không cần trích (bài gốc trên BSC). |
| Asef & Bamakan 2024 — *From x·y=k to Uniswap Hooks* — — | Tổng quan so sánh DEX (Uniswap, Curve, Balancer), hook v4. | Nghiên cứu cơ hội / mối đe dọa của hook. | Không cần trích. |

## 2. Chiến lược LP — học tăng cường / tối ưu (thư mục 02)

*Lưu ý: chữ "reward" trong các bài này là phần thưởng của học tăng cường, không phải trợ cấp.*

| Bài | Nội dung | Hướng mở / giới hạn | Dùng ở đâu |
|---|---|---|---|
| Bar-On & Mansour 2023 — *Online Learning Approach* — — | Bài toán chọn khoảng giá như học trực tuyến phần thưởng không ngẫu nhiên; thuật toán Exponential Weights đảm bảo cận dưới phần thưởng. | Mô hình phí / gas chính xác hơn. | Gộp một câu "LP tối ưu đơn lẻ". |
| Cartea, Drissi, Monga 2023 — *Predictable Loss and Optimal Liquidity Provision* (SIAM J. Fin. Math 2024) — — | Chiến lược dạng đóng: độ rộng khoảng phụ thuộc lợi nhuận bể, "predictable loss" (PL) và rủi ro tập trung; dữ liệu v3 cho thấy LP thực tế thường lỗ. | Giả định tái định vị liên tục, phí chia theo kích thước bể ngẫu nhiên; mở rộng độ lệch khoảng. | Một câu: **độ rộng tối ưu cân bằng phí vs rủi ro tập trung** — nền cho GĐ3. PL ≈ LVR. |
| Zhang, Chen, Yang 2023 — *DRL for Uniswap v3* — — | Dueling DDQN chọn thời điểm & độ rộng, kèm phòng hộ; lãi hơn baseline 9–69%. | Không xét vị thế khoảng tick tùy ý (đã ghi ở khoảng trống B). | Gộp "LP học tăng cường". |
| Urusov et al. 2025 — *Dynamic Liquidity Provision … CLMMs* — — | Dựng lại trạng thái thanh khoản lịch sử từ swap (sai số ~2%); τ-reset tối ưu bằng ML; τ vừa phải tốt nhất. | Nếu nhiều LP dùng cùng tham số tối ưu → rủi ro ổn định; hướng: lý thuyết trò chơi mean-field / mô phỏng tác nhân (khoảng trống A). | Trích câu hướng tiếp theo cho khoảng trống A. |
| Chionas, Kleitsikas, Leonardos 2026 — *RL Perspective* — — | Bài toán điều khiển xung, RL cho chính sách diễn giải được; nén đuôi trái PnL. | **Hướng tiếp: cạnh tranh đa tác nhân giữa các LP không đồng nhất**, phí động. | Trích cho khoảng trống A. |

## 3. Liquidity mining / airdrop (thư mục 03)

| Bài | Nội dung | Hướng mở / giới hạn | Dùng ở đâu |
|---|---|---|---|
| Liu & Zhu 2022 — *Fighting Sybils in Airdrops* — — | Phát hiện tài khoản sybil qua đồ thị giao dịch, hoạt động DApp giống nhau, mẫu chuyển token đều đặn. | Thiếu nhãn chuẩn; bot thủ công khó phân biệt. | Một câu nếu nói về farmer dùng nhiều ví. |
| Xu & Feng 2022 — *Survey of Yield Farming Protocols* (IEEE TNSM) — Ref 53 | Yield farming là tầng tổng hợp trên DEX/lending; mô phỏng tham số các chiến lược; đòn bẩy khuếch đại lãi/lỗ theo giá token quản trị. | — | Trích khi định nghĩa liquidity mining / yield farming. |
| Vozarik et al. 2026 — *Gasp* (rollup DEX) — — | DEX dạng rollup chuyên dụng; **thưởng theo thời gian nắm giữ với đường cong tiệm cận** khuyến khích cam kết dài hạn. | Tài liệu dự án, không có đánh giá. | Một câu: tiền lệ thực tế của **thưởng phụ thuộc thời gian / trả thưởng trễ** (RQ2). |

**Tài liệu web trong danh mục nhưng chưa có PDF** (cần lấy để trích đúng): Paradigm 2021 *Liquidity Mining on Uniswap v3*; Merkl docs (Angle Labs); Gauntlet *Uniswap Liquidity Mining Analysis* (2023) và *Arbitrum LTIPP Retro* (2024); Optimism *Retrospective Funding Analysis: Uniswap V3 Liquidity Incentives* (2023); FAQ Binance Alpha Points (Ref 1–2 bài gốc); PancakeSwap trading rewards; veAERO rewards.

## 4. Tấn công DeFi và MEV (thư mục 05)

| Bài | Nội dung | Hướng mở / giới hạn | Dùng ở đâu |
|---|---|---|---|
| Daian et al. 2019 — *Flash Boys 2.0* (IEEE S&P 2020) — Ref 18 | Bot arbitrage trên DEX, đấu giá gas ưu tiên (PGA), khái niệm MEV, rủi ro đồng thuận. | Gộp nhiều địa chỉ của cùng thực thể để lại cho sau. | Trích gộp "MEV và giao dịch đối nghịch". |
| Qin et al. 2020 — *Flash Loans for Fun and Profit* (FC 2021) — Ref 42 | Tấn công nguyên tử bằng flash loan; ROI > 500.000%; tối ưu tham số tấn công. | Tự động hóa mô hình hành động DeFi. | Đối chiếu: **khác tấn công do khuyến khích (không nguyên tử, nhiều ngày)**. |
| Zhou et al. 2020 — *High-Frequency Trading on DEX* (sandwich, IEEE S&P 2021) — Ref 56 | Hình thức hóa sandwich; LP cũng có thể sandwich; thế lưỡng nan slippage mặc định. | Hiệu ứng block mồ côi để lại. | Trích gộp MEV; "victim" ở đây là trader, không phải LP. |
| Qin, Zhou, Gervais 2021 — *Quantifying BEV* (IEEE S&P 2022) — Ref 41 | Đo giá trị trích xuất được (sandwich, thanh lý, arbitrage) trong 32 tháng; rủi ro miner fork. | — | Trích gộp MEV. |
| Torres, Camino, State 2021 — *Frontrunner Jones* (USENIX Sec 2021) — Ref 46 | Đo ba kiểu frontrunning (displacement, insertion, suppression) trên 11M block; ~200K vụ, 18,41M USD. | Heuristic có thể bỏ sót. | Trích gộp MEV. |
| Capponi, Jia, Wang 2023 — *Private Transaction Pools* (ePrint 2023/1461) — Ref 11 | Pool riêng chỉ loại được frontrunning khi rủi ro cao; validator giữ rent. | Giải pháp hợp đồng vs giao thức. | Không cần (trừ khi bàn về Jia và nhóm tác giả). |
| Li et al. 2023 — *DeFi MEV in Flashbots Bundle* (CCS 2023) — Ref 37 | ActLifter / ActCluster nhận diện hành động DeFi trong bundle; phát hiện 17 loại MEV mới. | Relay không công khai bundle. | Không cần; tham khảo nếu cần nhận diện hành động từ log. |
| Liu et al. 2024 — *I Experienced More than 10 DeFi Scams* — — | Phỏng vấn (14) + khảo sát (493) người dùng DeFi: nạn nhân vẫn tiếp tục chấp nhận rủi ro, hành vi gần cờ bạc. | Nhóm "nạn nhân chiến lược" chấp nhận rủi ro có tính toán. | Một câu: **nạn nhân có thể quay lại** → ủng hộ victim thích nghi chạy theo lợi suất; cảnh báo rủi ro có thể kém hiệu quả (RQ2). |
| Wen et al. 2024 — *FORAY* (CCS 2024) — Ref 51 | Tổng hợp tấn công cho lỗi logic sâu trong giao thức DeFi bằng DSL tài chính. | Thêm loại lỗi logic. | Không cần (lỗi hợp đồng, không phải thiết kế khuyến khích). |
| Müller et al. 2026 — *Cost of Manipulation in AMM-Based Oracles* — — | Chi phí tối thiểu để kéo oracle AMM một hệ số; trung vị trọng số thanh khoản tối ưu max-min. | Mở rộng thời gian giữ lệch giá (dwell time). | Một câu: thanh khoản sâu tăng chi phí thao túng — ngược lại, **tường rút đi làm chi phí thao túng sụp** (liên hệ cú xả). |

## 5. Thao túng thị trường (thư mục 06)

| Bài | Nội dung | Hướng mở / giới hạn | Dùng ở đâu |
|---|---|---|---|
| Kamps & Kleinberg 2018 — *To the Moon* (Crime Science) — Ref 33 | Định nghĩa pump-and-dump crypto, phát hiện bằng bất thường giá/khối lượng. | Dữ liệu 20 ngày, theo giờ. | Trích gộp "thao túng". |
| Xu & Livshits 2019 — *Anatomy of a Pump-and-Dump* (USENIX Sec 2019) — Ref 54 | 412 vụ P&D qua Telegram; mô hình dự đoán đồng bị pump. | — | Trích gộp; **so sánh pha**: P&D (pump → dump) vs tấn công (dựng tường → rút → xả). |
| La Morgia et al. 2020 — *P&D Real-Time Detection* (ICCCN) — Ref 36 | Phát hiện P&D thời gian thực. | Một số nhóm có pha "pre-pump" làm lộ. | Trích gộp. |
| Cong et al. 2021 — *Crypto Wash Trading* (Mgmt Sci 2023) — Ref 15 | Kiểm định thống kê (Benford, làm tròn, đuôi phân phối): sàn không quản lý wash trade trung bình > 70% khối lượng. | — | Một câu: **khối lượng bị thổi phồng** — liên hệ farmer giao dịch để lấy trợ cấp. |
| Victor & Weintraud 2021 — *Wash Trading on DEX* (WWW 2021) — Ref 48 | Wash trading trên IDEX/EtherDelta: ≥ 159M USD; > 30% token bị wash. | Tham số bảo thủ → cận dưới. | Trích gộp. |
| Cernera et al. 2022 — *Token Spammers, Rug Pulls, SniperBots* (USENIX Sec 2023) — Ref 12 | ~60% token sống < 1 ngày; "1-day rug pull" lãi ~240M USD (chủ yếu BSC); sniper bot. | Thiếu một phần token từ giao dịch nội bộ. | Trích gộp; liên hệ: **rút thanh khoản là hành vi gây hại phổ biến** (rug pull), tấn công trong bài gốc là biến thể có trợ cấp. |

## 6. Simulator (thư mục 07)

| Bài | Nội dung | Hướng mở / giới hạn | Dùng ở đâu |
|---|---|---|---|
| Chitra et al. 2019 — *ABM of Blockchain Protocols (Kadena Chainweb)* — — | Mô phỏng tác nhân hợp lý kinh tế và Byzantine để ước độ khó kinh tế của tấn công đồng thuận. | Chưa có selfish mining, withholding. | Một câu tiền lệ: **ABM để định lượng an ninh dưới động cơ kinh tế** (cùng StableSims). |

## 7. Phát hiện bất thường (thư mục 08)

| Bài | Nội dung | Hướng mở / giới hạn | Dùng ở đâu |
|---|---|---|---|
| Wu et al. 2021 — *DeFiRanger* (IEEE TDSC 2023) — Ref 52 | Khôi phục ngữ nghĩa DeFi từ trace, phát hiện thao túng giá trực tiếp / gián tiếp. | Thêm hành động (vay), thêm mẫu tấn công. | Trích gộp "phát hiện"; mẫu cho luật nhận diện sự kiện. |
| Yaremus et al. 2025 — *Rug Pulls on TON* — — | Gradient boosting phát hiện rug pull trong 5 phút đầu; định nghĩa TVL-based AUC ≤ 0,891; idle-based recall cao. | Thêm đặc trưng xã hội; backtest lịch sử. | Khoảng trống D: phát hiện theo TVL cho token mới, không cho tường có trợ cấp. |
| Li et al. 2026 — *Catching the Rug (Solana)* — — | 6,4M token; phần lớn memecoin có dấu hiệu rug pull trong 1 giờ; XGBoost tốt nhất. | **Chưa đủ để triển khai thật**; hiệu năng giảm mạnh khi chuyển nền tảng. | Khoảng trống D. |
| Shoaei et al. 2026 — *LROO Rug Pull Detector* — — | Dữ liệu 1.000 dự án gán tay, đặc trưng on-chain + OSINT căn đúng thời điểm, **chống rò rỉ dữ liệu tương lai**. | Chỉ EVM; OSINT không ổn định; độ trễ nhãn. | Khoảng trống D + **cảnh báo phương pháp** cho GĐ4 (nếu làm): tách thời gian huấn luyện / kiểm tra. |

## 8. Nền khác của bài gốc (thư mục 09)

| Bài | Nội dung | Dùng ở đâu |
|---|---|---|
| Chen et al. 2019 — *Survey on Ethereum Systems Security* (ACM CSUR 2020) — Ref 13 | 44 lỗ hổng, 26 tấn công, 47 phòng thủ theo kiến trúc 4 tầng (số theo toàn văn); thiếu định nghĩa hình thức thuộc tính an ninh. | Không cần trích (bài gốc trích làm nền). |
| Feist et al. 2019 — *Slither* (WETSEB) — Ref 24 | Phân tích tĩnh Solidity qua SlithIR. | Không cần (lỗi mã, không phải khuyến khích). |

---

## Đoạn gộp gợi ý cho Related Work

> **Tấn công kinh tế trên DEX.** Các nghiên cứu về MEV đã đo lường frontrunning, sandwich và arbitrage trên DEX [Daian 2020; Zhou 2021; Qin 2022; Torres 2021], cũng như các tấn công nguyên tử dùng flash loan [Qin 2021]. Thao túng thị trường crypto gồm pump-and-dump [Kamps 2018; Xu 2019; La Morgia 2020], wash trading [Cong 2023; Victor 2021] và rug pull [Cernera 2023], với nhiều công cụ phát hiện [Wu 2023; Yaremus 2025; Li 2026; Shoaei 2026]. Khác các dạng trên, tấn công thanh khoản do khuyến khích không nguyên tử, kéo dài nhiều ngày và khai thác thiết kế trợ cấp chứ không phải lỗi hợp đồng.
>
> **Chiến lược LP đơn lẻ.** Một dòng nghiên cứu tối ưu độ rộng và thời điểm tái cân bằng cho một LP bằng điều khiển tối ưu [Cartea 2024], học trực tuyến [Bar-On 2023] hoặc học tăng cường [Zhang 2023; Urusov 2025; Chionas 2026]; các bài này giả định LP không ảnh hưởng đến người khác và tự nêu cạnh tranh đa tác nhân là hướng mở.
