"""Bộ tải log BSC: keccak-256 và topic đúng chuẩn, giải mã log, tải theo đoạn có chia đôi và chạy tiếp (không cần mạng)."""
import json

from scenarios.lay_log_bsc import RPC, TOPIC, chay, giai_ma, keccak256, tai_doan


def _w(v: int) -> str:
    return f"{v % (1 << 256):064x}"


def test_keccak_va_topic_chuan():
    assert keccak256(b"").hex() == "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470"
    assert keccak256(b"a" * 135).hex() == keccak256(b"a" * 135).hex() and len(keccak256(b"a" * 135)) == 32
    # topic0 quen thuộc của Uniswap v3 (Swap, Mint, Burn)
    assert TOPIC["swap_uniswap"] == "0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67"
    assert TOPIC["mint"] == "0x7a53080ba414158be7ec69b987b5fb7d07dee101fe85488f0853ae16239d0bde"
    assert TOPIC["burn"] == "0x0c396cd989a39f4459b5fa1aed6a9a8dcdbc45908acfd67e028cd568da98982c"


def _log(topics, data, block=100, li=3):
    return {"topics": topics, "data": "0x" + "".join(data), "blockNumber": hex(block), "transactionIndex": "0x2",
            "logIndex": hex(li), "transactionHash": "0xabc"}


def test_giai_ma_mint_va_swap():
    chu = "0x" + "0" * 24 + "ab" * 20
    m = giai_ma(_log([TOPIC["mint"], chu, "0x" + _w(-59718), "0x" + _w(-59717)], [_w(1), _w(10 ** 20), _w(5), _w(7)]))
    assert (m["kind"], m["owner"], m["tick_lower"], m["tick_upper"], m["liquidity"], m["amount0"], m["amount1"]) == \
        ("mint", "0x" + "ab" * 20, -59718, -59717, 10 ** 20, 5, 7)
    s = giai_ma(_log([TOPIC["swap_pancake"], chu, chu], [_w(-50), _w(60), _w(2 ** 96), _w(999), _w(-3), _w(0), _w(0)]))
    assert (s["kind"], s["amount0"], s["amount1"], s["sqrt_price_x96"], s["liquidity_active"], s["tick"]) == \
        ("swap", -50, 60, 2 ** 96, 999, -3)
    assert giai_ma(_log(["0x" + "11" * 32], [])) is None


class _RPCGia(RPC):
    """Node giả: mỗi block có một Burn; từ chối khoảng > 4 block; đếm số lần gọi getLogs."""

    def __init__(self):
        super().__init__("gia", 0.0)
        self.goi_logs = 0

    def goi(self, method, params):
        if method == "eth_getBlockByNumber":
            return {"timestamp": hex(1_700_000_000 + int(params[0], 16))}
        self.goi_logs += 1
        a, z = int(params[0]["fromBlock"], 16), int(params[0]["toBlock"], 16)
        if z - a + 1 > 4:
            raise RuntimeError("limit exceeded")
        if TOPIC["burn"] not in params[0]["topics"][0]:
            return []
        chu = "0x" + "0" * 24 + "cd" * 20
        return [_log([TOPIC["burn"], chu, "0x" + _w(1), "0x" + _w(2)], [_w(9), _w(0), _w(0)], block=b) for b in range(a, z + 1)]


def test_tai_doan_chia_doi():
    rpc = _RPCGia()
    kq = list(tai_doan(rpc, "0xpool", [TOPIC["burn"]], 10, 25, 16))
    assert [e for e, _ in kq] == [13, 17, 21, 25] and sum(len(r) for _, r in kq) == 16


def test_chay_ghi_va_chay_tiep(tmp_path):
    rpc = _RPCGia()
    td = chay("0xpool", 10, 25, tmp_path, rpc, swap="khong", buoc=4)
    assert td["su_kien"] == 25
    dong = (tmp_path / "su_kien.csv").read_text().strip().splitlines()
    assert len(dong) == 17 and dong[0].startswith("block,tx_index")
    assert len((tmp_path / "moc.csv").read_text().strip().splitlines()) == 5
    truoc = rpc.goi_logs
    chay("0xpool", 10, 25, tmp_path, rpc, swap="khong", buoc=4)            # đã xong: không gọi lại, không ghi trùng
    assert rpc.goi_logs == truoc and len((tmp_path / "su_kien.csv").read_text().strip().splitlines()) == 17
    json.loads((tmp_path / "tien_do.json").read_text())
