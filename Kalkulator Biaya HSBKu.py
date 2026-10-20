import marimo

__generated_with = "0.19.11"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import math
    import pandas as pd

    return math, mo, pd


@app.cell
def _():
    # HSBKu per provinsi (Rp), PMK 51/PMK.02/2012: (Pertanian, Non Pertanian)
    HSBKU = {
        "Aceh": (50_000, 100_000), "Sumatera Utara": (50_000, 100_000), "Bengkulu": (30_000, 60_000),
        "Jambi": (50_000, 100_000), "Riau": (60_000, 120_000), "Sumatera Barat": (50_000, 100_000),
        "Sumatera Selatan": (50_000, 100_000), "Lampung": (40_000, 80_000),
        "Kepulauan Bangka Belitung": (50_000, 100_000), "Kepulauan Riau": (50_000, 100_000),
        "Banten": (50_000, 100_000), "Jawa Barat": (50_000, 100_000), "DKI Jakarta": (60_000, 120_000),
        "Jawa Tengah": (40_000, 80_000), "Jawa Timur": (50_000, 100_000), "DI Yogyakarta": (40_000, 80_000),
        "Bali": (50_000, 100_000), "Nusa Tenggara Barat": (30_000, 60_000),
        "Nusa Tenggara Timur": (20_000, 40_000), "Kalimantan Barat": (40_000, 80_000),
        "Kalimantan Selatan": (50_000, 100_000), "Kalimantan Tengah": (50_000, 100_000),
        "Kalimantan Timur": (60_000, 120_000), "Gorontalo": (30_000, 60_000),
        "Sulawesi Selatan": (40_000, 80_000), "Sulawesi Tenggara": (40_000, 80_000),
        "Sulawesi Tengah": (40_000, 80_000), "Sulawesi Utara": (50_000, 100_000),
        "Sulawesi Barat": (30_000, 60_000), "Maluku": (20_000, 40_000), "Maluku Utara": (20_000, 40_000),
        "Papua Barat": (50_000, 100_000), "Papua": (50_000, 100_000),
    }
    # Book1.pdf: (batas atas Ha, pembagi m2, konstanta Rp) for L > 10 Ha
    TIERS = [(20, 500, 100_000), (1_010, 4_000, 14_000_000), (float("inf"), 10_000, 134_000_000)]
    PERSEN = 0.8554
    # Analisa SBK PBT Luasan: Jawa Bali uses RO 6413.QAB.U16 and its own per-Ha SBK
    JAWA_BALI = {"Banten", "Jawa Barat", "DKI Jakarta", "Jawa Tengah", "Jawa Timur", "DI Yogyakarta", "Bali"}
    return HSBKU, JAWA_BALI, PERSEN, TIERS


@app.cell
def _(PERSEN, TIERS, math, pd):
    def biaya_ukur(L, hsbku, tarif):
        """Biaya pengukuran (tanpa TAK), kalkulator.xlsx K4: rumus Book1.pdf, dibulatkan ke bawah ke ribuan.
        tarif = SBK per Ha untuk 0-10 Ha (1.740.000 Luar Jawa Bali, 884.000 Jawa Bali)."""
        if L <= 10:
            t = tarif * L
        else:
            pembagi, konst = next((p, k) for batas, p, k in TIERS if L <= batas)
            t = tarif * 10 + PERSEN * ((L - 10) * 10_000 / pembagi * hsbku + konst)
        return math.floor(round(t, 6) / 1_000) * 1_000

    # Rincian Biaya per Ha (Analisa SBK PBT Luasan): harga Luar Jawa Bali / Jawa Bali
    B = ("B", "Partisipasi Masyarakat")
    C = ("C", "Pengukuran dan Pemetaan Bidang Tanah")
    BRG = ("528111", "Belanja Barang Persediaan Barang Konsumsi")
    NON = ("521219", "Belanja Barang Non Operasional Lainnya")
    rincian = pd.DataFrame([
        (*B, *BRG, "ATK",                5_000,   5_000),
        (*B, *NON, "Operasional lapang", 230_000, 230_000),
        (*C, *BRG, "ATK",                25_000,  25_000),
        (*C, *NON, "Pembantu Ukur",      128_000, 128_000),
        (*C, *NON, "Petugas Ukur",       676_000, 248_000),
        (*C, *NON, "Koordinator",        676_000, 248_000),
    ], columns=["sub", "sub_nama", "akun", "akun_nama", "item", "luar", "jawa"])
    assert (rincian.luar.sum(), rincian.jawa.sum()) == (1_740_000, 884_000)

    # ATK C PNBP fixed cost per bidang: Rp 83.000 for 10-20 Ha, Rp 1.487.000 (kalkulator.xlsx I21) above 20 Ha

    def rinci(L, hsbku, jawa_bali=False):
        """kalkulator.xlsx kolom H/I: Bagian SBK = min(L, 10) Ha × harga; Bagian PNBP = sisa biaya di atas SBK:
        10–20 Ha: 28% Operasional lapang, 72% Pengukuran; di atas 20 Ha: 20% / 80%. Dari bagian Pengukuran,
        ATK C tetap (Rp 83.000 untuk 10–20 Ha, Rp 1.487.000 di atas 20 Ha), sisanya ke 3 item 521219 C menurut SBK."""
        d = rincian.drop(columns=["luar", "jawa"]).assign(harga=rincian["jawa" if jawa_bali else "luar"])
        d["vol"] = min(L, 10)
        d["sbk"] = d.vol * d.harga
        pnbp = biaya_ukur(L, hsbku, d.harga.sum()) - d.sbk.sum()
        # Pengukuran share of PNBP: 72% for 10-20 Ha, 80% above 20 Ha; the rest goes to Operasional lapang.
        # ATK C PNBP is a fixed cost, never more than the Pengukuran share (just above 10 Ha ATK C takes all of it
        # and the honor items get 0), so the items always add up to the formula total
        ukur = pnbp * (0.72 if L <= 20 else 0.8)
        atk_c = min(83_000 if L <= 20 else 1_487_000, ukur)
        honor = (d["sub"] == "C") & (d.akun == "521219")
        d["pnbp"] = 0.0
        d.loc[d.item == "Operasional lapang", "pnbp"] = pnbp - ukur
        d.loc[(d["sub"] == "C") & (d.item == "ATK"), "pnbp"] = atk_c
        d.loc[honor, "pnbp"] = (ukur - atk_c) * d.sbk[honor] / d.sbk[honor].sum()
        return d

    # self-check against kalkulator.xlsx (L = 22 Ha, HSBKu 60.000) and hand-computed values
    _x = rinci(22, 60_000)
    assert biaya_ukur(22, 60_000, 1_740_000) == 30_915_000
    assert _x.pnbp.tolist()[:3] == [0, 2_703_000, 1_487_000]
    assert round(_x.pnbp.iloc[3], 2) == 806_486.49 and round(_x.pnbp.iloc[4], 2) == 4_259_256.76
    assert round((_x.sbk + _x.pnbp).sum()) == 30_915_000
    assert biaya_ukur(5, 50_000, 1_740_000) == 8_700_000 and rinci(5, 50_000).pnbp.sum() == 0
    assert rinci(15, 50_000).pnbp.iloc[2] == 83_000 and rinci(21, 50_000).pnbp.iloc[2] == 1_487_000
    _y = rinci(10.1, 20_000)  # PNBP 119.000: Operasional 28% (33.320), 72% = 85.680 (83.000 ATK C + 2.680 honor)
    assert round(_y.pnbp.iloc[1]) == 33_320 and _y.pnbp.iloc[2] == 83_000 and round(_y.pnbp.iloc[3:].sum()) == 2_680
    _w = rinci(10.05, 20_000)  # PNBP 102.000: 72% = 73.440 < 83.000, so ATK C gets all of it and honor 0
    assert round(_w.pnbp.iloc[2]) == 73_440 and (_w.pnbp.iloc[3:] == 0).all() and round(_w.pnbp.sum()) == 102_000
    _z = rinci(16, 50_000)  # PNBP 5.217.000: 28% = 1.460.760, 72% = 3.756.240 (83.000 ATK C + 3.673.240 honor)
    assert round(_z.pnbp.iloc[1]) == 1_460_760 and round(_z.pnbp.iloc[3:].sum()) == 3_673_240 and round(_z.pnbp.sum()) == 5_217_000
    assert biaya_ukur(15, 50_000, 1_740_000) == 17_400_000 + 4_362_000  # 0.8554 × (5.000.000 + 100.000) = 4.362.540
    _j = rinci(15, 50_000, jawa_bali=True)
    assert _j.sbk.sum() == 8_840_000 and round((_j.sbk + _j.pnbp).sum()) == 8_840_000 + 4_362_000
    return biaya_ukur, rinci


@app.cell
def _(HSBKU, mo):
    provinsi = mo.ui.dropdown(options=list(HSBKU), value="Sumatera Barat", label="1\\. Pilih provinsi")
    jenis = mo.ui.radio(options=["Pertanian", "Non Pertanian"], value="Pertanian", inline=True, label="HSBKu")
    luas = mo.ui.number(start=0, value=100, step=0.01, label="2\\. Luas (Ha)")
    # TAK at cost per honor item (kalkulator.xlsx J24:L26): fixed 3 items x 3 kolom
    tak_input = mo.ui.dictionary({
        item: mo.ui.dictionary({
            # Pembantu Ukur gets no Akomodasi: input locked at 0
            k: mo.ui.number(start=0, value=0, step=1_000, disabled=(item, k) == ("Pembantu Ukur", "Akomodasi"))
            for k in ["Transportasi", "Akomodasi", "Konsumsi"]
        })
        for item in ["Pembantu Ukur", "Petugas Ukur", "Koordinator"]
    })
    return jenis, luas, provinsi, tak_input


@app.cell
def _(HSBKU, JAWA_BALI, jenis, luas, mo, pd, provinsi, rinci, tak_input):
    TAK = ["Transportasi", "Akomodasi", "Konsumsi"]
    NUM = ["sbk", "pnbp", *TAK, "total"]
    rp = lambda x: f"Rp {x:,.0f}".replace(",", ".")
    fmt = lambda x: f"{x:,.2f}".rstrip("0").rstrip(".").replace(",", "#").replace(".", ",").replace("#", ".")
    hsbku = HSBKU[provinsi.value][jenis.value == "Non Pertanian"]
    _L = luas.value or 0
    _jb = provinsi.value in JAWA_BALI

    _out = [mo.md("# Kalkulator Biaya Pengukuran PBT Luasan"),
            mo.hstack([provinsi, jenis], justify="start", gap=2), luas,
            mo.md("<small>Pemisah desimal mengikuti bahasa browser: koma untuk Bahasa Indonesia (mis. 10,5), "
                  "titik untuk English (mis. 10.5).</small>")]
    if _L > 10:  # TAK at cost only applies to the part above 10 Ha
        _out += [mo.md("3\\. Isi TAK at cost (Rp) per item"),
                 mo.md("<small>Isi dalam Rupiah tanpa titik atau koma, mis. 500000.</small>"),
                 mo.vstack([mo.hstack([mo.md(""), *(mo.md(f"{k} (Rp)") for k in TAK)], widths="equal")] + [
                     mo.hstack([mo.md(item), *tak_input[item].values()], widths="equal") for item in tak_input
                 ])]
    if _L <= 0:
        _out.append(mo.callout(mo.md("Isi luas lebih dari 0 Ha."), kind="warn"))
    else:
        _tak = pd.DataFrame.from_dict(tak_input.value, orient="index")[TAK].fillna(0)
        if _L <= 10:  # hidden input -> no TAK (blank columns), even if values were typed earlier
            _tak[:] = float("nan")
        _d = rinci(_L, hsbku, _jb)
        # TAK only on the 3 honor items; NaN elsewhere renders blank
        _d = _d.join(_tak, on="item")
        _d["total"] = _d[NUM[:-1]].sum(axis=1)

        # flatten: sub-komponen row + akun rows (with subtotals) + item rows; sub/akun rows in bold
        _rows = []
        for (_sk, _sn), _g in _d.groupby(["sub", "sub_nama"], sort=False):
            _rows.append(dict(kode=_sk, uraian=_sn, **_g[NUM].sum(min_count=1), bold=True))
            for (_ak, _an), _ga in _g.groupby(["akun", "akun_nama"], sort=False):
                _rows.append(dict(kode=_ak, uraian=_an, **_ga[NUM].sum(min_count=1), bold=True))
                _rows += [dict(kode="", uraian=r["item"], **r[NUM], bold=False) for _, r in _ga.iterrows()]
        _disp = pd.DataFrame(_rows)
        _bold = set(_disp.index[_disp.bold].astype(str))
        _disp = _disp.drop(columns="bold").rename(columns={
            "kode": "Kode", "uraian": "Uraian", "sbk": "Bagian SBK", "pnbp": "Bagian PNBP", "total": "Yang dicairkan"})
        _ncols = ["Bagian SBK", "Bagian PNBP", *TAK, "Yang dicairkan"]
        _num = lambda x: "" if pd.isna(x) else f"{x:,.0f}".replace(",", ".")
        _out += [
            mo.md("## Rincian Biaya"),
            mo.md(("**6413.QAB.U16  PBT Luasan (Ulayat/HKB Redis/BMN/HPL) Jawa Bali**" if _jb else
                   "**6413.QAB.U17  PBT Luasan (Ulayat/HKB Redis/BMN/HPL) Luar Jawa Bali**")
                  + f"<br>052 Pengukuran dan Pemetaan Bidang Tanah (UTAMA) · {fmt(_L)} Ha · "
                    f"HSBKu {provinsi.value} ({jenis.value}) {rp(hsbku)}"),
            mo.ui.table(
                _disp, selection=None, pagination=False, show_column_summaries=False, show_data_types=False,
                show_download=False, format_mapping={c: _num for c in _ncols},
                text_justify_columns={c: "right" for c in _ncols}, wrapped_columns=["Uraian"],
                style_cell=lambda row, col, val: {"fontWeight": "bold"} if row in _bold else {},
            ),
            mo.md(f"### Total yang dicairkan: {rp(_d.total.sum())}"),
        ]
    mo.vstack(_out)
    return


@app.cell
def _(mo):
    _rumus = mo.md(r"""
    Biaya pengukuran (Book1.pdf), $L$ = luas dalam Ha, HSBKu dari PMK 51/PMK.02/2012,
    hasil dibulatkan ke bawah ke ribuan.
    $SBK$ = Rp 1.740.000/Ha (Luar Jawa Bali) atau Rp 884.000/Ha (Jawa Bali: Banten, Jawa Barat, DKI Jakarta,
    Jawa Tengah, Jawa Timur, DI Yogyakarta, Bali):

    | Luas | Rumus |
    |---|---|
    | $L \le 10$ | $T = SBK \times L$ |
    | $10 < L \le 20$ | $T = 10 \times SBK + 85{,}54\% \times \left(\frac{(L-10)\times 10.000}{500} \times HSBKu + 100.000\right)$ |
    | $20 < L \le 1.010$ | $T = 10 \times SBK + 85{,}54\% \times \left(\frac{(L-10)\times 10.000}{4.000} \times HSBKu + 14.000.000\right)$ |
    | $L > 1.010$ | $T = 10 \times SBK + 85{,}54\% \times \left(\frac{(L-10)\times 10.000}{10.000} \times HSBKu + 134.000.000\right)$ |

    Rincian per item:

    - **Bagian SBK** = $\min(L, 10)$ Ha × harga satuan item.
    - **Bagian PNBP** = $T -$ total Bagian SBK, dibagi ke Operasional lapang dan Pengukuran:
      28% / 72% untuk 10–20 Ha, 20% / 80% di atas 20 Ha. Dari bagian Pengukuran, ATK sub-komponen C tetap
      Rp 83.000 (10–20 Ha) atau Rp 1.487.000 (di atas 20 Ha), paling banyak sebesar bagian Pengukuran;
      sisanya ke Pembantu Ukur, Petugas Ukur, Koordinator menurut Bagian SBK masing-masing.
    - **TAK** (Transportasi, Akomodasi, Konsumsi) at cost.
    - **Yang dicairkan** = Bagian SBK + Bagian PNBP + TAK.
    """)
    # collapsed by default
    mo.vstack([mo.md("---"), mo.accordion({"Rumus": _rumus})])
    return


if __name__ == "__main__":
    app.run()
