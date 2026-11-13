import json

from scenarios import lay_log_bsc as L
from scenarios.tai_lich_su_be import TOPIC_INITIALIZE, chon_be, doc_lich_su, khoang_tiep, lui_mot_be


def test_khoang_tiep_nhay_qua_cua_so_va_khong_cham():
    cs = [(200, 300), (500, 600)]
    assert khoang_tiep(499, cs, 1000, 0) == (301, 499)             # dừng ngay sau cửa sổ 200–300
    assert khoang_tiep(650, cs, 1000, 0) == (601, 650)
    assert khoang_tiep(550, cs, 100, 0) == (400, 499)              # đang trong cửa sổ 500–600: nhảy xuống ngay dưới 500
    assert khoang_tiep(350, cs, 100, 0) == (301, 350)              # không chạm cửa sổ 200–300 dù đủ chỗ
    assert khoang_tiep(150, cs, 100, 0) == (51, 150)
    assert khoang_tiep(40, cs, 100, 50) is None                    # dưới giới hạn lo


def test_chon_be_chia_vong_tron_va_loc_tien_to():
    ds = ["0xc", "0xa", "0xb", "0xd", "0xe"]
    assert chon_be(ds, "1/2") == ["0xa", "0xc", "0xe"] and chon_be(ds, "2/2") == ["0xb", "0xd"]
    assert chon_be(ds, None, "0xb,0xd") == ["0xb", "0xd"]
    tat_ca = [b for i in (1, 2, 3) for b in chon_be(ds, f"{i}/3")]
    assert sorted(tat_ca) == sorted(ds)


class _RPCGia:
    """Giả `getLogs`: Initialize ở block 1000; Mint ở 1500, Burn ở 1800; từ chối khoảng dài hơn `toi_da` block."""

    def __init__(self, toi_da):
        self.toi_da, self.so_lan, self.so_loi = toi_da, 0, 0

    def goi(self, m, p):
        self.so_lan += 1
        a, z = int(p[0]["fromBlock"], 16), int(p[0]["toBlock"], 16)
        if z - a + 1 > self.toi_da:
            self.so_loi += 1
            raise RuntimeError('{"code": -32000, "message": "query exceeds block range limit"}')
        chua = lambda b: a <= b <= z
        out = []
        if chua(1000):
            out.append({"topics": [TOPIC_INITIALIZE], "blockNumber": hex(1000), "data": "0x", "transactionIndex": "0x0",
                        "logIndex": "0x0", "transactionHash": "0xh"})
        for b, ten in ((1500, "mint"), (1800, "burn")):
            if chua(b):
                d = "0x" + "".join(f"{x:064x}" for x in (0, 5, 7, 9))
                t = [L.TOPIC[ten], "0x" + "0" * 24 + "ab" * 20, "0x" + f"{(-10) % (1 << 256):064x}", "0x" + f"{10:064x}"]
                if ten == "burn":
                    d = "0x" + "".join(f"{x:064x}" for x in (5, 7, 9))
                out.append({"topics": t, "blockNumber": hex(b), "data": d, "transactionIndex": "0x1", "logIndex": "0x2",
                            "transactionHash": "0xh" + ten})
        return out


def test_lui_dung_khi_gap_initialize_va_ghi_du(tmp_path):
    r = _RPCGia(toi_da=600)
    td = lui_mot_be(r, "0xabcdef1234" + "0" * 30, [(2000, 2500)], 2000, buoc=1000, lo=0, goc=tmp_path)
    assert td["xong"] and td["thap"] <= 1000 and td["kich"] <= 600    # chia đôi khi node từ chối và nhớ
    d = doc_lich_su("0xabcdef1234", 2000, goc=tmp_path)
    assert sorted(d["block"].astype(int)) == [1500, 1800] and set(d["kind"]) == {"mint", "burn"}
    so = r.so_lan
    lui_mot_be(r, "0xabcdef1234" + "0" * 30, [(2000, 2500)], 2000, buoc=1000, lo=0, goc=tmp_path)   # chạy lại: đã xong, không gọi nữa
    assert r.so_lan == so


def test_lui_khong_thay_initialize_thi_dung_o_lo(tmp_path):
    class R:
        so_lan = 0

        def goi(self, m, p):
            R.so_lan += 1
            return []
    td = lui_mot_be(R(), "0xabcdef1234" + "0" * 30, [], 3000, buoc=1000, lo=1000, goc=tmp_path)
    assert td["xong"] and td["thap"] == 1000 and "khong_thay_Initialize" in td["ghi_chu"] and R.so_lan == 2
    assert json.loads((tmp_path / "0xabcdef12" / "lui" / "tien_do.json").read_text())["xong"] is True


def test_doc_lich_su_loc_block_va_rong_khi_chua_tai(tmp_path):
    assert doc_lich_su("0x0000000000", 20, goc=tmp_path).empty


def test_be_tao_trong_cua_so_dau_thi_chi_quet_khoang_giua():
    import tempfile
    from pathlib import Path

    class R:
        so_lan = 0

        def goi(self, m, p):
            R.so_lan += 1
            a, z = int(p[0]["fromBlock"], 16), int(p[0]["toBlock"], 16)
            return [{"topics": [TOPIC_INITIALIZE], "blockNumber": hex(1200), "data": "0x"}] if a <= 1200 <= z and len(p[0]["topics"][0]) == 1 else []
    with tempfile.TemporaryDirectory() as d:
        # cửa sổ đầu [1000, 1500] có sự kiện đầu ở 31000? dùng 21000 để vượt DO_TRE_KIEM_TAO; Initialize ở 1200 nằm trong cửa sổ
        td = lui_mot_be(R(), "0xabcdef1234" + "0" * 30, [(1000, 21500), (30000, 31000)], 30000, buoc=5000, lo=0, goc=Path(d), dau_su_kien=21000)
    assert td["xong"] and td["thap"] == 21501 and td["ghi_chu"] == "tao_trong_cua_so_dau"
    assert R.so_lan <= 2 + 5                       # kiểm Initialize ≤ 5 lượt (1000–21000, 5.000 block mỗi lần) + khoảng giữa hai cửa sổ
