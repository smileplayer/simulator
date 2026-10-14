# INTERFACE — hợp đồng giữa ba vai

> **Trạng thái: DỰ THẢO (14/10/2026).** Vai C rà và chốt trước **18/10**, rồi đổi dòng này thành "ĐÃ CHỐT ngày …". Sau khi chốt, mọi thay đổi phải ghi "ĐỔI INTERFACE" trong nhật ký `SYNC.md`. Chỉ vai C sửa file này.

## 1. Quy ước chung

| Thứ | Quy ước |
|---|---|
| token0 = `x` | token alpha (token phụ, bị xả) |
| token1 = `y` | token định giá (USDT); **mọi giá trị tiền tính bằng token1** |
| Giá | `P` = token1 trên mỗi token0; `z = √P`; `P(i) = 1.0001^i` |
| Tick | số nguyên; `tick_spacing` mặc định 1 |
| Phí | `fee` = tỷ lệ (ví dụ `0.0025`), thu trên **token đi vào**, cộng dồn cho LP theo `feeGrowth` |
| Thời gian | bước nguyên `t = 0, 1, 2, …`; **1 bước = 1 giờ** (đề xuất — C chốt) |
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

Cấu hình kịch bản là `dict` (đọc từ JSON trong `scenarios/configs/`), tối thiểu có: `fee`, `sigma`, `Q`, `subsidy_form` (`"linear"` | `"log"`), `steps`, `L_A`, `c_V`, `n_farmers`, `victim_type` (`"omniscient"` | `"adaptive"`), `defense` (`null` hoặc tên + tham số).

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
| `amount0`, `amount1` | float | dấu theo mục 1 (dương = vào bể). Với `subsidy`: `amount1` = tiền trợ cấp trả cho farmer (ghi **dương**, không đi qua bể) |
| `fee0`, `fee1` | float | phí của swap (theo token vào), hoặc phí thu được ở `collect` |
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

## 7. Câu hỏi còn mở (C quyết khi chốt)

- 1 bước = 1 giờ hay 1 block?
- Arbitrageur có phải tác nhân riêng (`arb:*`) kéo giá bể về `P_e` mỗi bước không?
- Farmer giao dịch hai chiều thế nào để khối lượng lớn mà giá vẫn trong tick?
- Trợ cấp trả theo cửa sổ dài bao nhiêu bước?
