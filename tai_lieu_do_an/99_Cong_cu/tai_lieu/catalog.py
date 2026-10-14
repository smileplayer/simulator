# -*- coding: utf-8 -*-
# Danh muc tai lieu. prio: 3 = doc ngay, 2 = nen doc, 1 = tham khao khi can
import json, re

AX = lambda i: f"https://arxiv.org/pdf/{i}"
AXL = lambda i: f"https://arxiv.org/abs/{i}"

CATS = [
 ("01_Nen_tang_AMM_CLMM", "Nền tảng AMM và CLMM", "Cơ chế gốc mà engine của simulator phải cài đặt, và các mô hình chi phí của LP."),
 ("02_Chien_luoc_LP_va_ly_thuyet_tro_choi", "Chiến lược LP và lý thuyết trò chơi", "LP chọn lượng và độ rộng khoảng giá thế nào — nền lý thuyết cho victim agent, nhất là ở GĐ3."),
 ("03_Liquidity_mining_va_incentive", "Liquidity mining và thiết kế khuyến khích", "Các cơ chế thưởng đã có, kể cả thưởng theo khoảng giá — đây là nhóm prior art trực tiếp của hướng cải tiến."),
 ("04_JIT_va_vi_the_sieu_hep", "JIT liquidity và vị thế siêu hẹp", "Cùng nguyên thủy với cuộc tấn công: vị thế một tick và pha loãng phí của LP. Bài gốc không trích dẫn nhóm này."),
 ("05_Tan_cong_DeFi_va_MEV", "Tấn công DeFi và MEV", "Khung phân loại tấn công kinh tế trong DeFi, để đặt cuộc tấn công này vào đúng chỗ."),
 ("06_Thao_tung_thi_truong", "Thao túng thị trường", "Pump-and-dump, wash trading, rug pull — các hình thái thao túng gần với cuộc tấn công."),
 ("07_Simulator_va_phuong_phap_danh_gia", "Simulator và phương pháp đánh giá", "Simulator CLMM đã có và tiền lệ dùng mô phỏng tác nhân để đánh giá tham số khuyến khích."),
 ("08_Phat_hien_bat_thuong", "Phát hiện bất thường", "Phát hiện rút thanh khoản và thao túng — nền cho hướng anomaly detector (GĐ4)."),
 ("09_Tham_khao_nen_khac", "Tham khảo nền khác của bài gốc", "Các tài liệu bài gốc trích dẫn để làm nền rộng, ít liên quan trực tiếp đến hướng của bạn."),
]

P = []
def add(cat, prio, year, authors, title, venue, why, pdf=None, link=None, ref=None, fname=None):
    P.append(dict(cat=cat, prio=prio, year=year, authors=authors, title=title, venue=venue,
                  why=why, pdf=pdf, link=link, ref=ref, fname=fname))

C1, C2, C3, C4, C5, C6, C7, C8, C9 = [c[0] for c in CATS]

# ---------------- 01 ----------------
add(C1,3,2021,"Adams, Zinsmeister, Salem, Keefer, Robinson","Uniswap v3 Core (whitepaper)","Uniswap Labs",
    "Đặc tả gốc của CLMM: tick, √P, liquidity, fee growth, cross-tick. Là bản thiết kế trực tiếp cho engine GĐ1.",
    pdf="https://app.uniswap.org/whitepaper-v3.pdf", link="https://app.uniswap.org/whitepaper-v3.pdf", fname="2021_Adams_Uniswap_v3_Core_whitepaper.pdf")
add(C1,1,2024,"Adams, Salem, Toda, et al.","Uniswap v4 Core (whitepaper)","Uniswap Labs",
    "Cơ chế hooks — nơi trong thực tế có thể cài thưởng nhận biết khoảng giá hoặc chống JIT.",
    pdf="https://app.uniswap.org/whitepaper-v4.pdf", link="https://app.uniswap.org/whitepaper-v4.pdf", fname="2024_Adams_Uniswap_v4_Core_whitepaper.pdf")
add(C1,3,2021,"Fritsch","Concentrated Liquidity in Automated Market Makers","ACM CCS DeFi Workshop 2021",
    "Mô hình hóa toán học CLMM và lựa chọn khoảng giá của LP. Bài gốc trích dẫn.", pdf=AX("2110.01368"), link=AXL("2110.01368"), ref=26)
add(C1,2,2021,"Xu, Paruch, Cousaert, Feng","SoK: Decentralized Exchanges (DEX) with Automated Market Maker (AMM) Protocols","ACM Computing Surveys 2023",
    "Tổng quan hệ thống về AMM — tra cứu nền tảng khi viết báo cáo.", pdf=AX("2103.12732"), link=AXL("2103.12732"), ref=55)
add(C1,3,2022,"Milionis, Moallemi, Roughgarden, Zhang","Automated Market Making and Loss-Versus-Rebalancing","arXiv",
    "Thước đo chuẩn cho chi phí của LP (LVR). Dùng để mô hình hóa phần chi phí trong c_V cho có cơ sở.", pdf=AX("2208.06046"), link=AXL("2208.06046"))
add(C1,2,2021,"Loesch, Hindman, Richardson, Welch","Impermanent Loss in Uniswap v3","arXiv",
    "Đo impermanent loss thực tế trên v3 — số liệu hiệu chỉnh chi phí LP.", pdf=AX("2111.09192"), link=AXL("2111.09192"))
add(C1,3,2022,"Heimbach, Schertenleib, Wattenhofer","Risks and Returns of Uniswap V3 Liquidity Providers","ACM AFT 2022",
    "Hành vi LP thật trên v3: dải hẹp lãi cao hơn nhưng rủi ro cao hơn. Dữ liệu để kiểm định victim agent.", pdf=AX("2205.08904"), link=AXL("2205.08904"))
add(C1,2,2024,"Fritsch, Canidio","Measuring Arbitrage Losses and Profitability of AMM Liquidity","WWW 2024 Companion",
    "Lỗ do arbitrage vượt phí ở nhiều bể v3. Cơ sở cho giả định chi phí LP. Bài gốc trích dẫn.", pdf=AX("2404.05803"), link=AXL("2404.05803"), ref=27)
add(C1,2,2022,"Hashemseresht, Pourpouneh","Concentrated Liquidity Analysis in Uniswap V3","ACM CCS DeFi Workshop 2022",
    "Phân tích thanh khoản tập trung trên v3. Bài gốc trích dẫn. Không tìm thấy bản mở.", link="https://doi.org/10.1145/3560832.3563438", ref=31)
add(C1,1,2022,"Bergault, Bertucci, Bouba, Guéant","Automated Market Makers: Mean-Variance Analysis of LPs Payoffs and Design of Pricing Functions","arXiv",
    "Phân tích lợi nhuận và rủi ro của LP theo khung trung bình–phương sai.", pdf=AX("2212.00336"), link=AXL("2212.00336"))
add(C1,1,2024,"Asef, Bamakan","From x*y=k to Uniswap Hooks: A Comparative Review of Decentralized Exchanges","arXiv",
    "Tổng quan tiến hóa DEX từ v2 tới hooks v4.", pdf=AX("2410.10162"), link=AXL("2410.10162"))
add(C1,1,2024,"Gogol, Schneider, Tessone","Liquidity Fragmentation or Optimization? Analyzing AMMs Across Ethereum and Rollups","arXiv",
    "Hành vi LP và lợi nhuận trên các rollup.", pdf=AX("2410.10324"), link=AXL("2410.10324"))
add(C1,1,2024,"Adams et al.","Layer 2 be or Layer not 2 be: Scaling on Uniswap v3","arXiv",
    "Hành vi LP v3 trên Layer 2.", pdf=AX("2403.09494"), link=AXL("2403.09494"), fname="2024_Adams_Layer_2_be_or_Layer_not_2_be_Scaling_on_Uniswap_v3.pdf")

# ---------------- 02 ----------------
add(C2,3,2024,"Tang, El-Azouzi, Lee, Chan, Fanti","Game Theoretic Liquidity Provisioning in Concentrated Liquidity Market Makers","POMACS 2025",
    "LP chọn cả lượng và khoảng giá; cân bằng kiểu waterfilling; hơn 65% LP thật chỉ dùng một vị thế. Nền lý thuyết cho GĐ3. Có code CLMM-game. Bài gốc trích dẫn.",
    pdf=AX("2411.10399"), link=AXL("2411.10399"), ref=45)
add(C2,2,2021,"Fan, Marmolejo-Cossío, Moroz, et al.","Strategic Liquidity Provision in Uniswap v3","arXiv",
    "Chiến lược LP tối ưu trên v3 theo kỳ vọng giá.", pdf=AX("2106.12033"), link=AXL("2106.12033"))
add(C2,2,2023,"Cartea, Drissi, Monga","Decentralised Finance and Automated Market Making: Predictable Loss and Optimal Liquidity Provision","arXiv",
    "Mô hình LP tối ưu và khái niệm predictable loss — tham khảo khi đặt chi phí cho victim.", pdf=AX("2309.08431"), link=AXL("2309.08431"))
add(C2,1,2023,"Bar-On, Mansour","Uniswap Liquidity Provision: An Online Learning Approach","arXiv",
    "LP như bài toán học trực tuyến — gợi ý cho victim thích nghi.", pdf=AX("2302.00610"), link=AXL("2302.00610"))
add(C2,1,2023,"Zhang, Chen, Yang","Adaptive Liquidity Provision in Uniswap V3 with Deep Reinforcement Learning","arXiv",
    "Học tăng cường cho LP.", pdf=AX("2309.10129"), link=AXL("2309.10129"))
add(C2,1,2026,"Chionas, Kleitsikas, Leonardos, et al.","Concentrated Liquidity Provision: a Reinforcement Learning Perspective","arXiv",
    "Học tăng cường cho LP thanh khoản tập trung (2026).", pdf=AX("2608.19389"), link=AXL("2608.19389"))
add(C2,1,2025,"Urusov, Berezovskiy, Krestenko, et al.","Dynamic Liquidity Provision in Decentralized Markets: Strategy Optimization and Performance Evaluation in CLMMs","arXiv",
    "Tối ưu chiến lược LP động và cách đánh giá hiệu năng.", pdf=AX("2505.15338"), link=AXL("2505.15338"))

# ---------------- 03 ----------------
add(C3,3,2021,"Yin (izumi Finance)","On Liquidity Mining for Uniswap v3","arXiv",
    "Thưởng theo bin giá; chứng minh cân bằng Nash là dàn thanh khoản theo phân bố thưởng; cảnh báo dồn thưởng một bin khiến LP dồn hết vào đó. Tiền lệ học thuật gần nhất của range-aware reward.",
    pdf=AX("2108.05800"), link=AXL("2108.05800"))
add(C3,3,2021,"Adams (Paradigm)","Liquidity Mining on Uniswap v3","Paradigm blog",
    "Thiết kế liquidity mining chuẩn cho v3: chia theo active liquidity, KHÔNG phụ thuộc độ rộng khoảng. Baseline để so sánh.",
    link="https://www.paradigm.xyz/2021/05/liquidity-mining-on-uniswap-v3")
add(C3,3,2023,"Angle Labs","Merkl — Liquidity Provisioning Incentives","Sản phẩm / tài liệu",
    "Hạ tầng phân phối thưởng có tùy chọn theo khoảng giá và loại trừ vị thế siêu hẹp. Bằng chứng range-aware reward đã chạy thực tế; bài gốc không trích dẫn.",
    link="https://merkl.xyz/solutions/concentrated-liquidity")
add(C3,2,2022,"Xu, Feng","Reap the Harvest on Blockchain: A Survey of Yield Farming Protocols","IEEE TNSM 2022",
    "Khảo sát các giao thức yield farming. Bài gốc trích dẫn.", pdf=AX("2210.04194"), link=AXL("2210.04194"), ref=53)
add(C3,2,2023,"Messias, Yaish, Livshits","Airdrops: Giving Money Away Is Harder Than It Seems","arXiv",
    "Hành vi của người săn airdrop — rất gần với points farmer trong cuộc tấn công.", pdf=AX("2312.02752"), link=AXL("2312.02752"))
add(C3,2,2026,"Vozarik, Nowakowski, Siddiqui, et al.","Gasp: A DeFi Application Specific Rollup as a Consolidation Layer for All Assets","arXiv",
    "Thưởng LP theo thời gian nắm giữ để chống mercenary capital — liên quan biện pháp trả thưởng trễ.", pdf=AX("2607.16052"), link=AXL("2607.16052"))
add(C3,2,2023,"Gauntlet","Uniswap Liquidity Mining Analysis","Báo cáo công nghiệp",
    "Đánh giá chương trình incentive theo khối lượng tăng thêm so với incentive bỏ ra — gần với chỉ số chi phí trợ cấp của bạn.",
    link="https://www.gauntlet.xyz/resources/uniswap-liquidity-mining-analysis")
add(C3,1,2024,"Gauntlet","Arbitrum LTIPP Program Retro","Báo cáo công nghiệp",
    "Hồi cứu một chương trình incentive lớn: thanh khoản có ở lại sau khi hết thưởng không.",
    link="https://www.gauntlet.xyz/resources/arbitrum-ltipp-program-results")
add(C3,1,2023,"Optimism Governance","Retrospective Funding Analysis: Uniswap V3 Liquidity Incentives","Diễn đàn quản trị",
    "Phân tích hồi cứu incentive cho các bể v3 trên Optimism.",
    link="https://gov.optimism.io/t/retrospective-funding-analysis-uniswap-v3-liquidity-incentives/6212")
add(C3,1,2022,"Liu, Zhu","Fighting Sybils in Airdrops","arXiv", "Chống tài khoản ảo khi phát thưởng.", pdf=AX("2209.04603"), link=AXL("2209.04603"))
add(C3,1,2024,"Yaish, Livshits","TierDrop: Harnessing Airdrop Farmers for User Growth","arXiv", "Thiết kế thưởng có tính đến farmer.", pdf=AX("2407.01176"), link=AXL("2407.01176"))
for r,t in [(1,"Binance alpha 2.0, 2025."),(2,"Frequently asked questions on binance alpha points, 2025."),
            (3,"Pancakeswap trading rewards program, 2025."),(4,"veaero rewards program, 2025.")]:
    add(C3,1,2025,"—",t,"Tài liệu chương trình", "Tài liệu chính thức của chương trình thưởng mà bài gốc dùng làm bối cảnh. Tra trên trang chính thức của sàn.", ref=r)
for r,a,t,v in [(6,"Allen, Berg, Lane","Why airdrop cryptocurrency tokens?","Journal of Business Research 2023"),
                (23,"Fan, Min, Wu, Cai","Altruistic and profit-oriented: Making sense of roles in web3 community from airdrop perspective","CHI 2023"),
                (30,"Han, Yan, Liang, Yang","How can incentive mechanisms and blockchain benefit with each other? A survey","ACM Computing Surveys 2022"),
                (16,"Cong, Li, Wang","Token-based platform finance","Journal of Financial Economics 2022"),
                (28,"Gan, Tsoukalas, Netessine","Decentralized platforms: Governance, tokenomics, and ICO design","Management Science 2023"),
                (22,"Drasch, Fridgen, Manner-Romberg, Nolting, Radszuwill","The token's secret: The two-faced financial incentive of the token economy","Electronic Markets 2020"),
                (35,"Kim, Laskowski, Zargham, et al.","Token economics in real life: Cryptocurrency and incentives design for Insolar's blockchain network","Computer 2021")]:
    add(C3,1,int(re.search(r"(19|20)\d\d",v).group(0)),a,t,v,"Nền về tokenomics và thiết kế khuyến khích. Bài gốc trích dẫn. Chưa tìm bản mở — tra Google Scholar theo tên bài.", ref=r)

# ---------------- 04 ----------------
add(C4,3,2023,"Xiong, Wang, Cui, Knottenbelt, Huth","Demystifying Just-in-Time (JIT) Liquidity Attacks on Uniswap V3","BRAINS 2023 / IACR ePrint 2023/973",
    "36.671 vụ JIT trong 20 tháng; LP hiện hữu bị pha loãng trung bình 85%. Cùng nguyên thủy vị thế siêu hẹp + pha loãng phí; con số là mốc hiệu chỉnh simulator. Bài gốc không trích dẫn.",
    pdf="https://eprint.iacr.org/2023/973.pdf", link="https://eprint.iacr.org/2023/973", fname="2023_Xiong_Demystifying_JIT_Liquidity_Attacks_on_Uniswap_V3.pdf")
add(C4,3,2025,"Trotti, Tang, El-Azouzi, et al.","Strategic Analysis of Just-In-Time Liquidity Provision in Concentrated Liquidity Market Makers","AFT 2025",
    "Mô hình hình thức JIT ở cấp giao dịch trong CLMM: tác động giá và phân bổ phí. Cùng nhóm tác giả với bài lý thuyết trò chơi [45].",
    pdf=AX("2509.16157"), link=AXL("2509.16157"))
add(C4,2,2023,"Capponi, Jia, Zhu","The Paradox of Just-in-Time Liquidity in Decentralized Exchanges: More Providers Can Sometimes Mean Less Liquidity","arXiv",
    "JIT có thể làm thanh khoản thụ động rút đi. Ruizhe Jia là đồng tác giả bài gốc, nhưng bài gốc không trích dẫn bài này.",
    pdf=AX("2311.18164"), link=AXL("2311.18164"))
add(C4,2,2024,"Ma, Crapis","The Cost of Permissionless Liquidity Provision in Automated Market Makers","arXiv",
    "Chi phí của việc cho phép LP tự do vào ra — JIT gây hại cho LP thụ động.", pdf=AX("2402.18256"), link=AXL("2402.18256"))

# ---------------- 05 ----------------
add(C5,3,2022,"Zhou, Xiong, Ernstberger, et al.","SoK: Decentralized Finance (DeFi) Attacks","IEEE S&P 2023",
    "Khung phân loại tấn công DeFi. Dùng để định vị cuộc tấn công này là tấn công kinh tế, không phải lỗi mã. Bài gốc trích dẫn.",
    pdf=AX("2208.13035"), link=AXL("2208.13035"), ref=57)
add(C5,2,2019,"Daian, Goldfeder, Kell, et al.","Flash Boys 2.0: Frontrunning, Transaction Reordering, and Consensus Instability in DEXs","IEEE S&P 2020",
    "Bài khởi đầu về MEV. Bài gốc trích dẫn.", pdf=AX("1904.05234"), link=AXL("1904.05234"), ref=18)
add(C5,2,2021,"Qin, Zhou, Gervais","Quantifying Blockchain Extractable Value: How dark is the forest?","IEEE S&P 2022",
    "Đo giá trị có thể bóc tách. Bài gốc trích dẫn.", pdf=AX("2101.05511"), link=AXL("2101.05511"), ref=41)
add(C5,2,2020,"Qin, Zhou, Livshits, Gervais","Attacking the DeFi Ecosystem with Flash Loans for Fun and Profit","FC 2021",
    "Tấn công kinh tế bằng flash loan. Bài gốc trích dẫn.", pdf=AX("2003.03810"), link=AXL("2003.03810"), ref=42)
add(C5,2,2026,"Müller, Moumeni, Messaoudi, et al.","Cost of Manipulation in AMM-Based Oracles","arXiv",
    "Chi phí thao túng giá trong AMM — liên quan việc tính lợi nhuận của kẻ tấn công.", pdf=AX("2606.03548"), link=AXL("2606.03548"))
add(C5,1,2020,"Zhou, Qin, Ferreira Torres, Le, Gervais","High-Frequency Trading on Decentralized On-Chain Exchanges","IEEE S&P 2021",
    "Sandwich attack. Bài gốc trích dẫn.", pdf=AX("2009.14021"), link=AXL("2009.14021"), ref=56)
add(C5,1,2021,"Ferreira Torres, Camino, State","Frontrunner Jones and the Raiders of the Dark Forest","USENIX Security 2021",
    "Đo frontrunning trên Ethereum. Bài gốc trích dẫn.", pdf=AX("2102.03347"), link=AXL("2102.03347"), ref=46)
add(C5,1,2023,"Li, Li, He, et al.","Demystifying DeFi MEV Activities in Flashbots Bundle","ACM CCS 2023",
    "17 loại MEV mới trong bundle. Bài gốc trích dẫn.", pdf=AX("2312.01091"), link=AXL("2312.01091"), ref=37)
add(C5,1,2023,"Capponi, Jia, Wang","Do Private Transaction Pools Mitigate Frontrunning Risk?","IACR ePrint 2023/1461",
    "Kênh giao dịch riêng và frontrunning. Bài gốc trích dẫn.",
    pdf="https://eprint.iacr.org/2023/1461.pdf", link="https://eprint.iacr.org/2023/1461", ref=11, fname="2023_Capponi_Do_Private_Transaction_Pools_Mitigate_Frontrunning_Risk.pdf")
add(C5,1,2024,"Wen, Liu, Song, et al.","FORAY: Towards Effective Attack Synthesis against Deep Logical Vulnerabilities in DeFi Protocols","ACM CCS 2024",
    "Tự động tổng hợp tấn công DeFi. Bài gốc trích dẫn.", pdf=AX("2407.06348"), link=AXL("2407.06348"), ref=51)
add(C5,1,2024,"Liu, Huh, Han, et al.","I Experienced More than 10 DeFi Scams: On DeFi Users' Perception of Security Breaches and Countermeasures","arXiv",
    "Cảm nhận rủi ro của người dùng DeFi — liên quan biện pháp cảnh báo rủi ro.", pdf=AX("2406.15709"), link=AXL("2406.15709"))
add(C5,1,2025,"Capponi, Jia, Wang","Maximal extractable value and allocative inefficiencies in public blockchains","Journal of Financial Economics 2025",
    "MEV và phân bổ kém hiệu quả. Bài gốc trích dẫn.", link="https://papers.ssrn.com/abstract=3997796", ref=9)
add(C5,1,2023,"Capponi, Jia, Wang","Blockchain private pools and price discovery","AEA Papers and Proceedings 2023",
    "Bài gốc trích dẫn. Chưa tìm bản mở.", ref=10)
add(C5,1,2022,"Wang, Zuest, Yao, Lu, Wattenhofer","Impact and User Perception of Sandwich Attacks in the DeFi Ecosystem","CHI 2022",
    "Nhận thức của người dùng về sandwich attack. Bài gốc trích dẫn.", link="https://doi.org/10.1145/3491102.3517585", ref=50)

# ---------------- 06 ----------------
add(C6,2,2018,"Xu, Livshits","The Anatomy of a Cryptocurrency Pump-and-Dump Scheme","USENIX Security 2019",
    "Cấu trúc một vụ pump-and-dump — hình thái thao túng gần nhất về logic dựng rồi xả. Bài gốc trích dẫn.", pdf=AX("1811.10109"), link=AXL("1811.10109"), ref=54)
add(C6,2,2022,"Cernera, La Morgia, Mei, Sassi","Token Spammers, Rug Pulls, and SniperBots: Tokens in Ethereum and BNB Smart Chain","USENIX Security 2023",
    "Rug pull và bot trên chính BSC — cùng chuỗi với dữ liệu bài gốc. Bài gốc trích dẫn.", pdf=AX("2206.08202"), link=AXL("2206.08202"), ref=12)
add(C6,2,2021,"Victor, Weintraud","Detecting and Quantifying Wash Trading on Decentralized Cryptocurrency Exchanges","WWW 2021",
    "Khối lượng ảo trên DEX. Giúp phân biệt wash trading với khối lượng do trợ cấp. Bài gốc trích dẫn.", pdf=AX("2102.07001"), link=AXL("2102.07001"), ref=48)
add(C6,1,2021,"Cong, Li, Tang, Yang","Crypto Wash Trading","Management Science 2023",
    "Wash trading trên sàn tập trung. Bài gốc trích dẫn.", pdf=AX("2108.10984"), link=AXL("2108.10984"), ref=15)
add(C6,1,2020,"La Morgia, Mei, Sassi, Stefa","Pump and Dumps in the Bitcoin Era: Real Time Detection of Cryptocurrency Market Manipulations","ICCCN 2020",
    "Phát hiện pump-and-dump thời gian thực. Bài gốc trích dẫn.", pdf=AX("2005.06610"), link=AXL("2005.06610"), ref=36)
add(C6,1,2018,"Kamps, Kleinberg","To the moon: defining and detecting cryptocurrency pump-and-dumps","Crime Science 2018",
    "Định nghĩa và phát hiện pump-and-dump. Bài gốc trích dẫn. Tạp chí truy cập mở.",
    pdf="https://crimesciencejournal.biomedcentral.com/counter/pdf/10.1186/s40163-018-0093-5.pdf",
    link="https://doi.org/10.1186/s40163-018-0093-5", ref=33, fname="2018_Kamps_To_the_moon_pump_and_dumps.pdf")
for r,a,t,v in [(21,"Dhawan, Putniņš","A new wolf in town? Pump-and-dump manipulation in cryptocurrency markets","Review of Finance 2023"),
                (40,"Niu, Li, Peng, Li","Unveiling wash trading in popular NFT markets","WWW 2024 Companion"),
                (5,"Aggarwal, Wu","Stock market manipulations","Journal of Business 2006"),
                (14,"Comerton-Forde, Putniņš","Stock price manipulation: Prevalence and determinants","Review of Finance 2014"),
                (17,"Cooper, Donaldson","A strategic analysis of corners and squeezes","JFQA 1998"),
                (32,"Jarrow","Market manipulation, bubbles, corners, and short squeezes","JFQA 1992"),
                (34,"Khwaja, Mian","Unchecked intermediaries: Price manipulation in an emerging stock market","Journal of Financial Economics 2005"),
                (47,"Van Bommel","Rumors","Journal of Finance 2003")]:
    add(C6,1,int(re.search(r"(19|20)\d\d",v).group(0)),a,t,v,"Lý thuyết thao túng thị trường kinh điển hoặc thực nghiệm. Bài gốc trích dẫn. Tạp chí trả phí — tra Google Scholar.", ref=r)

# ---------------- 07 ----------------
add(C7,3,2026,"Tarantelli","Constructing and Validating an Agent-Based Simulator for Uniswap v3 Concentrated Liquidity","Zenodo",
    "Simulator tác nhân cho v3, kiểm định trên 181 ngày dữ liệu mainnet (biến động mô phỏng 0,0301 so với thực 0,0292). Lấy phương pháp kiểm định làm chuẩn cho GĐ1. Không có incentive hay tấn công.",
    pdf="https://zenodo.org/records/21647967/files/main.pdf?download=1", link="https://zenodo.org/records/21647967",
    fname="2026_Tarantelli_Agent_Based_Simulator_Uniswap_v3.pdf")
add(C7,3,2022,"Kirillov, Chung","StableSims: Optimizing MakerDAO Liquidations 2.0 Incentives via Agent-Based Modeling","arXiv",
    "Tiền lệ phương pháp: dùng mô phỏng tác nhân để chọn tham số khuyến khích của một giao thức thật. Đúng khuôn đề tài của bạn.",
    pdf=AX("2201.03519"), link=AXL("2201.03519"))
add(C7,2,2024,"Urusov, Berezovskiy, Yanovich","Backtesting Framework for Concentrated Liquidity Market Makers on Uniswap V3","Blockchain: Research and Applications 2024",
    "Khung backtest cho CLMM — tham khảo cấu trúc engine và cách dùng dữ liệu thật.", pdf=AX("2410.09983"), link=AXL("2410.09983"))
add(C7,2,2022,"Chaudhary, Pinna","A multi-asset, agent-based approach applied to DeFi lending protocol modelling","arXiv",
    "Mô phỏng tác nhân để thử tham số giao thức DeFi.", pdf=AX("2211.08870"), link=AXL("2211.08870"))
add(C7,1,2019,"Chitra, Quaintance, Haber, Martino","Agent-Based Simulations of Blockchain protocols illustrated via Kadena's Chainweb","arXiv",
    "Mô phỏng tác nhân có tác nhân đối kháng để ước lượng chi phí tấn công.", pdf=AX("1904.12924"), link=AXL("1904.12924"))
add(C7,2,2025,"Tang et al.","CLMM-game (mã nguồn)","GitHub",
    "Mã phân tích đi kèm bài lý thuyết trò chơi [45]. Dùng để đối chiếu victim agent ở GĐ3.", link="https://github.com/WeizhaoT/CLMM-game")
add(C7,1,2023,"idrees535","Uniswap-V3-Simulator (mã nguồn)","GitHub", "Simulator v3 dựa trên TokenSpice.", link="https://github.com/idrees535/Uniswap-V3-Simulator")
add(C7,1,2021,"Aloe Labs","uniswap-simulator (mã nguồn)","GitHub", "Simulator v3 bằng Python.", link="https://github.com/aloelabs/uniswap-simulator")

# ---------------- 08 ----------------
add(C8,3,2025,"RajabiNekoo, Rasoul, Farhadi, et al.","SILS: Strategic Influence on Liquidity Stability and Whale Detection in Concentrated-Liquidity DEXs","arXiv",
    "Phát hiện LP có ảnh hưởng hệ thống và rút thanh khoản trong CLMM, kèm phân tích phản thực. Gần nhất với hướng anomaly detector.",
    pdf=AX("2507.19411"), link=AXL("2507.19411"))
add(C8,2,2021,"Wu, Yu, Wang, et al.","DeFiRanger: Detecting Price Manipulation Attacks on DeFi Applications","IEEE TDSC 2023",
    "Phát hiện thao túng giá. Bài gốc trích dẫn.", pdf=AX("2104.15068"), link=AXL("2104.15068"), ref=52)
add(C8,2,2025,"Yaremus, Li, Kalacheva, et al.","Detecting Rug Pulls in Decentralized Exchanges: Machine Learning Evidence from the TON Blockchain","arXiv",
    "Phát hiện sớm dựa trên TVL (rút thanh khoản đột ngột) — cùng dạng tín hiệu với việc tháo tường.", pdf=AX("2509.01168"), link=AXL("2509.01168"))
add(C8,1,2026,"Li, Kuznetsov, Yanovich, et al.","Catching the Rug: Early Prediction of Fraudulent Memecoins on Solana via Machine Learning","arXiv",
    "Dự đoán sớm rug pull trên Solana.", pdf=AX("2608.20271"), link=AXL("2608.20271"))
add(C8,1,2026,"Shoaei, Pishdar, Bag-Mohammadi","LROO Rug Pull Detector: A Leakage-Resistant Framework Based on On-Chain and OSINT Signals","arXiv",
    "Chú ý cách tránh rò rỉ dữ liệu tương lai khi huấn luyện detector — bài học phương pháp cho GĐ4.", pdf=AX("2603.11324"), link=AXL("2603.11324"))

# ---------------- 09 ----------------
add(C9,1,2019,"Chen, Pendleton, Njilla, Xu","A Survey on Ethereum Systems Security: Vulnerabilities, Attacks and Defenses","ACM Computing Surveys 2020",
    "Khảo sát an ninh Ethereum. Bài gốc trích dẫn.", pdf=AX("1908.04507"), link=AXL("1908.04507"), ref=13)
add(C9,1,2019,"Feist, Grieco, Groce","Slither: A Static Analysis Framework For Smart Contracts","WETSEB 2019",
    "Phân tích tĩnh hợp đồng. Bài gốc trích dẫn để đối lập với tấn công kinh tế.", pdf=AX("1908.09878"), link=AXL("1908.09878"), ref=24)
for r,a,t,v in [(7,"Atzei, Bartoletti, Cimoli","A survey of attacks on Ethereum smart contracts (SoK)","POST 2017"),
                (8,"Breidenbach, Cachin, et al.","Chainlink 2.0: Next steps in the evolution of decentralized oracle networks","Chainlink Labs 2021"),
                (19,"Das, Erwig, Faust, Loss, Riahi","The exact security of BIP32 wallets","ACM CCS 2021"),
                (20,"Das, Faust, Loss","A formal treatment of deterministic wallets","ACM CCS 2019"),
                (25,"Feng, Hitsch, Qin, et al.","DeFi auditing: Mechanisms, effectiveness, and user perceptions","FC 2023"),
                (29,"Guarnizo, Szalachowski","PDFS: Practical data feed service for smart contracts","ESORICS 2019"),
                (38,"Luu, Chu, Olickel, Saxena, Hobor","Making smart contracts smarter","ACM CCS 2016"),
                (39,"Mao, Dang, Wang, Zhang, Zhong","Solution probing attack against coin mixing based privacy-preserving crowdsourcing platforms","IEEE TDSC 2024"),
                (43,"Ruaro, Gritti, McLaughlin, et al.","Not your type! Detecting storage collision vulnerabilities in Ethereum smart contracts","NDSS 2024"),
                (44,"Si, Sharma, Wang","Understanding user-perceived security risks and mitigation strategies in the web3 ecosystem","CHI 2024"),
                (49,"Wang, Mao, Zhong","Solution probing attack against blockchain-based quality-aware crowdsourcing platforms","IEEE MASS 2022")]:
    add(C9,1,int(re.search(r"(19|20)\d\d",v).group(0)),a,t,v,"Nền rộng về an ninh blockchain mà bài gốc trích dẫn; ít liên quan trực tiếp. Tra Google Scholar nếu cần.", ref=r)

if __name__ == "__main__":
    import re
    for p in P:
        if p["pdf"] and not p["fname"]:
            first = p["authors"].split(",")[0].split("(")[0].strip().split()[-1]
            first = re.sub(r"[^A-Za-z\-]", "", first.encode("ascii","ignore").decode()) or "Anon"
            words = re.sub(r"[^A-Za-z0-9 ]", " ", p["title"]).split()
            p["fname"] = f"{p['year']}_{first}_" + "_".join(words[:9]) + ".pdf"
    json.dump(dict(cats=CATS, papers=P), open("catalog.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
    n_pdf = sum(1 for p in P if p["pdf"])
    print("tong:", len(P), "| co ban PDF mo:", n_pdf, "| chi link/tham chieu:", len(P)-n_pdf)
    refs = sorted(p["ref"] for p in P if p["ref"])
    print("ref cua bai goc da bao phu:", len(refs), "/ 57 ; thieu:", sorted(set(range(1,58))-set(refs)))
