"""Revise only Ver.1 slides 15-18, preserving all other package parts."""
from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import re
import subprocess
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

TASK = Path(__file__).resolve().parent
ROOT = TASK.parents[1]
BUILD = TASK / ".build/ver2_slides"
ASSETS = BUILD / "assets"
BLUE, INK = "#17365D", "#263746"
ORIGINAL = TASK / "slides/seminar_ver1.pptx"
FINAL = TASK / "slides/seminar_ver2.pptx"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
TARGETS = [15, 16, 17, 18]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def protect() -> list[dict]:
    baseline = json.loads((TASK / "ver2_protected_inputs.json").read_text(encoding="utf-8"))
    expected = []
    for name, digest in baseline.items():
        p = (TASK / name).resolve()
        assert p.is_relative_to(ROOT) and sha(p.read_bytes()) == digest, name
        expected.append(dict(path=p.relative_to(ROOT).as_posix(), sha256=digest))
    manifest = BUILD / "protected_inputs.json"
    if not manifest.exists():
        manifest.write_text(json.dumps(expected, indent=2), encoding="utf-8")
    records = json.loads(manifest.read_text(encoding="utf-8"))
    assert records == expected, "Private protection manifest differs from the public pre-work hashes."
    return records


def formula(name: str, latex: str) -> str:
    path = ASSETS / (name + ".png")
    fig = plt.figure(figsize=(12, 1.6), dpi=260)
    fig.patch.set_alpha(0)
    fig.text(.01, .5, "$" + latex + "$", fontsize=32, color=BLUE,
             va="center", math_fontfamily="stix")
    fig.savefig(path, transparent=True, bbox_inches="tight", pad_inches=.08)
    plt.close(fig)
    return path.relative_to(TASK).as_posix()


def text(value, x, y, w, h, size=21, color=INK, bold=False, math=False):
    if math:
        value = re.sub(r"([A-Za-z])_([A-Za-z0-9]+)", r"\1_{\2}", value)
        value = re.sub(r"\^([A-Za-z0-9]+)", r"^{\1}", value)
    return dict(kind="text", text=value, x=x, y=y, w=w, h=h, size=size,
                color=color, bold=bold, math=math)


def image(path, x, y, w, h, alt):
    return dict(kind="image", path=path, x=x, y=y, w=w, h=h, alt=alt)


def official_figure():
    """Direct official-PDF crop. No plot extraction, redrawing or data inference."""
    source = TASK / "sources_local/papers/spp_supplement.pdf"
    rendered = ASSETS / "sm-page3"
    subprocess.run(["pdftoppm", "-f", "3", "-l", "3", "-singlefile", "-r", "340",
                    "-png", str(source), str(rendered)], check=True)
    original = Image.open(rendered.with_suffix(".png"))
    point_box = (102, 48, 519, 203)
    scale = original.width / 612
    pixel_box = tuple(round(v * scale) for v in point_box)
    cropped = original.crop(pixel_box)
    path = ASSETS / "fig_s1_ab_direct.png"
    cropped.save(path)
    assert sha(path.read_bytes()) == "8ce89bec8d31cd046c9c6e231bd38196e60d4a1fe770cbe2cbdf1f3fe50efdc8"
    with zipfile.ZipFile(ORIGINAL) as package:
        old_figure_bytes = []
        for rel in ET.fromstring(package.read("ppt/slides/_rels/slide18.xml.rels")):
            if rel.attrib["Type"].endswith("/image"):
                target = posixpath.normpath(posixpath.join("ppt/slides", rel.attrib["Target"]))
                old_figure_bytes.append(package.read(target))
    assert path.read_bytes() in old_figure_bytes, "Fresh official crop differs from Ver.1's embedded plot."
    report = dict(source=source.relative_to(ROOT).as_posix(), source_sha256=sha(source.read_bytes()),
                  pdf_page=3, render_dpi=340, crop_box_pdf_points=point_box, crop_box_pixels=pixel_box,
                  image_dimensions=cropped.size, crop_sha256=sha(path.read_bytes()),
                  method="pdftoppm full-page rasterization, then direct rectangular PIL crop; no redraw or resampling",
                  old_slide18_image_bytes_equal=True)
    (BUILD / "source_figure_ver2.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return path.relative_to(TASK).as_posix()


def prepare():
    ASSETS.mkdir(parents=True, exist_ok=True)
    protected = protect()
    definitions = {
        "s9": r"p_c=p_c(N)+bN^{-1/\bar\nu}\qquad\mathrm{(S9)}",
        "zero": r"u=(p_c-p_c)N^{1/\bar\nu}=0",
        "at_zero": r"\langle P(p_c,N)\rangle=N^{-\beta/\bar\nu}F^{(1)}(0)",
        "s10": r"P(p_c)=\langle P(p=p_c,N)\rangle\sim N^{-\beta/\bar\nu}\qquad\mathrm{(S10)}",
        "s11": r"P_c(N)=\langle P(p=p_c(N),N)\rangle\sim N^{-\beta/\bar\nu}\qquad\mathrm{(S11)}",
        "s12": r"S_c(N)=\langle S(p=p_c(N),N)\rangle\sim N^{\gamma/\bar\nu}\qquad\mathrm{(S12)}",
        "minus_b": r"u=[p_c(N)-p_c]N^{1/\bar\nu}=-b",
    }
    f = {key: formula("eq_" + key, val) for key, val in definitions.items()}
    figure = official_figure()
    slides = []
    sm = "Kim & Radicchi (2024), Supplemental Material "

    def add(id, title, elements, source, notes):
        slides.append(dict(id=id, title=title, elements=elements, footer=source,
                           notes=notes, header=True))

    add(15, "臨界点と疑似臨界点の関係", [
        text("有限サイズの疑似臨界点p_c(N)と、無限サイズの臨界点p_cの\n関係を、FSSでは次のように表す。", 50, 121, 860, 65, 22, INK, False, True),
        image(f["s9"], 70, 210, 820, 86, definitions["s9"]),
        text("b：サイズNに依存しない係数。符号は限定しない。", 50, 333, 860, 33, 22),
        text("p_c(N)とp_cのずれを、Nのべき乗で表すシフト則。\n複数サイズのp_c(N)を調べ、p_cと1/ν̄を推定する。", 50, 398, 860, 65, 23, BLUE, False, True),
    ], sm + "IV.A・IV.B、PDF3–4／印刷3–4、式(S7)–(S9)。導出と前提は板書へ。",
    "【原論文の内容】Supplemental Material IV.AのS9はp_c=p_c(N)+bN^{-1/ν̄}。bはNによらない係数で符号を限定しない。複数サイズの疑似臨界点から極限の臨界点とシフト指数の情報を得る。著者の実際の解析順序ではPのべき乗当てはまりからp_cを先に推定し、そのp_cとp_c(N)の差から1/ν̄、bを推定する（IV.B PDF3–4）。本スライドは同時非線形フィットを実施したとの主張ではない。【説明用の数学的補足】S7でu=(p-p_c)N^{1/ν̄}。N固定では前因子N^{γ/ν̄}はpによらない正定数。サイズに依存しない関数F^{(2)}のピークu_*がスケーリング領域内にあり、有限サイズ補正・離散化・観測範囲端の影響を無視できるなら、S8の平均Sピーク位置はu_*=[p_c(N)-p_c]N^{1/ν̄}に対応する。p_c(N)-p_c=u_*N^{-1/ν̄}、b=-u_*と定義すればS9を得る。これは原文に記載された厳密導出ではなく、FSS仮定の数学的説明。ν̄>0かつb有限ならN→∞でずれが0になりp_c(N)→p_cだが、S9を書くだけでν̄>0を証明するわけではない。b≠0なら対数シフトの傾きは-1/ν̄。2D制限なしSPPでの指数や転移次数は別途検討する。")

    add(16, "臨界点でのサイズ依存性", [
        text("式(S6)においてp=p_cとすると、\nスケーリング関数の引数は0となる。", 50, 121, 860, 63, 22, INK, False, True),
        image(f["zero"], 110, 191, 740, 54, definitions["zero"]),
        image(f["at_zero"], 100, 265, 760, 59, definitions["at_zero"]),
        image(f["s10"], 50, 341, 860, 65, definitions["s10"]),
        text("F⁽¹⁾(0)が有限かつ非零なら、Pのサイズ依存性として\nこのNのべき乗則が得られる。", 50, 424, 860, 55, 20),
    ], sm + "IV.B、PDF3／印刷3、式(S10)。P(p_c)はN依存を省略した平均Pの原文記法。",
    "【原論文の内容】S10の原文はP(p_c)=〈P(p=p_c,N)〉〜N^{-β/ν̄}。原文のP(p_c)はN依存を省略した平均Pの記法。全サイズで共通のp_cを用い、Nごとに移動するp_c(N)での評価とは区別する。【説明用の数学的補足】S6のu=(p-p_c)N^{1/ν̄}にp=p_cを代入する理由は引数を0に固定するため。〈P(p_c,N)〉=N^{-β/ν̄}F^{(1)}(0)=A_0N^{-β/ν̄}〜N^{-β/ν̄}。A_0=F^{(1)}(0)はNによらない有限の正定数とする。Pが非負なので有限非零を正定数として解釈する。ここでは代入の論理を説明し、グラフの軸や候補pごとの回帰は説明しない。p_cは最初から既知とは限らず、数値推定は次のFig.S1(a)(b)で説明する。FSSの仮定からの関係であり、SPP転移次数の証明ではない。")

    add(17, "疑似臨界点での臨界指数推定", [
        text("p_c(N)：", 50, 120, 140, 29, 20, BLUE, True, True),
        text("サイズNで、試行平均したSが最大となる辺の削除率", 200, 120, 710, 29, 20),
        text("P_c(N)：", 50, 150, 140, 29, 20, BLUE, True, True),
        text("その削除率での、最大連結成分の割合Pの試行間平均", 200, 150, 710, 29, 20),
        text("S_c(N)：", 50, 180, 140, 29, 20, BLUE, True, True),
        text("同じ削除率での、平均クラスターサイズSの試行間平均", 200, 180, 710, 29, 20),
        image(f["s11"], 50, 223, 860, 53, definitions["s11"]),
        image(f["s12"], 50, 284, 860, 53, definitions["s12"]),
        text("＝：観測量の定義　～：FSSに基づくサイズ依存性", 50, 348, 860, 26, 18),
        image(f["minus_b"], 50, 382, 440, 46, definitions["minus_b"]),
        text("S9より引数が一定となるため、S6・S7から\nべき乗のサイズ依存性が得られる。", 520, 379, 390, 54, 18),
        text("Sは試行内での平均、〈S〉はさらに試行間の平均。\n添字cは評価位置を表し、経路長上限Cとは別。", 50, 439, 860, 45, 16.5),
    ], sm + "IV.B、PDF4／印刷4、式(S11)・(S12)。有限・非零の関数値を仮定。",
    "【原論文の内容】S11はP_c(N)=〈P(p=p_c(N),N)〉〜N^{-β/ν̄}、S12はS_c(N)=〈S(p=p_c(N),N)〉〜N^{γ/ν̄}。p_c(N)はS8の試行平均S最大位置であり、各試行のピーク位置を先に平均した量ではない。Pは最大連結成分そのものではなくその割合、Sは平均クラスターサイズでありクラスタリング係数ではない。Sは1試行内で最大成分1個を除いて計算する頂点重みの平均、〈S〉はさらに異なる試行間での平均。添字cは臨界・疑似臨界の評価位置を表し、SPPの経路長上限Cとは別の記号。式の最初の等号は観測量の定義、右側の〜はFSSに基づくサイズ依存性。【説明用の数学的補足】S9をp_c(N)-p_c=-bN^{-1/ν̄}と変形。p=p_c(N)ならu=[p_c(N)-p_c]N^{1/ν̄}=(-bN^{-1/ν̄})N^{1/ν̄}=-b。Nごとにp_c(N)は異なるが引数uは一定。S6/S7へ代入するとP_c(N)=N^{-β/ν̄}F^{(1)}(-b)、S_c(N)=N^{γ/ν̄}F^{(2)}(-b)。両関数値がNによらない有限非零値で、主要なスケーリング関係として成立するなら、表示のべき乗則になる。サイズ依存から推定するのはβ/ν̄、γ/ν̄という指数比であり、個々の指数がすべて直接決まるわけではない。前ページの固定p_cでの評価との違いを説明する。")

    add(18, "原論文の臨界点推定：C=1", [
        text("候補pごとにlog Nとlog〈P〉を切片ありの単回帰し、Pearson相関係数rを求める。\n(a) r²はその二乗の決定係数。1に近いほど直線に沿い、黄色ひし形の最大位置を採用。\n(b) 推定したp_cと前後を比較し、黒の条件のべき乗当てはまりが最良であることを確認。", 50, 410, 860, 75, 17, INK, False, True),
        image(figure, 35, 126, 735, 273,
              "Official Supplemental Material PDF3 Fig.S1(a)(b), direct 340dpi crop; original axes, markers, lines and legend unchanged"),
        text("ER上の原図\np_c=0.750\nΔ=0.005\n黒：0.750\n紫：0.745\n赤：0.755", 790, 161, 140, 190, 17.5, BLUE, False, True),
    ], sm + "III・IV.B、PDF2–3／印刷2–3、Fig.S1(a)(b)。補足原PDFから直接抽出（著者公開版と同一）。",
    "【原論文の内容と原図】公式Supplemental Material PDF3 Fig.S1(a)(b)を直接引用。公式論文ページからリンクされる著者公開supplementary.pdfとローカルPDFのSHA一致を独立確認した記録はboard/source_check_ver2.mdに示す。グラフは再作図せず、340dpiの全頁をPDF点座標(102,48,519,203)で直接切り抜いた画像。Ver.1のslide18埋込PNGともバイト・画素一致。元の軸、点、線、マーカー、色、凡例を保ち、等方的な拡大縮小のみ行う。C=1のERネットワークの結果で、2D格子の測定結果ではない。候補pごとにX_i=log N_i、Y_i=log〈P(p,N_i)〉を用い、切片ありの単回帰Y_i≈a+ζX_iを行う。原文SecIIIのrは、この対数変換後のX,YのPearson相関係数。pとr²との相関ではない。分散が非零のデータについてr=Σ_i[(X_i-X̄)(Y_i-Ȳ)]/sqrt(Σ_i(X_i-X̄)² Σ_i(Y_i-Ȳ)²)。一般的な数学補足として、切片ありの単回帰でr²は決定係数となり0以上1以下。傾きが負ならrは負にもなる。(a)は各候補pに対応するr²を示し、黄色のひし形の最大位置からp_c=0.750を推定する。(b)はその結果をサイズ依存で確認するもので、独立した別手法ではない。Δ=.005、黒四角はp=.750、紫丸はp=.745、赤三角はp=.755、黄色の破線は最良べき乗当てはめ。原図では黒がほぼ直線、紫は大きいNで緩やかになり、赤は下側へ曲がる。原文はp=p_cが最もよいべき乗当てはめを与えると説明する。r²が高いだけで真の臨界点・物理的べき乗則・転移次数を厳密に証明するわけではない。p_cは複数サイズのPから推定する無限系の臨界点で、S8の有限Nごとのp_c(N)とは区別する。")

    assert [s["id"] for s in slides] == TARGETS
    payload = dict(canvas=[960, 540], font="Meiryo", slides=slides, total_slides=23,
                   scope="Only slides 15-18 and their speaker notes", equations=definitions,
                   protected_inputs=protected, official_figure=figure)
    (BUILD / "deck_ver2.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Prepared only slides 15-18, keeping 23 slides and the original paired Fig.S1(a)(b).")


def merge(candidate: Path):
    """Replace four slide/notes XML and their slide rels; preserve everything else."""
    protect()
    replacement, additions = {}, {}
    with zipfile.ZipFile(ORIGINAL) as old, zipfile.ZipFile(candidate) as draft:
        old_names = set(old.namelist())
        definitions = json.loads((BUILD / "deck_ver2.json").read_text(encoding="utf-8"))["slides"]
        for index, i in enumerate(TARGETS):
            slide = f"ppt/slides/slide{i}.xml"
            current_text = "".join(node.text or "" for node in ET.fromstring(draft.read(slide)).iter(
                "{http://schemas.openxmlformats.org/drawingml/2006/main}t"))
            assert definitions[index]["title"] in current_text, (i, "candidate title missing")
            intro = definitions[index]["elements"][0]["text"].replace("\n", "").replace("\r", "")
            # Math source markup is stored as native runs without braces.
            intro = re.sub(r"[_^]\{([^}]+)\}", r"\1", intro)
            assert intro in current_text.replace("\n", "").replace("\r", ""), (i, "revised introduction absent")
            replacement[slide] = draft.read(slide)
            replacement[f"ppt/notesSlides/notesSlide{i}.xml"] = draft.read(f"ppt/notesSlides/notesSlide{i}.xml")
            relpart = f"ppt/slides/_rels/slide{i}.xml.rels"
            reltree = ET.fromstring(draft.read(relpart))
            original_nonimages = {r.attrib["Type"]: r.attrib["Target"] for r in ET.fromstring(old.read(relpart))
                                  if not r.attrib["Type"].endswith("/image")}
            for j, rel in enumerate(reltree):
                if rel.attrib["Type"].endswith("/image"):
                    target = posixpath.normpath(posixpath.join("ppt/slides", rel.attrib["Target"]))
                    data = draft.read(target)
                    assert Path(target).suffix.lower() == ".png", target
                    name = f"ppt/media/ver2_slide{i}_image{j}.png"
                    assert name not in old_names, name
                    additions[name] = data
                    rel.attrib["Target"] = "../media/" + posixpath.basename(name)
                else:
                    assert rel.attrib["Type"] in original_nonimages, rel.attrib
                    assert rel.attrib["Target"] == original_nonimages[rel.attrib["Type"]], rel.attrib
            ET.register_namespace("", REL_NS)
            replacement[relpart] = ET.tostring(reltree, encoding="utf-8", xml_declaration=True)
            noterels = f"ppt/notesSlides/_rels/notesSlide{i}.xml.rels"
            assert old.read(noterels) == draft.read(noterels), noterels
        assert b'Extension="png"' in old.read("[Content_Types].xml")
        FINAL.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(FINAL, "w", compression=zipfile.ZIP_DEFLATED) as out:
            for entry in old.infolist():
                out.writestr(entry, replacement.get(entry.filename, old.read(entry.filename)))
            for name, data in additions.items():
                out.writestr(name, data)
    unchanged = []
    with zipfile.ZipFile(ORIGINAL) as old, zipfile.ZipFile(FINAL) as new:
        for name in old.namelist():
            if name not in replacement:
                assert old.read(name) == new.read(name), name
                unchanged.append(name)
        for i in list(range(1, 15)) + list(range(19, 24)):
            for name in [f"ppt/slides/slide{i}.xml", f"ppt/slides/_rels/slide{i}.xml.rels",
                         f"ppt/notesSlides/notesSlide{i}.xml", f"ppt/notesSlides/_rels/notesSlide{i}.xml.rels"]:
                assert name in unchanged, name
        assert new.testzip() is None
    result = dict(status="PASS", revised_slides=TARGETS, unchanged_slide_count=19,
                  changed_original_parts=sorted(replacement), added_media_parts=sorted(additions),
                  all_other_original_parts_byte_identical=True, unchanged_original_parts=len(unchanged),
                  original_sha256=sha(ORIGINAL.read_bytes()), final_sha256=sha(FINAL.read_bytes()))
    (BUILD / "package_preservation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    protect()
    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--merge", type=Path)
    args = parser.parse_args()
    if args.merge:
        merge(args.merge.resolve())
    else:
        prepare()
