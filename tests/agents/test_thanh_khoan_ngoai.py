"""Test offline cho scenarios.thanh_khoan_ngoai bằng RPC giả (không gọi mạng)."""
from scenarios import thanh_khoan_ngoai as tk

ALPHA = "0x" + "aa" * 20
USDT = "0x55d398326f99059ff775485246999027b3197955"
WBNB = "0xbb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c"
BE_VU = "0x" + "11" * 20
BE_NGOAI = "0x" + "22" * 20
V2 = "0x" + "33" * 20


def w(x: str) -> str:
    return "0x" + x.replace("0x", "").rjust(64, "0")


class RPCGia:
    """Trả hex theo (to, data); lệnh không có trong bảng thì ném RuntimeError như node lỗi."""

    def __init__(self):
        self.bang = {}
        self.so_lan = 0

    def dat(self, to, data, kq):
        self.bang[(to.lower(), data)] = kq

    def goi(self, method, params):
        self.so_lan += 1
        c = params[0]
        k = (c["to"].lower(), c["data"])
        if k not in self.bang:
            raise RuntimeError("revert")
        return self.bang[k]


def dung_rpc():
    r = RPCGia()
    cd = tk.calldata
    r.dat(BE_VU, cd("token0()"), w(ALPHA))
    r.dat(BE_VU, cd("token1()"), w(USDT))
    r.dat(BE_VU, cd("fee()"), w("0x9c4"))
    r.dat(BE_VU, cd("factory()"), w(tk.FACTORY_PANCAKE_V3))
    r.dat(ALPHA, cd("decimals()"), w("0x12"))
    r.dat(USDT, cd("decimals()"), w("0x12"))
    r.dat(WBNB, cd("decimals()"), w("0x12"))
    r.dat(ALPHA, cd("symbol()"), "0x" + b"ALP".hex().ljust(64, "0"))          # bytes32
    r.dat(ALPHA, cd("balanceOf(address)", BE_VU), w(hex(300 * 10 ** 18)))
    r.dat(USDT, cd("balanceOf(address)", BE_VU), w(hex(1000 * 10 ** 18)))
    # bể ngoài v3 (WBNB, phí 500), một getPool trả địa chỉ 0 và một trả chính bể vụ
    r.dat(tk.FACTORY_PANCAKE_V3, cd("getPool(address,address,uint24)", ALPHA, WBNB, 500), w(BE_NGOAI))
    r.dat(tk.FACTORY_PANCAKE_V3, cd("getPool(address,address,uint24)", ALPHA, USDT, 100), w("0x0"))
    r.dat(tk.FACTORY_PANCAKE_V3, cd("getPool(address,address,uint24)", ALPHA, USDT, 2500), w(BE_VU))
    r.dat(tk.FACTORY_PANCAKE_V2, cd("getPair(address,address)", ALPHA, USDT), w(V2))
    r.dat(ALPHA, cd("balanceOf(address)", BE_NGOAI), w(hex(100 * 10 ** 18)))
    r.dat(WBNB, cd("balanceOf(address)", BE_NGOAI), w(hex(5 * 10 ** 18)))
    r.dat(ALPHA, cd("balanceOf(address)", V2), w(hex(100 * 10 ** 18)))
    r.dat(USDT, cd("balanceOf(address)", V2), w(hex(2000 * 10 ** 18)))
    return r


def test_selector_va_calldata():
    assert tk.selector("balanceOf(address)") == "70a08231"
    assert tk.selector("token0()") == "0dfe1681"
    assert tk.selector("decimals()") == "313ce567"
    assert tk.selector("getPair(address,address)") == "e6a43905"
    assert tk.selector("getPool(address,address,uint24)") == "1698ee82"
    a, b = "0x" + "aa" * 20, "0x" + "bb" * 20
    esp = "0x1698ee82" + "0" * 24 + "aa" * 20 + "0" * 24 + "bb" * 20 + "0" * 60 + "01f4"
    assert tk.calldata("getPool(address,address,uint24)", a, b, 500) == esp


def test_tim_alpha():
    assert tk.tim_alpha(ALPHA, USDT)[:2] == (ALPHA, USDT)
    assert tk.tim_alpha(WBNB, ALPHA)[:2] == (ALPHA, WBNB)
    assert tk.tim_alpha(USDT, WBNB)[0] is None


def test_symbol_hai_dang():
    assert tk.giai_ma_symbol("0x" + b"ABC".hex().ljust(64, "0")) == "ABC"
    dyn = "0x" + w("0x20")[2:] + w("0x3")[2:] + b"XYZ".hex().ljust(64, "0")
    assert tk.giai_ma_symbol(dyn) == "XYZ"
    assert tk.giai_ma_symbol(None) == ""


def test_tong_hop_ty_le():
    assert tk.tong_hop(300, 100) == 0.25
    assert tk.tong_hop(0, 0) is None


def test_be_ngoai_bo_zero_va_be_vu():
    r = dung_rpc()
    gc = []
    be = tk.tim_be_ngoai(r, ALPHA, BE_VU, 100, gc)
    dia = sorted(b[0] for b in be)
    assert dia == sorted([BE_NGOAI, V2])
    assert "pcs_v2_loi_goi" not in gc and "uni_v3_loi_goi" in gc


def test_do_mot_vu_tong_hop():
    r = dung_rpc()
    d = tk.do_mot_vu(r, dict(pool=BE_VU, t_m=100, t_b=200))
    assert d["alpha"] == ALPHA and d["quote"] == USDT and d["alpha_symbol"] == "ALP"
    assert d["factory_dung"] == 1 and d["phi_be_vu"] == 2500
    assert d["so_be_ngoai"] == 2
    assert abs(d["alpha_ngoai"] - 200) < 1e-6 and abs(d["alpha_trong_be_vu"] - 300) < 1e-6
    assert abs(d["ty_le_alpha_ngoai"] - 0.4) < 1e-9
    assert abs(d["quote_ngoai_usd"] - 2000) < 1e-6 and abs(d["quote_ngoai_wbnb"] - 5) < 1e-6
    assert d["quote_ngoai_ge_quote_vu"] == 1                # 2000 USD >= 1000 USD


def test_doc_bang_vu_that():
    vu = tk.doc_bang_vu()
    assert len(vu) == 29 and vu[0]["t_m"] == 53417418 and vu[1]["pool"].startswith("0x9485")


def test_het_han_muc_khong_bi_coi_la_be_khong_ton_tai():
    import pytest
    from scenarios.lay_log_bsc import HetHanMuc
    from scenarios.thanh_khoan_ngoai import eth_call

    class R:
        def goi(self, m, p):
            raise RuntimeError('RPC không trả lời: HTTP 429 {"error":{"message":"insufficient compute units"}}')
    with pytest.raises(HetHanMuc):
        eth_call(R(), "0xa", "0x", 1)

    class Rv:
        def goi(self, m, p):
            raise RuntimeError('{"code": -32000, "message": "execution reverted"}')
    assert eth_call(Rv(), "0xa", "0x", 1) is None        # revert thật vẫn là "không đọc được"


def test_dong_loi_duoc_do_lai(tmp_path):
    from scenarios.thanh_khoan_ngoai import COT, bo_dong_can_do_lai, da_xong, ghi_dong
    ra = tmp_path / "k.csv"
    ok = {c: "" for c in COT} | {"pool": "0xa", "t_m": 1, "alpha": "0xt"}
    loi = {c: "" for c in COT} | {"pool": "0xb", "t_m": 2, "ghi_chu": "khong_doc_duoc_token(x)"}
    ghi_dong(ra, ok)
    ghi_dong(ra, loi)
    assert da_xong(ra) == {("0xa", "1")}
    assert bo_dong_can_do_lai(ra) == 1 and da_xong(ra) == {("0xa", "1")}
