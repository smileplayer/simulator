"""attacker_profit trên log GĐ3: victim dải rộng phải được nhận ra khi không truyền `victims` (lỗi w_max = 1, 11/11)."""
from metrics.phases import phases
from metrics.pnl import attacker_profit
from scenarios.batch import to_hop_rq1
from scenarios.quet_gd3 import cau_hinh_gd3
from scenarios.run import run_frame


def test_attacker_profit_nhan_victim_dai_rong():
    vu = {v["id"]: v for v in to_hop_rq1()}["L27_10"]
    df = run_frame(cau_hinh_gd3(vu, 2.0, 50, "omniscient"), 0)
    assert df.attrs["meta"]["w_victim_chon"] == 50
    ph = phases(df)
    mac_dinh = attacker_profit(df, ph).loc["TOTAL", "ban_thang"]
    tuong_minh = attacker_profit(df, ph, victims={"victim:0"}).loc["TOTAL", "ban_thang"]
    hep = attacker_profit(df, ph, w_max=1).loc["TOTAL", "ban_thang"]
    assert mac_dinh == tuong_minh          # mặc định giờ lấy w_max từ meta
    assert hep > tuong_minh                # w_max = 1 bỏ sót victim: bể bán thẳng còn thanh khoản của nó nên bán được giá hơn
