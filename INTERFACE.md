# INTERFACE — hợp đồng giữa ba vai

> **Trạng thái: ĐÃ CHỐT ngày 14/10/2026** (vai C, Đức duyệt). Từ nay mọi thay đổi phải ghi "ĐỔI INTERFACE" trong nhật ký `SYNC.md`. Chỉ vai C sửa file này.

## 1. Quy ước chung

| Thứ | Quy ước |
|---|---|
| token0 = `x` | token alpha (token phụ, bị xả) |
| token1 = `y` | token định giá (USDT); **mọi giá trị tiền tính bằng token1** |
| Giá | `P` = token1 trên mỗi token0; `z = √P`; `P(i) = 1.0001^i` |
| Tick | số nguyên; `tick_spacing` mặc định 1 |
| Phí | `fee` = tỷ lệ (ví dụ `0.0025`), thu trên **token đi vào**, cộng dồn cho LP theo `feeGrowth` |
| Thời gian | bước nguyên `t = 0, 1, 2, …`; **1 bước = 1 giờ** (đã chốt). Thứ tự trong một bước theo cột `seq` — B dùng `seq` khi cần độ phân giải dưới 1 giờ (pha thu hoạch) |
| Số | `float` (không mô phỏng Q64.96) |
| Chủ sở hữu | chuỗi `"<vai>:<số>"`: `attacker:0`, `victim:3`, `farmer:12`, `bg:0` (giao dịch nền), `arb:0`, `platform` (bên trả trợ cấp). Vai = phần trước dấu `:` |
| Dấu lượng token | trong log, **dương = đi vào bể**, âm = ra khỏi bể (nhìn từ phía bể) |

## 2. Engine — `engine/pool.py` (vai A cài đặt)

```python
@dataclass
class Position:
    id: int
    owner: str
    tick_lower: int
    tick_upper: int          # tick_upper > tick_lower; độ rộng w = tick_upper - tick_lower
    liquidity: float

@dataclass
class SwapResult:
    amount_in: float         # lượng vào (đã gồm phí), token vào
    amount_out: float        # lượng ra, token ra
    fee: float               # phí, tính bằng token vào
    zero_for_one: bool       # True = bán token0 lấy token1 (giá giảm)
    sqrt_price_before: float
    sqrt_price_after: float
    tick_before: int
    tick_after: int
    ticks_crossed: int

class Pool:
    def __init__(self, fee: float, sqrt_price: float, tick_spacing: int = 1): ...
    # trạng thái đọc được
    fee: float                            # tỷ lệ phí (farmer cần để tính chi phí)
    sqrt_price: float
    tick: int
    liquidity: float                      # thanh khoản đang hoạt động L_active

    def mint(self, owner: str, tick_lower: int, tick_upper: int, liquidity: float) -> tuple[int, float, float]:
        """Thêm vị thế. Trả (position_id, amount0, amount1) phải nạp vào."""
    def burn(self, position_id: int, liquidity: float | None = None) -> tuple[float, float]:
        """Rút thanh khoản (None = rút hết). Trả (amount0, amount1) nhận về, CHƯA gồm phí."""
    def collect(self, position_id: int) -> tuple[float, float]:
        """Thu phí đã tích lũy của vị thế, trả (fee0, fee1), đặt lại về 0."""
    def swap(self, owner: str, zero_for_one: bool, amount_in: float | None = None,
             sqrt_price_limit: float | None = None) -> SwapResult:
        """Swap cross-tick. Cho amount_in, hoặc sqrt_price_limit (đi tới giá giới hạn), hoặc cả hai
        (dừng ở điều kiện đến trước). Hết thanh khoản thì dừng, không lặp vô hạn."""
    def quote_swap(self, zero_for_one: bool, amount_in: float | None = None,
                   sqrt_price_limit: float | None = None) -> SwapResult:
        """Như swap nhưng KHÔNG đổi trạng thái — farmer dùng để tính trượt giá MC(v)."""
    def position_amounts(self, position_id: int) -> tuple[float, float]:
        """(x, y) hiện nằm trong vị thế theo giá hiện tại, chưa gồm phí."""
    def fees_owed(self, position_id: int) -> tuple[float, float]:
        """Phí chưa thu (fee0, fee1)."""
    def positions(self, owner: str | None = None) -> list[Position]: ...
    def liquidity_at(self, tick: int) -> float:
        """Thanh khoản hoạt động nếu giá nằm ở tick này (để vẽ L(tick))."""
```

Mọi hàm đổi trạng thái (`mint`, `burn`, `collect`, `swap`) **ghi một sự kiện** vào `pool.log` (mục 4). Pool cần biết bước thời gian hiện tại: `pool.t` do bộ chạy kịch bản đặt.

**GĐ3 (để sau):** tham số `fee_weight: Callable[[int], float] | None` cho `Pool.__init__` — `φ(w)`; `None` = chia pro-rata như v3.

## 3. Tác nhân và bộ chạy — `agents/`, `scenarios/` (vai C cài đặt)

```python
class Agent(Protocol):
    owner: str
    def act(self, t: int, pool: Pool, market: "Market") -> None: ...

class Market(Protocol):
    def external_price(self, t: int) -> float:   # P_e(t), giá ngoài sàn, token1/token0
        ...

def run(config: dict, seed: int) -> "EventLog":   # scenarios/run.py
    """Chạy một kịch bản từ đầu tới cuối, trả về log sự kiện."""
```

Cấu hình kịch bản là `dict` (đọc từ JSON trong `scenarios/configs/`), tối thiểu có: `fee`, `sigma`, `Q`, `subsidy_form` (`"linear"` | `"log"`), `subsidy_window` (số bước, mặc định `24`), `steps`, `L_A`, `c_V`, `n_farmers`, `victim_type` (`"omniscient"` | `"adaptive"`), `defense` (`null` hoặc tên + tham số).

**Thứ tự trong mỗi bước `t`** (bộ chạy đảm bảo): đặt `pool.t = t` → giao dịch nền `bg:*` → farmer (gồm farmer của `attacker:0` nếu `attacker_farm_share` > 0) → victim → attacker → `arb:0` → (nếu `t+1` chia hết cho `subsidy_window`) nền tảng chốt thưởng → thu hồi (clawback, nếu có) → ghi các dòng `subsidy` tới hạn → dòng `step`.

**Quy ước tác nhân (đã chốt 14/10):**
- **Arbitrageur `arb:0`** là tác nhân riêng, hành động **cuối** mỗi bước (trước dòng `step`): swap kéo giá bể về `P_e(t)` bằng `sqrt_price_limit`. Hết thanh khoản thì dừng ở đó. Khối lượng của `arb:*` được ghi log như mọi swap, B có thể lọc theo `role`.
- **Farmer chỉ mua** (`zero_for_one=False`, đưa `v` token1 vào bể), token0 nhận về được định giá theo `P_e(t)` — như Theorem 1 bài gốc (bài gốc đo được chỉ 0,0038% swap của farmer là khứ hồi). Lợi ích một bước: `U(v) = thưởng(v) − [v − P_e·x(v)]`, trong đó `x(v)` lấy từ `quote_swap` trên bể thật; phần `v − P_e·x(v)` = phí `f·v` + `MC(v)` (trượt giá so với giá ngoài). Khối lượng `v` tính bằng token1. **Không dùng khứ hồi trong bể**: khứ hồi gần như thuận nghịch nên chi phí không phụ thuộc `L`, làm tường `L_A` mất tác dụng. Giá được kéo về tick tường nhờ `arb:0` bán token0 ngược lại cuối bước.
- **Trợ cấp** cộng dồn theo cửa sổ `subsidy_window` bước (mặc định 24 = 1 ngày): cuối mỗi cửa sổ, mỗi farmer nhận `σ·min{v_win, Q}` (tuyến tính) hoặc theo luật log, ghi một dòng `subsidy` (`owner` = farmer, `amount1` = tiền thưởng). Biện pháp "trả trễ" chỉ dời thời điểm ghi dòng này; biến thể `clawback` hủy khoản treo (không có dòng `subsidy`, tổng ở `meta["subsidy_clawed"]`).
- **Kẻ tấn công cũng là farmer (14/10, CH-6):** config `attacker_farm_share` = s ∈ [0, 1) (mặc định 0). Khi s > 0, `attacker:0` có thêm **lệnh mua** (swap `zero_for_one=False`, `amount1 > 0`) như farmer và nhận dòng `subsidy` với `owner = "attacker:0"`. Token0 mua được **không** cộng vào kho xả (định giá theo `P_e` như farmer). Meta thêm `attacker_farm_accounts` (số tài khoản ảo m = s/(1−s)·n_farmers), `subsidy_pending_attacker`, `subsidy_clawed`.

## 4. Log sự kiện — đầu ra mà vai B đọc

`EventLog` = danh sách dòng; xuất ra `pandas.DataFrame` bằng `log.to_frame()` và ra file bằng `log.to_csv(path)`.

| Cột | Kiểu | Ý nghĩa |
|---|---|---|
| `t` | int | bước thời gian |
| `seq` | int | thứ tự trong cùng bước (tăng dần) |
| `kind` | str | `mint`, `burn`, `collect`, `swap`, `subsidy`, `step` |
| `owner` | str | như mục 1 |
| `role` | str | phần trước `:` của `owner` |
| `position_id` | int / NaN | với mint, burn, collect |
| `tick_lower`, `tick_upper` | int / NaN | với mint, burn |
| `liquidity` | float / NaN | `L` của mint/burn |
| `amount0`, `amount1` | float | dấu theo mục 1 (dương = vào bể): mint dương, burn âm, swap token vào dương / token ra âm (lượng vào **đã gồm phí**). Với `collect`: `0`. Với `subsidy`: `amount0 = 0`, `amount1` = tiền trợ cấp trả cho farmer (ghi **dương**, không đi qua bể). Với `step`: `0` |
| `fee0`, `fee1` | float | **luôn ≥ 0**: phí của swap (theo token vào, chiều kia = 0), hoặc phí LP rút ra ở `collect`. Dòng khác: `0` |
| `sqrt_price_after`, `tick_after` | float, int | trạng thái bể sau sự kiện |
| `liquidity_active_after` | float | `L_active` sau sự kiện |
| `external_price` | float / NaN | chỉ ở dòng `step` |

- Dòng `kind="step"`: bộ chạy ghi **một dòng mỗi bước** sau khi mọi tác nhân hành động — ảnh chụp giá, `L_active`, giá ngoài. B dùng dòng này cho chuỗi thời gian.
- Dòng `kind="subsidy"`: nền tảng ghi khi trả thưởng cho farmer (cuối mỗi cửa sổ trợ cấp, hoặc theo luật của biện pháp trả trễ). Đây là nguồn của **chi phí trợ cấp**.
- Vai B **chỉ đọc log**, không gọi vào engine — nên B làm được trên log giả trước khi engine xong.

## 5. Đo lường — `metrics/` (vai B cài đặt)

```python
def phases(df) -> dict              # mốc t_m, t_50, t_peak, t_0, t_oot, t_b và ranh giới Prep/Attack/Post
def victim_loss(df, mode="full")    # mode: "full" | "nonalpha" (như bài gốc); trả theo từng victim + tổng
def attacker_profit(df)             # từ dòng tiền của owner role=attacker trong [t_0, t_b] (+ phí), đo độc lập
def subsidy_cost(df)                # tổng amount1 của kind="subsidy"
def pool_liquidity(df)              # chuỗi L_active và trung bình trước/sau như kế hoạch
def derived(df)                     # hiệu quả chi tiêu, tỷ lệ rò rỉ
def validate_rq1(dfs: list) -> "pd.DataFrame"   # bảng Đạt / Không đạt theo mục 6 kế hoạch simulator
```

## 6. Log giả để làm song song

`scenarios/fake_log.py` (vai C viết trước 18/10): `make_fake_log(seed) -> pd.DataFrame` sinh một vụ tấn công "giả" đúng định dạng mục 4 (dựng tường → farmer giao dịch → victim mint → rút tường → xả → post), số liệu không cần đúng mô hình, chỉ cần đúng cột và đúng trình tự. B dùng file này để viết và test `metrics/` trước khi có engine thật.

## 7. Các câu hỏi đã chốt (14/10/2026)

| Câu hỏi | Quyết định | Lý do ngắn |
|---|---|---|
| 1 bước = 1 giờ hay 1 block? | **1 giờ** | Dữ liệu bài gốc theo giờ (giá Alpha, cửa sổ `t_b` 2 giờ, VWAP 1 giờ); 1 block (3 s trên BSC) làm số bước gấp 1200 lần mà không thêm thông tin. Thứ tự trong giờ đã có `seq` |
| Arbitrageur có phải tác nhân riêng? | **Có**, `arb:0`, kéo giá về `P_e` cuối mỗi bước | Tách khối lượng chênh giá khỏi khối lượng farmer/nền, B lọc được theo `role`. Lưu ý: arb kéo giá bể về `P_e`, nên trong kịch bản tấn công `Market` phải cho `P_e` tụt theo cú xả (hoặc tắt arb trong pha Attack) — C xử lý khi viết kịch bản |
| Farmer giao dịch thế nào? | **Chỉ mua trong bể, `arb:0` bán ngược lại** (sửa 14/10, bỏ phương án khứ hồi) | Khớp Theorem 1 và số đo bài gốc; khứ hồi trong bể có chi phí không phụ thuộc `L` nên tường mất tác dụng (trái quyết định chốt số 4) |
| Trợ cấp trả theo cửa sổ dài bao nhiêu? | **24 bước** (1 ngày), tham số `subsidy_window` | Khớp chu kỳ ngày của Binance Alpha; luật log dùng cửa sổ trượt 15 ngày = 360 bước khi cần |
