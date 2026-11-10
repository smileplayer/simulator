# Kiểm độ bền RQ3 với LP tính rủi ro theo khoảng — kế hoạch

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Kiểm xem kết luận RQ3 ("chia phí theo độ rộng φ không bảo vệ được nạn nhân") còn đứng không khi nạn nhân chọn độ rộng, vị trí khoảng và vốn có tính thiệt hại sập kỳ vọng theo từng khoảng; kèm sửa chữ đoạn G (dòng tiền phạt) trong bài báo.

**Architecture:** Không đổi engine. Thêm một hàm chọn khoảng theo rủi ro trong `agents/do_rong.py`; bộ chạy `scenarios/run.py` dùng nó khi config có khóa `victim_rui_ro`, rồi đưa (w, vị trí, chi phí hiệu dụng) vào hai lớp nạn nhân đã có. Bộ quét GĐ3 thêm chế độ `--rui_ro`; lớp đo thêm bảng ghép cặp. Không có khóa mới thì mọi thứ chạy y như cũ.

**Tech Stack:** Python 3.11+, numpy, pandas, pytest (như repo).

**Spec:** quyết định trong phiên ngày 27–30/10/2026 (đánh giá gói `penalty_recipient_audit-tlmh-27102026` và `tlmh-30102026` của Hoàng); quyết định chốt 2, 3, 5, 6 trong `../CLAUDE.md`.

## Đức hỏi: làm gì, ảnh hưởng gì, cần đạt gì

### Làm gì

| Phần | Nội dung | Có chạy mô phỏng mới? |
|---|---|---|
| A | Sửa chữ đoạn G trong bài báo: giải thích dòng "nạn nhân −79, kẻ tấn công +0,6%" bằng tiền phạt của nạn nhân chảy vào tường (đã đo 27/10: trung vị 48% ở cấu hình giữ tường 168 giờ); trích audit RC2 của OpenZeppelin; thêm giới hạn "nạn nhân không tính phạt khi rút". | Không |
| B | Thêm nạn nhân "tính rủi ro theo khoảng" vào GĐ3, chạy lại một lưới GĐ3 thu gọn, so với nạn nhân cũ. | Có (Đức chạy, ước 1–2 giờ, đo lại bằng `--nhanh` ở Task B4) |

Mô hình rủi ro của Phần B (một tham số mới λ):

- Với một khoảng (w, vị trí d) tại giá P₀, một cú sập sâu δ làm 1 token1 vốn trong khoảng còn `V₁/C₁`; mất `m(w,d,δ) = 1 − V₁/C₁` (định giá ở giá sau sập, cùng cách `metrics.pnl.victim_loss`).
- Thiệt hại kỳ vọng `h(w,d) = Σ_δ π_δ · m(w,d,δ)`, prior công khai `δ ∈ {0,1; 0,2; 0,5}`, trọng số bằng nhau (bài gốc chỉ cho biết các vụ sập ≥ 10%).
- Chi phí hiệu dụng theo vốn: `c_eff(w,d) = c · [(1 − λ) + λ · h(w,d)/h(1,"tren")]`, với c = `c_V_von` hiện tại. λ = phần của c_V mà rủi ro sập chiếm ở vị thế một tick. λ = 0 ⇒ trùng nạn nhân cũ; ở (1, "tren") luôn có `c_eff = c` ⇒ không tính rủi ro hai lần (điểm Hoàng nêu).
- Nạn nhân chọn (w, d) tối đa `Π*(w,d) = (√(f·V) − √(c_eff·W/g))²` (0 nếu không vào), `g = φ(w)·ℓ(w,d)`, rồi chỉnh vốn mỗi bước như cũ với `c_von = c_eff(w*,d*)`.

### Ảnh hưởng

| Chỗ | Ảnh hưởng |
|---|---|
| `engine/` | Không đổi |
| Số liệu RQ1, RQ2, G, F, RQ3 cũ | Không đổi (khóa mới vắng ⇒ code cũ). Test hồi quy ở Task B2 chứng minh |
| `INTERFACE.md` | Thêm khóa config `victim_rui_ro` → ghi "ĐỔI INTERFACE" |
| Bài báo | A: đoạn G, Bảng G (chú thích), giới hạn. B: mục RQ3 thêm một đoạn + một bảng nhỏ, giới hạn (vi) sửa, có thể thêm 1 câu ở Kết luận. Giữ ≤ 20 trang |
| Kịch bản, giáo trình, tổng kết, SYNC | Cập nhật theo kết quả (luật 17/10) |
| `.pptx` | Không sửa, chờ chốt |
| Thời gian | Code ~1 buổi; Đức chạy 1–2 giờ; viết ~1 buổi. Xong trước 08/11, còn 2 tuần tới hạn 22/11 |

### Kết quả cần đạt

Kỹ thuật (bắt buộc):
1. Toàn repo qua test trên pandas 2.2.3 và 3.0.6 (320 cũ + test mới).
2. λ = 0 cho đúng (w, vị trí, c_von) và đúng log như nạn nhân cũ trên cùng config.
3. `tomtat_ruiro.csv` đủ 3.600 dòng; bảng `ket_qua/gd3/bang_ruiro/` sinh lại được bằng một lệnh.

Nghiên cứu (ghi trước khi chạy, ngưỡng do Claude đề xuất, Đức chốt trước Task B4):
- **R1 — RQ3 đứng:** với λ ∈ {0,5; 1}, ở α ≥ 1,5, lợi tăng thêm của kẻ tấn công (`dc_excess`, trung vị % ghép cặp so với α = 0 cùng λ) **không** giảm ≥ 25% ở ít nhất 4/6 vụ, cho cả hai loại nạn nhân → giữ kết luận, thêm "bền với nạn nhân tính rủi ro theo khoảng".
- **R2 — RQ3 phải thu hẹp:** có λ mà φ làm `dc_excess` giảm ≥ 25% ở ≥ 4/6 vụ → viết lại: φ có tác dụng khi LP định giá rủi ro theo khoảng, nêu điều kiện (λ, α, w₀, k).
- **R3 — rủi ro tự bảo vệ:** ở α = 0, λ > 0 đã làm `phan_duong_sap` hoặc `von_victim` giảm ≥ 25% so với λ = 0 → báo kênh "định giá rủi ro" riêng, tách khỏi tác dụng của φ.
- Mọi kết quả kèm CI bootstrap cặp; ghi rõ nạn nhân nằm ở biên lưới (w = 2.000 hoặc luôn "duoi") nếu xảy ra.

## Global Constraints

- Không sửa `engine/`. Không đổi giá trị mặc định nào của config cũ.
- Docstring tiếng Việt 1–2 dòng, ghi đơn vị (token1, tick, cửa sổ).
- Số thực `float`. Không thêm thư viện.
- Script chạy lâu ghi dần, bỏ lượt đã có, có `--nhanh` (luật repo).
- Commit chỉ khi Đức nói "chốt"; mỗi vai một commit; không `git add -A`.
- Bài báo: chạy `python 99_Cong_cu/soat_viet.py 02_Bao_cao_va_trinh_bay/bai_bao.tex`; ≤ 20 trang; 0 Overfull.

## Review Focus

- Nạn nhân không vào ở mọi khoảng (Π* = 0 khắp nơi): phải trả w = argmax g như `chon_w`, C = 0, không chia cho 0.
- Khoảng "duoi"/"tren" khi giá đúng ở biên tick: `h` phải hữu hạn, trong [0, 1].
- Trần động / cảnh báo (`c_V_hieu_luc`) cùng bật: hệ số cảnh báo phải nhân lên `c_eff`, không bị mất.
- λ ngoài [0, 1] hoặc prior rỗng: báo `ValueError`, không chạy âm thầm.
- Đọc lại `.meta.json` của lượt có rủi ro: khóa mới phải ghi được ra JSON.

---

## Phần A — sửa chữ đoạn G

### Task A1: Đoạn G, chú thích Bảng G, giới hạn

**Files:**
- Modify: `02_Bao_cao_va_trinh_bay/bai_bao.tex` (đoạn `\paragraph{Phạt rút sớm.}`, caption `tab:G`, giới hạn (ii), `\bibitem` mới `ozaudit2025`)
- Modify: `02_Bao_cao_va_trinh_bay/Kich_ban_slide_10_phut.md` (mục hỏi đáp), `giao_trinh/index.html` (bài 15/19), `04_Simulator/ket_qua/ban_nhap/muc7_ket_qua_RQ2.md`

- [ ] **Step 1:** Thêm 2–3 câu sau câu "Hai cách né cho sẵn đều hiệu quả…": khi tường giữ đủ cửa sổ, tiền phạt của nạn nhân thích nghi rút sớm được chia theo thanh khoản đang hoạt động, mà tường chiếm phần lớn; trung vị 48% (22/30 vụ có phạt, seed 0) chảy vào tường; đó là nguồn của dòng −79 / +0,6 trong Bảng G. Ở phat168/phat336 phần này nhỏ (trung vị 1–2%) vì nạn nhân chủ yếu rút sau khi tường đã rút.
- [ ] **Step 2:** Trích `\cite{ozaudit2025}` (OpenZeppelin, *Uniswap Hooks v1.1.0-rc.2 Audit*, 16/07/2025, mục Secondary Accounts) cho ý "người nhận tiền phạt có thể là kẻ tấn công".
- [ ] **Step 3:** Giới hạn (ii): thêm "nạn nhân không tính tiền phạt khi quyết định rút".
- [ ] **Step 4:** Chạy `soat_viet.py`, biên dịch `pdflatex` ×2. Kỳ vọng: ≤ 20 trang, `grep -c Overfull bai_bao.log` = 0.
- [ ] **Step 5:** Sửa kịch bản (một câu hỏi đáp), bản nháp mục 7, giáo trình; đăng lại giáo trình cùng link.

Số 48% / 1–2% lấy từ phép đo ngày 27/10 (`scratchpad/do_dong_phat.py`, 30 vụ × seed 0). Trước Step 1, chạy lại script đó trên `main` hiện tại để xác nhận số (≈ 1 phút).

---

## Phần B — nạn nhân tính rủi ro theo khoảng (RQ3)

### Task B1: Hàm thiệt hại sập và chọn khoảng theo rủi ro

**Files:**
- Modify: `04_Simulator/agents/do_rong.py`
- Test: `04_Simulator/tests/agents/test_rui_ro_khoang.py` (mới)

**Interfaces:**
- Produces:
  - `DO_SAP_PRIOR: tuple[float, ...] = (0.1, 0.2, 0.5)`
  - `VI_TRI: tuple[str, ...] = ("tren", "giua", "duoi")`
  - `mat_khi_sap(w: int, z: float, tick: int, vi_tri: str, delta: float) -> float` — phần vốn (token1 trên mỗi token1) mất khi giá giảm δ, định giá ở giá sau sập.
  - `h_rui_ro(w: int, z: float, tick: int, vi_tri: str, prior=DO_SAP_PRIOR) -> float` — trung bình đều của `mat_khi_sap` trên prior.
  - `c_hieu_dung(c: float, lam: float, w: int, z: float, tick: int, vi_tri: str, prior=DO_SAP_PRIOR) -> float`
  - `chon_khoang_rui_ro(f: float, V: float, W: float, c: float, lam: float, phi, z: float, tick: int, luoi=LUOI_W, vi_tri=VI_TRI, prior=DO_SAP_PRIOR) -> dict` trả `{w, vi_tri, c_eff, g, Pi, bang: [(w, vi_tri, g, c_eff, Π)]}`; hòa → Π, rồi g, rồi w nhỏ, rồi thứ tự trong `vi_tri`.

- [ ] **Step 1: Viết test hỏng**

```python
def test_c_hieu_dung_bang_c_o_mot_tick_tren():
    assert c_hieu_dung(0.002, 0.7, 1, Z0, 0, "tren") == pytest.approx(0.002)

def test_lam_0_khong_doi_chi_phi():
    for w in (1, 10, 200):
        for d in VI_TRI:
            assert c_hieu_dung(0.002, 0.0, w, Z0, 0, d) == pytest.approx(0.002)

def test_mat_khi_sap_trong_0_1_va_tang_theo_delta():
    for w in (1, 50, 2000):
        for d in VI_TRI:
            m = [mat_khi_sap(w, Z0, 0, d, x) for x in (0.1, 0.2, 0.5)]
            assert all(0.0 <= v <= 1.0 for v in m) and m[0] <= m[1] <= m[2]

def test_lam_0_chon_giong_chon_w_cu():
    phi = PhiLuyThua(2.0, 50)
    r = chon_khoang_rui_ro(F, V, W, C, 0.0, phi, Z0, 0, vi_tri=("giua",))
    assert r["w"] == chon_w(F, V, W, C, phi, Z0, tick=0, vi_tri="giua")["w"]

def test_khong_vao_o_dau_ca_tra_w_argmax_g():
    r = chon_khoang_rui_ro(F, V=1e-9, W=W, c=C, lam=0.5, phi=None, z=Z0, tick=0)
    assert r["Pi"] == 0.0 and r["w"] == 1

def test_lam_ngoai_khoang_bao_loi():
    with pytest.raises(ValueError):
        chon_khoang_rui_ro(F, V, W, C, 1.5, None, Z0, 0)
```

Hằng số test: `Z0 = sqrt_price_at_tick(0) * 1.0001 ** 0.25`, `F = 0.0025`, `V = 72_000.0`, `W = 4e8`, `C` = `c_V_von` của `co_so` (tính trong fixture như `quet_gd3.cau_hinh_gd3`).

- [ ] **Step 2:** `python -m pytest tests/agents/test_rui_ro_khoang.py -q` → FAIL (chưa có hàm).
- [ ] **Step 3:** Cài các hàm trên. `mat_khi_sap`: dùng `khoang_tick`, `amounts_for_liquidity` ở `z` và ở `z·√(1−δ)` với L = 1; `m = 1 − (b0·P₁ + b1)/(a0·P₀ + a1)`, cắt về [0, 1]. `chon_khoang_rui_ro`: duyệt `luoi × vi_tri`, `g = g_w(...)`, `C = C_V_sao(f, V, W, g, c_eff)`, `Π = Pi_V(...)`; λ ∉ [0, 1] hoặc prior rỗng → `ValueError`.
- [ ] **Step 4:** Test qua.

### Task B2: Nối vào bộ chạy, hồi quy λ = 0

**Files:**
- Modify: `04_Simulator/scenarios/run.py:207-218` (khối chọn `w_victim`, `vi_tri_v`, `c_von`)
- Modify: `04_Simulator/INTERFACE.md` (mục config GĐ3)
- Test: `04_Simulator/tests/agents/test_rui_ro_khoang.py`

**Interfaces:**
- Consumes: `chon_khoang_rui_ro` (Task B1).
- Produces: khóa config `victim_rui_ro = {"lam": float, "prior": [δ...] (tùy chọn)}`; meta thêm `victim_vi_tri_chon: str`, `victim_c_eff: float` (cùng `w_victim_chon` đã có).

- [ ] **Step 1: Viết test hỏng**

```python
VU = {v["id"]: v for v in to_hop_gd3()}          # scenarios.quet_gd3
cfg_gd3 = cau_hinh_gd3(VU["L27_16"], 2.0, 50, "omniscient")

def test_lam_0_log_trung_nan_nhan_cu():
    goc = run_frame(cfg_gd3, 0)
    moi = run_frame({**cfg_gd3, "victim_rui_ro": {"lam": 0.0}}, 0)
    pd.testing.assert_frame_equal(goc.drop(columns="seq"), moi.drop(columns="seq"))

def test_meta_ghi_lua_chon_rui_ro():
    df = run_frame({**cfg_gd3, "victim_rui_ro": {"lam": 0.5}}, 0)
    m = df.attrs["meta"]
    assert m["victim_vi_tri_chon"] in VI_TRI and m["victim_c_eff"] > 0
    json.dumps(m, default=lambda o: o.tolist())

def test_canh_bao_nhan_len_c_eff():
    a = run_frame({**cfg_gd3, "victim_rui_ro": {"lam": 0.5}}, 0).attrs["meta"]["victim_c_eff"]
    b = run_frame({**cfg_gd3, "victim_rui_ro": {"lam": 0.5}, "defense": {"name": "warn", "he_so": 2.0}}, 0).attrs["meta"]["victim_c_eff"]
    assert b == pytest.approx(2.0 * a)
```

(Ở test thứ nhất, nạn nhân cũ dùng `vi_tri="giua"`; khi λ = 0 hàm mới chỉ được duyệt `("giua",)` để trùng — bộ chạy truyền `vi_tri=(vi_tri_v,)` khi `lam == 0`.)

- [ ] **Step 2:** Chạy test → FAIL.
- [ ] **Step 3:** Trong `run.py`: nếu `cfg.get("victim_rui_ro")` và `w_victim == "tu_chon"`, gọi `chon_khoang_rui_ro(fee, V_ky_vong, W = L_A_eff·φ(w_A), c = c_von_goc, lam, phi, z0, tick0, luoi_w, vi_tri)`; đặt `w_victim`, `vi_tri_v`, `c_von = c_V_hieu_luc(c_eff, defense)`. Nạn nhân thích nghi cũng chọn khoảng theo `V_ky_vong` (luật thưởng công khai), còn vốn mỗi bước theo V̂ như cũ — ghi rõ trong docstring và INTERFACE.
- [ ] **Step 4:** Test qua; `python -m pytest -q` toàn repo qua (pandas 3.0.6), rồi chạy lại bằng venv pandas 2.2.3.
- [ ] **Step 5:** Ghi "ĐỔI INTERFACE" vào nhật ký `SYNC.md`.

### Task B3: Chế độ quét `--rui_ro`

**Files:**
- Modify: `04_Simulator/scenarios/quet_gd3.py`
- Test: `04_Simulator/tests/agents/test_rui_ro_khoang.py`

**Interfaces:**
- Produces: `LUOI_PHI_RR = [(0.0, 0)] + [(a, w0) for a in (1.5, 2.0, 3.0) for w0 in (10, 50, 200)]`; `LAM_RR = (0.0, 0.5, 1.0)`; `LUOI_W_RR = LUOI_W + (500, 1000, 2000)`; `KHOA_RR = ["scenario_id", "alpha", "w0", "lam", "victim_type", "seed"]`; cột kết quả thêm `lam`, `vi_tri_victim`, `c_eff`; file `ket_qua/gd3/tomtat_ruiro.csv`. Lệnh: `python -m scenarios.quet_gd3 --rui_ro [--seeds 10] [--nhanh]`.

- [ ] **Step 1:** Test hỏng: `danh_sach_viec(10, rui_ro=True)` có 6 × 10 × 3 × 2 × 10 = 3.600 phần tử; `--nhanh` cho 1 seed, 1 vụ.
- [ ] **Step 2:** FAIL → cài (dùng lại `dong_ket_qua`, `chi_so_victim`; ghi dần, bỏ khóa đã có) → PASS.
- [ ] **Step 3:** Chạy `--nhanh`, đo thời gian mỗi lượt, ước tổng; ghi vào `SYNC.md` "Chờ Đức chạy: …" kèm lệnh PowerShell:

```powershell
$env:PYTHONIOENCODING="utf-8"; python -m scenarios.quet_gd3 --rui_ro --seeds 10
```

### Task B4: Bảng ghép cặp và quyết định R1/R2/R3

**Files:**
- Modify: `04_Simulator/metrics/gd3.py`
- Create: `04_Simulator/metrics/chay_ruiro.py`
- Test: `04_Simulator/tests/metrics/test_gd3_ruiro.py` (mới)

**Interfaces:**
- Consumes: `tomtat_ruiro.csv` (Task B3).
- Produces: `bang_ruiro(df: pd.DataFrame, B: int = 2000) -> pd.DataFrame` với hai loại so sánh: (i) φ so với α = 0 cùng λ; (ii) λ so với λ = 0 cùng φ. Cột: `lam, alpha, w0, victim_type, chi_so, n_cap, hieu, pct, pct_lo, pct_hi`; chỉ số `dc_excess, von_victim, phan_duong_sap, vl_full`. `ket_luan_ruiro(bang) -> dict` trả số vụ (trên 6) đạt ngưỡng −25% cho R1/R2/R3. `python -m metrics.chay_ruiro` → `ket_qua/gd3/bang_ruiro/{ghep_cap.csv, ket_luan.json}`.

- [ ] **Step 1:** Test hỏng trên bảng giả 2 vụ × 2 seed (giá trị dựng tay): `pct` đúng, `ket_luan_ruiro` đếm đúng số vụ.
- [ ] **Step 2:** FAIL → cài (dùng `hieu_cap` và bootstrap phân cụm theo vụ như `bang_gd3`) → PASS.
- [ ] **Step 3:** Đức chốt ngưỡng R1/R2/R3 (−25%, ≥ 4/6 vụ) **trước** khi chạy lưới đầy đủ.
- [ ] **Step 4:** Sau khi Đức chạy xong: `python -m metrics.chay_ruiro`, đọc bằng pandas, báo kết luận R1/R2/R3 cùng vị trí lựa chọn của nạn nhân (tỷ lệ chọn w ≥ 500, tỷ lệ chọn "duoi").

### Task B5: Viết vào bài báo và các file trạng thái

**Files:** `bai_bao.tex` (mục RQ3, giới hạn (vi), có thể Kết luận), `Kich_ban_slide_10_phut.md`, `ket_qua/ban_nhap/muc8_ket_qua_RQ3.md`, `TONG_KET_DU_AN.md`, `SYNC.md`, `../CLAUDE.md`, `giao_trinh/index.html`.

- [ ] **Step 1:** Viết đoạn kết quả theo đúng nhánh R1/R2/R3 đã đạt; một bảng ≤ 8 dòng; không đổi số RQ3 cũ.
- [ ] **Step 2:** `soat_viet.py`, biên dịch ×2, ≤ 20 trang, 0 Overfull.
- [ ] **Step 3:** Cập nhật kịch bản, bản nháp, tổng kết, CLAUDE.md, giáo trình (đăng lại cùng link).
- [ ] **Step 4:** Chờ Đức "chốt": test toàn repo, commit theo vai ([C] agents/scenarios/INTERFACE, [B] metrics/ket_qua, [CH] SYNC/TONG_KET), push, sửa commit trong mục Mã nguồn của bài báo.
