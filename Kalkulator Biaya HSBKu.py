# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo",
#     "pandas",
#     "great-tables",
# ]
# ///

import marimo

__generated_with = "0.19.11"
app = marimo.App(width="medium")


@app.cell
async def _():
    import marimo as mo
    import math
    import sys
    import pandas as pd

    if sys.platform == "emscripten":  # published WASM site: great-tables is not bundled with Pyodide
        import micropip
        # 1.x needs multimark (no pure-Python wheel); 0.20 uses commonmark and has everything used here
        await micropip.install("great-tables==0.20.0")
    from great_tables import GT, loc, style

    return GT, loc, math, mo, pd, style


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

    # ATK C PNBP fixed cost per bidang: Rp 164.000 for 10-20 Ha, Rp 1.487.000 (kalkulator.xlsx I21) above 20 Ha

    def rinci(L, hsbku, jawa_bali=False):
        """kalkulator.xlsx kolom H/I: Bagian SBK = min(L, 10) Ha × harga; Bagian PNBP = sisa biaya di atas SBK:
        20% Operasional lapang, ATK C tetap (Rp 164.000 untuk 10–20 Ha, Rp 1.487.000 di atas 20 Ha), sisa 80% ke 3 item 521219 C menurut SBK."""
        d = rincian.drop(columns=["luar", "jawa"]).assign(harga=rincian["jawa" if jawa_bali else "luar"])
        d["vol"] = min(L, 10)
        d["sbk"] = d.vol * d.harga
        pnbp = biaya_ukur(L, hsbku, d.harga.sum()) - d.sbk.sum()
        # ATK C PNBP is a fixed cost, but never more than the 80% share: just above 10 Ha ATK C takes what is
        # left of the 80% and the honor items get 0, so the items always add up to the formula total
        atk_c = min(164_000 if L <= 20 else 1_487_000, pnbp * 0.8)
        honor = (d["sub"] == "C") & (d.akun == "521219")
        d["pnbp"] = 0.0
        d.loc[d.item == "Operasional lapang", "pnbp"] = pnbp * 0.2
        d.loc[(d["sub"] == "C") & (d.item == "ATK"), "pnbp"] = atk_c
        d.loc[honor, "pnbp"] = (pnbp * 0.8 - atk_c) * d.sbk[honor] / d.sbk[honor].sum()
        return d

    # self-check against kalkulator.xlsx (L = 22 Ha, HSBKu 60.000) and hand-computed values
    _x = rinci(22, 60_000)
    assert biaya_ukur(22, 60_000, 1_740_000) == 30_915_000
    assert _x.pnbp.tolist()[:3] == [0, 2_703_000, 1_487_000]
    assert round(_x.pnbp.iloc[3], 2) == 806_486.49 and round(_x.pnbp.iloc[4], 2) == 4_259_256.76
    assert round((_x.sbk + _x.pnbp).sum()) == 30_915_000
    assert biaya_ukur(5, 50_000, 1_740_000) == 8_700_000 and rinci(5, 50_000).pnbp.sum() == 0
    assert rinci(15, 50_000).pnbp.iloc[2] == 164_000 and rinci(21, 50_000).pnbp.iloc[2] == 1_487_000
    _y = rinci(10.1, 20_000)  # PNBP 119.000: ATK C gets the 80% (95.200), honor items 0
    assert round(_y.pnbp.iloc[2]) == 95_200 and (_y.pnbp.iloc[3:] == 0).all() and round(_y.pnbp.sum()) == 119_000
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
        item: mo.ui.dictionary({k: mo.ui.number(start=0, value=0, step=1_000) for k in ["Transportasi", "Akomodasi", "Konsumsi"]})
        for item in ["Pembantu Ukur", "Petugas Ukur", "Koordinator"]
    })
    return jenis, luas, provinsi, tak_input


@app.cell
def _(GT, HSBKU, JAWA_BALI, jenis, loc, luas, mo, pd, provinsi, rinci, style, tak_input):
    TAK = ["Transportasi", "Akomodasi", "Konsumsi"]
    NUM = ["sbk", "pnbp", *TAK, "total"]
    rp = lambda x: f"Rp {x:,.0f}".replace(",", ".")
    fmt = lambda x: f"{x:,.2f}".rstrip("0").rstrip(".").replace(",", "#").replace(".", ",").replace("#", ".")
    hsbku = HSBKU[provinsi.value][jenis.value == "Non Pertanian"]
    _L = luas.value or 0
    _jb = provinsi.value in JAWA_BALI

    _out = [mo.md("# Kalkulator Biaya Pengukuran PBT Luasan"),
            mo.hstack([provinsi, jenis], justify="start", gap=2), luas,
            mo.md("3\\. Isi TAK at cost (Rp) per item"),
            mo.vstack([mo.hstack([mo.md(""), *map(mo.md, TAK)], widths="equal")] + [
                mo.hstack([mo.md(item), *tak_input[item].values()], widths="equal") for item in tak_input
            ])]
    if _L <= 0:
        _out.append(mo.callout(mo.md("Isi luas lebih dari 0 Ha."), kind="warn"))
    else:
        _tak = pd.DataFrame.from_dict(tak_input.value, orient="index")[TAK].fillna(0)
        _d = rinci(_L, hsbku, _jb)
        # TAK only on the 3 honor items; NaN elsewhere renders blank
        _d = _d.join(_tak, on="item")
        _d["total"] = _d[NUM[:-1]].sum(axis=1)

        # flatten: per sub-komponen group -> akun row (with subtotals) + its item rows
        _rows = []
        for (_sk, _sn), _g in _d.groupby(["sub", "sub_nama"], sort=False):
            _grp = f"{_sk}  {_sn}  —  {rp(_g.total.sum())}"
            for (_ak, _an), _ga in _g.groupby(["akun", "akun_nama"], sort=False):
                _rows.append(dict(grp=_grp, kode=_ak, uraian=_an, **_ga[NUM].sum(min_count=1), is_akun=True))
                _rows += [dict(grp=_grp, kode="", uraian=r["item"], **r[NUM], is_akun=False) for _, r in _ga.iterrows()]
        _disp = pd.DataFrame(_rows)
        _out += [
            mo.md("## Rincian Biaya"),
            GT(_disp.drop(columns="is_akun"), groupname_col="grp")
            .tab_header(title=("6413.QAB.U16  PBT Luasan (Ulayat/HKB Redis/BMN/HPL) Jawa Bali" if _jb else
                               "6413.QAB.U17  PBT Luasan (Ulayat/HKB Redis/BMN/HPL) Luar Jawa Bali"),
                        subtitle=f"052  Pengukuran dan Pemetaan Bidang Tanah (UTAMA)  ·  {fmt(_L)} Ha  ·  "
                                 f"HSBKu {provinsi.value} ({jenis.value}) {rp(hsbku)}")
            .tab_spanner(label="TAK (at cost)", columns=TAK)
            .cols_label(kode="Kode", uraian="Uraian", sbk="Bagian SBK", pnbp="Bagian PNBP", total="Yang dicairkan")
            .fmt_number(columns=NUM, decimals=0, sep_mark=".", dec_mark=",")
            .sub_missing(columns=TAK, missing_text="")
            .tab_style(style=style.text(weight="bold"), locations=loc.body(rows=_disp.index[_disp.is_akun].tolist()))
            .tab_style(style=style.text(weight="bold"), locations=loc.row_groups())
            .cols_align("right", columns=["kode", *NUM])
            .tab_source_note(f"Total yang dicairkan: {rp(_d.total.sum())}")
            .tab_style(style=style.text(weight="bold", size="large"), locations=loc.source_notes()),
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
    - **Bagian PNBP** = $T -$ total Bagian SBK, dibagi: 20% ke Operasional lapang; Rp 164.000 untuk 10–20 Ha dan
      Rp 1.487.000 di atas 20 Ha (tetap; jika 80% Bagian PNBP lebih kecil, ATK C = 80% Bagian PNBP)
      ke ATK sub-komponen C; sisa 80% ke Pembantu Ukur, Petugas Ukur, Koordinator menurut Bagian SBK masing-masing.
    - **TAK** (Transportasi, Akomodasi, Konsumsi) at cost.
    - **Yang dicairkan** = Bagian SBK + Bagian PNBP + TAK.
    """)
    # collapsed by default
    mo.vstack([mo.md("---"), mo.accordion({"Rumus": _rumus})])
    return


if __name__ == "__main__":
    app.run()
