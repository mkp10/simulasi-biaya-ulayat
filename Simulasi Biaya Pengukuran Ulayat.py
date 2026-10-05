import marimo

__generated_with = "0.19.11"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import pandas as pd

    return mo, pd


@app.cell
def _(pd):

    cols = ["kode_output", "uraian_output", "kode_komponen", "uraian_komponen", "jenis_komponen",
            "sub_komponen", "uraian_sub_komponen", "akun", "uraian_akun",
            "item", "volume", "satuan", "harga_satuan", "jumlah"]

    out = ("6413.QAB.U17", "PBT Luasan (Ulayat/HKB Redis/BMN/HPL) Luar Jawa Bali",
           "052", "Pengukuran dan Pemetaan Bidang Tanah", "UTAMA")
    B = ("B", "Partisipasi Masyarakat")
    C = ("C", "Pengukuran dan Pemetaan Bidang Tanah")
    BRG = ("528111", "Belanja Barang Persediaan Barang Konsumsi")
    NON = ("521219", "Belanja Barang Non Operasional Lainnya")

    rows = [
        (*out, *B, *BRG, "ATK",               1, "Paket",  5_000,   5_000),
        (*out, *B, *NON, "Operasional lapang", 1, "Hektar", 230_000, 230_000),
        (*out, *C, *BRG, "ATK",               1, "Paket",  25_000,  25_000),
        (*out, *C, *NON, "Pembantu Ukur",     1, "Hektar", 128_000, 128_000),
        (*out, *C, *NON, "Petugas Ukur",      1, "Hektar", 676_000, 676_000),
        (*out, *C, *NON, "Koordinator",       1, "Hektar", 676_000, 676_000),
    ]

    df = pd.DataFrame(rows, columns=cols)
    # per-Hektar items scale with area -> variable; per-Paket (ATK) stays flat -> fixed
    df["kategori_biaya"] = df.satuan.str.lower().map({"hektar": "Variable Cost"}).fillna("Fixed Cost")
    return (df,)


@app.cell
def _():
    import altair as alt

    return (alt,)


@app.cell(hide_code=True)
def _():
    # Simulasi Koefisien ("coba koef.xlsx" > Simulasi (edit)): each block of hectares priced at tarif x koef, like tax brackets
    TIERS = [(10, 1), (100, 0.25), (1_000, 0.08), (float("inf"), 0.05)]  # (batas atas Ha, koef)

    def opsi2_blok(ha, tarif):
        """Cost per block: [{blok, koef, ha, biaya}, ...] for blocks the area reaches."""
        out, prev = [], 0
        for batas, koef in TIERS:
            if ha <= prev:
                break
            n = min(ha, batas) - prev
            nama = f"> {prev:,} Ha" if batas == float("inf") else f"{prev:,}–{batas:,} Ha"
            out.append({"blok": nama.replace(",", "."), "koef": koef, "ha": n, "biaya": n * tarif * koef})
            prev = batas
        return out

    def opsi2(ha, tarif):
        return sum(b["biaya"] for b in opsi2_blok(ha, tarif))

    # tier logic matches column F of the sheet (sheet applies koef to the full 1.740.000)
    assert opsi2(10, 1_740_000) == 17_400_000
    assert round(opsi2(3_000, 1_740_000)) == 355_830_000
    return TIERS, opsi2, opsi2_blok


@app.cell
def _(df):
    fixed = df.loc[df.kategori_biaya == "Fixed Cost", "jumlah"].sum()
    var_ha = df.loc[df.kategori_biaya == "Variable Cost", "jumlah"].sum()
    rp = lambda x: f"Rp {round(x):,}".replace(",", ".")
    # Indonesian decimal format: 1.234,5
    fmt = lambda x, d=1: f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    # tiny shares would round to 0.00% / 100.00%
    pct = lambda x: "< 0.01%" if 0 < x < 0.0001 else "> 99.99%" if 0.9999 < x < 1 else f"{x:.2%}"
    assert (pct(30_000 / 1_710_030_000), pct(1_710_000_000 / 1_710_030_000), pct(0.5)) == ("< 0.01%", "> 99.99%", "50.00%")
    return fixed, fmt, pct, rp, var_ha


@app.cell
def _(mo, pd):
    bidang_editor = mo.ui.data_editor(
        pd.DataFrame({"Bidang": ["Bidang 1", "Bidang 2", "Bidang 3"], "Luas (Ha)": [50.0, 250.0, 1_200.0]}),
        label="Daftar bidang (ubah nama/luas, tambah atau hapus baris)",
    )
    tampil_flat = mo.ui.switch(label="Tampilkan perbandingan Flat")
    return bidang_editor, tampil_flat


@app.cell
def _(
    alt,
    bidang_editor,
    fixed,
    fmt,
    lainnya,
    mo,
    opsi2,
    pd,
    rp,
    tampil_flat,
    var_ha,
):
    # each bidang is measured on its own: own ATK package (fixed) and its own koef blocks
    # (each bidang has its own boundary, so the tiers restart per bidang)
    bidang = pd.DataFrame(bidang_editor.value)
    bidang["Luas (Ha)"] = pd.to_numeric(bidang["Luas (Ha)"], errors="coerce")
    _invalid = bidang["Luas (Ha)"].isna() | (bidang["Luas (Ha)"] <= 0)
    bidang = bidang[~_invalid].reset_index(drop=True)

    bidang["Flat"] = fixed + var_ha * bidang["Luas (Ha)"]
    bidang["Simulasi Koefisien"] = bidang["Luas (Ha)"].map(lambda ha: fixed + opsi2(ha, var_ha))
    _luas_total = bidang["Luas (Ha)"].sum()
    _flat, _sk = bidang["Flat"].sum(), bidang["Simulasi Koefisien"].sum()
    _gabung = fixed + opsi2(_luas_total, var_ha) if len(bidang) else 0
    _skema = ["Flat", "Simulasi Koefisien"] if tampil_flat.value else ["Simulasi Koefisien"]

    _tabel = bidang.assign(**{
        "Luas (Ha)": bidang["Luas (Ha)"].map(fmt),
        "Flat": bidang["Flat"].map(rp),
        "Simulasi Koefisien": bidang["Simulasi Koefisien"].map(rp),
        "Rata-rata / Ha": (bidang["Simulasi Koefisien"] / bidang["Luas (Ha)"]).map(rp),
    })
    _tabel.loc[len(_tabel)] = ["Total", fmt(_luas_total), rp(_flat), rp(_sk),
                               rp(_sk / _luas_total) if _luas_total else "-"]
    if not tampil_flat.value:
        _tabel = _tabel.drop(columns="Flat")

    _long = bidang.melt(id_vars=["Bidang", "Luas (Ha)"], value_vars=_skema, var_name="skema", value_name="biaya")
    _bar = alt.Chart(_long, title="Biaya per Bidang").mark_bar().encode(
        x=alt.X("Bidang:N", title=None, sort=None),
        xOffset="skema:N",
        y=alt.Y("biaya:Q", title="Biaya (Rp)", axis=alt.Axis(format=",.0f")),
        color=alt.Color("skema:N", title="Skema"),
        tooltip=["Bidang", alt.Tooltip("Luas (Ha):Q", format=",.1f"), "skema",
                 alt.Tooltip("biaya:Q", format=",.0f")],
    ).properties(width="container")

    _ringkas = f"**{len(bidang)} bidang, {fmt(_luas_total)} Ha** · Simulasi Koefisien: **{rp(_sk)}**"
    if tampil_flat.value and _flat:
        _ringkas += f" · Flat: **{rp(_flat)}** (koefisien = {_sk / _flat:.1%} dari flat)"

    _out = [mo.md("# Simulasi"), bidang_editor]
    if _invalid.any():
        _out.append(mo.callout(mo.md(f"{_invalid.sum()} baris diabaikan: luas kosong, bukan angka, atau ≤ 0."), kind="warn"))
    if len(bidang):
        _out += [mo.ui.table(_tabel, selection=None, pagination=False), mo.md(_ringkas)]
        if lainnya.value:  # "one bidang" comparison and bar chart only with the other analyses
            _out += [
                mo.md(
                    f"Jika semua luas dihitung sebagai **satu bidang** ({fmt(_luas_total)} Ha): {rp(_gabung)}. "
                    f"Dipisah per bidang lebih mahal {rp(_sk - _gabung)}, karena tiap bidang punya batas, "
                    "paket ATK, dan blok tarif penuh 0–10 Ha sendiri."
                ),
                _bar,
            ]
    mo.vstack(_out)
    return (bidang,)


@app.cell
def _(bidang, fmt, mo):
    # numbered labels stay unique even if two bidang share a name
    pilihan_bidang = {"Total semua bidang": -1} | {
        f"{i + 1}. {nama} ({fmt(ha)} Ha)": i for i, (nama, ha) in enumerate(zip(bidang["Bidang"], bidang["Luas (Ha)"]))
    }
    pilih_bidang = mo.ui.dropdown(list(pilihan_bidang), value="Total semua bidang", label="Tampilkan rincian untuk")
    return pilih_bidang, pilihan_bidang


@app.cell(hide_code=True)
def _(
    alt,
    bidang,
    df,
    fixed,
    fmt,
    lainnya,
    mo,
    opsi2,
    opsi2_blok,
    pd,
    pilih_bidang,
    pilihan_bidang,
    rp,
    tampil_flat,
    var_ha,
):
    # per-item: fixed items once per bidang; per-Ha items share each bidang's koef cost by their price weight
    _idx = pilihan_bidang.get(pilih_bidang.value, -1)  # stale/empty selection -> total
    _sel = bidang if _idx < 0 else bidang.iloc[[_idx]]
    _n, _ha = len(_sel), _sel["Luas (Ha)"].sum()
    _var_sk = sum(opsi2(h, var_ha) for h in _sel["Luas (Ha)"])

    _is_var = df.kategori_biaya == "Variable Cost"
    _rinci = df[["sub_komponen", "item", "kategori_biaya"]].copy()
    _rinci["Flat"] = (df.jumlah * _ha).where(_is_var, df.jumlah * _n)
    _rinci["Simulasi Koefisien"] = (df.jumlah / var_ha * _var_sk).where(_is_var, df.jumlah * _n)
    _rinci.loc[len(_rinci)] = ["", "Total", "", _rinci["Flat"].sum(), _rinci["Simulasi Koefisien"].sum()]
    assert round(_rinci["Simulasi Koefisien"].iloc[-1]) == round(_n * fixed + _var_sk)
    _kolom = ["Flat", "Simulasi Koefisien"] if tampil_flat.value else ["Simulasi Koefisien"]
    _tabel = _rinci.assign(**{k: _rinci[k].map(rp) for k in _kolom})[
        ["sub_komponen", "item", "kategori_biaya", *_kolom]
    ].rename(columns={"sub_komponen": "Komponen", "item": "Item", "kategori_biaya": "Kategori"})

    # per-block: where the koef cost comes from (summed over the selected bidang)
    _blok = pd.DataFrame([b for h in _sel["Luas (Ha)"] for b in opsi2_blok(h, var_ha)])
    _judul = f"{_n} bidang, {fmt(_ha)} Ha" if _idx < 0 else pilih_bidang.value
    _out = [mo.md("## Rincian Biaya"), pilih_bidang]
    if _n:
        _blok = _blok.groupby(["blok", "koef"], sort=False, as_index=False)[["ha", "biaya"]].sum()
        _bar = alt.Chart(_blok, title=f"Simulasi Koefisien per Blok Luas ({_judul})").mark_bar().encode(
            x=alt.X("biaya:Q", title="Biaya (Rp)", axis=alt.Axis(format=",.0f")),
            y=alt.Y("blok:N", title=None, sort=None),
            tooltip=["blok", "koef", alt.Tooltip("ha:Q", format=",.1f", title="Ha di blok ini"),
                     alt.Tooltip("biaya:Q", format=",.0f")],
        ).properties(width="container")
        _out.append(mo.ui.table(_tabel, selection=None, pagination=False))
        if lainnya.value:  # ATK note and block chart only with the other analyses
            _out += [mo.md(f"ATK dihitung sekali per bidang ({_n} × {rp(fixed)})."), _bar]
    mo.vstack(_out)
    return


@app.cell
def _(mo, tampil_flat):
    lainnya = mo.ui.switch(label="Tampilkan analisis lainnya (grafik per bidang & per blok, simulasi 1 bidang, √Luas)")
    mo.vstack([mo.md("---"), tampil_flat, lainnya])
    return (lainnya,)


@app.cell
def _(mo):
    # shared state keeps slider and number input in sync
    get_luas, set_luas = mo.state(100)
    return get_luas, set_luas


@app.cell
def _(get_luas, mo, set_luas):
    # ponytail: inputs must live in their own cell (marimo only reruns *other* cells on change); shown below with the chart
    luas_slider = mo.ui.slider(1, 5_000, value=get_luas(), label="Luas (Ha)", full_width=True, on_change=set_luas)
    luas_input = mo.ui.number(1, 5_000, value=get_luas(), on_change=set_luas)
    tampil = mo.ui.multiselect(["Flat", "Simulasi Koefisien"], value=["Flat", "Simulasi Koefisien"], label="Tampilkan garis")
    log_x = mo.ui.switch(label="Log scale sumbu X (luas)")
    log_y = mo.ui.switch(label="Log scale sumbu Y (biaya)")
    return log_x, log_y, luas_input, luas_slider, tampil


@app.cell(hide_code=True)
def _(
    alt,
    fixed,
    get_luas,
    lainnya,
    log_x,
    log_y,
    luas_input,
    luas_slider,
    mo,
    opsi2,
    pct,
    pd,
    rp,
    tampil,
    var_ha,
):
    luas = get_luas() or 1  # number box can be cleared -> None
    # Simulasi Koefisien here: ATK stays fixed, koef only discounts the per-Ha items
    # (differs from the sheet, which also discounts ATK: ~1.7% lower)
    biaya_opsi2 = lambda ha: fixed + opsi2(ha, var_ha)

    # fixed axes over the full slider range; tier breakpoints added so Simulasi Koefisien's bends show exactly
    # extra small-area points keep the lines smooth when X is on log scale
    sim = pd.DataFrame({"luas": sorted({*range(0, 5_001, 50), 1, 2, 5, 10, 20, 100, 1_000})})
    if log_x.value:
        sim = sim[sim.luas > 0]  # log(0) is undefined
    sim["Flat"] = fixed + var_ha * sim.luas
    sim["Simulasi Koefisien"] = sim.luas.map(biaya_opsi2)
    sim = sim.melt("luas", var_name="skema", value_name="biaya")

    total = fixed + var_ha * luas
    total2 = round(biaya_opsi2(luas))
    assert luas != 100 or total2 == 55_605_000  # 30.000 + 1.710.000 x (10 + 90 x 0.25)
    pilih = pd.DataFrame({"luas": [luas, luas], "skema": ["Flat", "Simulasi Koefisien"], "biaya": [total, total2]})

    enc = dict(
        x=alt.X("luas:Q", title="Luas (Ha)", scale=alt.Scale(type="log" if log_x.value else "linear")),
        y=alt.Y("biaya:Q", title="Biaya (Rp)", axis=alt.Axis(format=",.0f"),
                scale=alt.Scale(type="log" if log_y.value else "linear")),
        color=alt.Color("skema:N", title="Skema"),
        tooltip=["skema", "luas", alt.Tooltip("biaya:Q", format=",.0f")],
    )
    sim, pilih = sim[sim.skema.isin(tampil.value)], pilih[pilih.skema.isin(tampil.value)]
    line = alt.Chart(sim, title="Simulasi Biaya vs Luas").mark_line().encode(**enc)
    titik = alt.Chart(pilih).mark_point(size=120, filled=True).encode(**enc)
    mo.vstack([
        mo.md("## Simulasi 1 Bidang: Flat vs Koefisien"),
        luas_slider,
        luas_input,
        tampil,
        mo.hstack([log_x, log_y], justify="start", gap=2),
        mo.md(f"**Total biaya {luas:,} Ha (flat): {rp(total)}**".replace(",", ".")),
        mo.md(f"Fixed Cost: {pct(fixed / total)} · Variable Cost: {pct(var_ha * luas / total)}"),
        mo.md(f"**Simulasi Koefisien (berjenjang): {rp(total2)}** · {total2 / total:.1%} dari flat · "
              f"rata-rata {rp(total2 / luas)}/Ha"),
        mo.md(f"Fixed Cost: {pct(fixed / total2)} · Variable Cost: {pct((total2 - fixed) / total2)}"),
        (line + titik).properties(width="container"),
    ]) if lainnya.value else None
    return luas, total2


@app.cell
def _(alt, df, fixed, lainnya, luas, mo, total2, var_ha):
    # cost per item at the selected area: fixed items once in both schemes;
    # per-Ha items x luas (Flat) or a share of the koefisien variable part by price weight
    _is_var = df.kategori_biaya == "Variable Cost"
    _label = df.sub_komponen + " · " + df["item"]  # ATK appears in both B and C
    _skema = {
        "Flat": df.jumlah.where(~_is_var, df.jumlah * luas),
        "Simulasi Koefisien": df.jumlah.where(~_is_var, df.jumlah / var_ha * (total2 - fixed)),
    }

    def _pie(nama, biaya):
        _judul = f"{nama}: {luas:,} Ha · Rp {round(biaya.sum()):,}".replace(",", ".")
        return alt.Chart(df.assign(label=_label, jumlah=biaya), title=_judul).mark_arc().encode(
            theta="jumlah:Q",
            color=alt.Color("label:N", title="Item"),
            tooltip=["label", alt.Tooltip("jumlah:Q", format=",.0f"),
                     alt.Tooltip("pct:Q", format=".2%", title="porsi")],
        ).transform_joinaggregate(total="sum(jumlah)").transform_calculate(pct="datum.jumlah / datum.total")

    mo.vstack([
        mo.md("### Komposisi Biaya (luas pada slider)"),
        alt.hconcat(*[_pie(n, b) for n, b in _skema.items()]).resolve_scale(color="shared"),
    ]) if lainnya.value else None
    return


@app.cell
def _(TIERS, df, lainnya, mo, rp):
    # Simulasi Koefisien per-Ha price of each per-Ha item in each area block (harga x koef); ATK is fixed, paid once
    per_ha = df[df.kategori_biaya == "Variable Cost"].set_index("item")[["harga_satuan"]]
    prev_b = 0
    for batas_b, koef_b in TIERS:
        kolom = (f"> {prev_b:,} Ha" if batas_b == float("inf") else f"{prev_b:,}–{batas_b:,} Ha").replace(",", ".")
        per_ha[f"{kolom} (x{koef_b:g})"] = per_ha.harga_satuan * koef_b
        prev_b = batas_b
    per_ha.loc["Total per Ha"] = per_ha.sum()
    per_ha = per_ha.rename(columns={"harga_satuan": "Harga Satuan"}).map(rp).reset_index(names="Item")

    atk = df.loc[df.kategori_biaya == "Fixed Cost", "jumlah"].sum()
    mo.vstack([
        mo.md("### Simulasi Koefisien: Biaya per Ha per Blok Luas"),
        mo.ui.table(per_ha, selection=None, pagination=False),
        mo.md(f"ATK (Fixed Cost) {rp(atk)} dibayar sekali per bidang, tidak per Ha."),
    ]) if lainnya.value else None
    return


@app.cell
def _(alt, lainnya, log_x, log_y, luas, mo, opsi2, pd):
    # compare Simulasi Koefisien's coefficients with sqrt(Area), both in "Ha setara tarif penuh":
    #   Simulasi Koefisien: sum of koef x Ha over the blocks  (= opsi2(ha, 1))
    #   sqrt:   sqrt(10 x Ha), scaled to equal Simulasi Koefisien at 10 Ha (end of the full-rate block)
    _ha = sorted({*range(0, 5_001, 50), 1, 2, 5, 10, 20, 100, 1_000})
    if log_x.value or log_y.value:
        _ha = [h for h in _ha if h > 0]  # log(0) undefined
    _model = {"√Luas (√(10 × Luas))": lambda h: (10 * h) ** 0.5, "Simulasi Koefisien (Σ koef × Ha)": lambda h: opsi2(h, 1)}
    akar = pd.DataFrame([{"luas": h, "garis": g, "setara": f(h)} for g, f in _model.items() for h in _ha])
    _pilih = pd.DataFrame([{"luas": luas, "garis": g, "setara": f(luas)} for g, f in _model.items()])

    _enc = dict(
        x=alt.X("luas:Q", title="Luas (Ha)", scale=alt.Scale(type="log" if log_x.value else "linear")),
        y=alt.Y("setara:Q", title="Ha setara tarif penuh", scale=alt.Scale(type="log" if log_y.value else "linear")),
        color=alt.Color("garis:N", title=None, sort=list(_model), legend=alt.Legend(orient="top")),
        tooltip=["garis", "luas", alt.Tooltip("setara:Q", format=",.1f", title="Ha setara")],
    )
    _chart = (alt.Chart(akar, title="Apakah Simulasi Koefisien mengikuti √Luas?").mark_line().encode(**_enc)
              + alt.Chart(_pilih).mark_point(size=120, filled=True).encode(**_enc)
              ).properties(width="container")
    _rasio = opsi2(luas, 1) / (10 * luas) ** 0.5

    _f = lambda x, d=0: f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    mo.vstack([
        mo.md(
            "### Mengapa biaya mengikuti panjang batas\n"
            "Pada PBT luasan (ulayat, HPL), tim mengukur **batas luar** satu bidang besar: menyusuri batas, "
            "memasang patok, mengambil koordinat GNSS di titik sudut, dan menyepakati batas dengan tetangga. "
            "Bagian dalam tidak diukur meter demi meter, jadi hari kerja lapangan bergantung pada **km batas**.\n\n"
            "Untuk bentuk apa pun: **keliling = c × √luas**. c ≈ 3,5 (lingkaran), 4 (persegi), "
            "6–8 (batas ulayat tidak beraturan mengikuti sungai/punggungan). Bentuk tidak beraturan berarti "
            "lebih banyak km, tetapi tetap tumbuh dengan √luas."
        ),
        _chart,
        mo.md(
            f"Pada **{_f(luas)} Ha**: √luas = {_f(luas ** 0.5, 2)} "
            f"(batas persegi ≈ {_f(0.4 * luas ** 0.5, 1)} km). "
            "Luas 100× lebih besar → batas hanya 10× lebih panjang."
        ),
        mo.md(
            f"Simulasi Koefisien pada {_f(luas)} Ha = **{_f(opsi2(luas, 1), 1)} Ha setara** vs √Luas "
            f"{_f((10 * luas) ** 0.5, 1)} → **{_f(_rasio * 100, 0)}%** dari kurva √Luas "
            "(>100% = lebih mahal dari model batas, <100% = lebih murah)."
        ),
    ]) if lainnya.value else None
    return


if __name__ == "__main__":
    app.run()
