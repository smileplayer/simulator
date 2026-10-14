from metrics.report import summarize_many
from metrics.validate import bang_chia_nhom
from plots.hinh import ve_bang4, ve_bang7, ve_hop_rv, ve_timeline
from scenarios.fake_log import make_fake_log


def test_ve_du_bon_hinh(tmp_path):
    dfs = [make_fake_log(s) for s in (0, 1)]
    tt = summarize_many(dfs)
    b = bang_chia_nhom(tt)
    ph = ve_timeline(dfs[0], tmp_path / "tl.png", "thử")
    ve_hop_rv(tt, tmp_path / "rv.png")
    ve_bang4(b["bang4_lift"], tmp_path / "b4.png")
    ve_bang7(b["bang7_drop"], tmp_path / "b7.png")
    assert ph["t_0"] == 144
    for f in ("tl", "rv", "b4", "b7"):
        p = tmp_path / f"{f}.png"
        assert p.exists() and p.stat().st_size > 10_000
