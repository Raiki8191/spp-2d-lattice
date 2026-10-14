"""Revise Ver.2 slides 19, 20, 23 only; preserve slides 1-18, 21, 22 exactly."""
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
BUILD = TASK / ".build/ver3_slides"
ASSETS = BUILD / "assets"
BLUE, INK = "#17365D", "#263746"
ORIGINAL = TASK / "slides/seminar_ver2.pptx"
FINAL = TASK / "slides/seminar_ver3.pptx"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
TARGETS = [19, 20, 23]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def protect() -> list[dict]:
    baseline = json.loads((TASK / "ver3_protected_inputs.json").read_text(encoding="utf-8"))
    expected = []
    for name, digest in baseline.items():
        p = (TASK / name).resolve()
        assert p.is_relative_to(ROOT) and sha(p.read_bytes()) == digest, name
        expected.append(dict(path=p.relative_to(ROOT).as_posix(), sha256=digest))
    manifest = BUILD / "protected_inputs.json"
    if not manifest.exists():
        manifest.write_text(json.dumps(expected, indent=2), encoding="utf-8")
    records = json.loads(manifest.read_text(encoding="utf-8"))
    assert records == expected, "Protection manifest differs from the public pre-work hashes."
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


def original_figures():
    """Direct PDF crops with byte comparison against the existing embedded PNGs."""
    source = TASK / "sources_local/papers/spp_supplement.pdf"
    crops = {
        "fig_s1_cd": (3, (102, 204, 519, 356), [19]),
        "fig_s2_a": (4, (50, 188, 146, 295), [20]),
        "fig_s2_bc": (4, (146, 188, 335, 295), [21]),
        "fig_s2_de": (4, (335, 188, 520, 295), [22]),
        "fig_s2_legend": (4, (522, 215, 568, 256), [20, 21, 22]),
        "table_s2": (4, (145, 407, 468, 497), [23]),
    }
    pages = {}
    for page in [3, 4]:
        rendered = ASSETS / f"sm-page{page}"
        subprocess.run(["pdftoppm", "-f", str(page), "-l", str(page), "-singlefile", "-r", "340",
                        "-png", str(source), str(rendered)], check=True)
        pages[page] = Image.open(rendered.with_suffix(".png"))
    paths, records = {}, []
    with zipfile.ZipFile(ORIGINAL) as package:
        for name, (page, point_box, slide_numbers) in crops.items():
            original = pages[page]
            scale = original.width / 612
            pixel_box = tuple(round(v * scale) for v in point_box)
            cropped = original.crop(pixel_box)
            path = ASSETS / (name + "_direct.png")
            cropped.save(path)
            matched = []
            for slide in slide_numbers:
                for rel in ET.fromstring(package.read(f"ppt/slides/_rels/slide{slide}.xml.rels")):
                    if rel.attrib["Type"].endswith("/image"):
                        target = posixpath.normpath(posixpath.join("ppt/slides", rel.attrib["Target"]))
                        if package.read(target) == path.read_bytes():
                            matched.append(dict(slide=slide, target=target))
            assert len({m["slide"] for m in matched}) == len(slide_numbers), (name, "Fresh crop differs from the embedded original.")
            records.append(dict(name=name, pdf_page=page, crop_box_pdf_points=point_box,
                                crop_box_pixels=pixel_box, dimensions=cropped.size,
                                sha256=sha(path.read_bytes()), matching_ver2_embedded_images=matched))
            paths[name] = path.relative_to(TASK).as_posix()
    (BUILD / "source_figures_ver3.json").write_text(json.dumps(dict(
        source=source.relative_to(ROOT).as_posix(), source_sha256=sha(source.read_bytes()),
        render_dpi=340, method="pdftoppm full page, then direct rectangular crop; no redrawing or resampling",
        figures=records), indent=2), encoding="utf-8")
    return paths


def prepare():
    ASSETS.mkdir(parents=True, exist_ok=True)
    protected = protect()
    definitions = {
        "s9": r"p_c=p_c(N)+bN^{-1/\bar\nu}\qquad\mathrm{(S9)}",
        "s9_absolute_derived": r"|p_c-p_c(N)|=|b|N^{-1/\bar\nu}",
    }
    f = {key: formula("eq_" + key, val) for key, val in definitions.items()}
    sources = original_figures()
    slides = []
    sm = "Kim & Radicchi (2024), Supplemental Material "

    def add(id, title, elements, source, notes):
        slides.append(dict(id=id, title=title, elements=elements, footer=source,
                           notes=notes, header=True))

    add(19, "原論文の臨界点推定：制限なし", [
        text("(c) C=1と同じ回帰法。r²軸は約0.7〜1へ拡大（図(a)と異なる）。\n(d) p_cと前後のPのサイズ依存を比較する。\n著者の評価：固定p_cの指数には強い有限サイズ効果がある。\np_cの推定はその影響を受けないと評価するが、数学的な証明ではない。", 50, 394, 860, 92, 17, INK, False, True),
        image(sources["fig_s1_cd"], 35, 124, 735, 265,
              "SM PDF3 Fig.S1(c)(d), direct original crop; axes, markers, lines and colors unchanged"),
        text("ER・C=∞\n設定：C=N\np_c=0.646\nΔ=0.01\n黒：0.646\n紫：0.636\n赤：0.656", 790, 148, 140, 175, 17.5, BLUE, False, True),
    ], sm + "IV.B、PDF3／印刷3、Fig.S1(c)(d)。補足原PDFから直接抽出（著者公開版と同一）。",
    "【原論文の内容】C=1と同じ方法を制限なしに適用する。原図の表示C=∞、数値設定C=N。有限グラフの最短経路は単純な経路で長さN−1以下なのでC=Nは長さの制限にならない。Fig.S1(c)は候補pごとのlog Nとlog平均Pの回帰に基づくr²を示し、その最大位置でp_c=.646を推定する。rの定義は18で説明済みなので繰り返さない。r²の表示軸は約.7〜1.0で、C=1の(a)とは異なる。Fig.S1(d)は推定値と前後のサイズ依存を比較する一続きの確認図で、独立した別手法ではない。黒四角p=.646、紫丸p=.636、赤三角p=.656、Δ=.01。元の軸、点、線、色、マーカーを変更しない。IV.Bでは制限なしの固定p_cで得た臨界指数が強い有限サイズ効果を受ける一方、p_cの推定はその影響を受けないと著者が評価する。これは著者の数値解析上の評価であり、有限サイズ効果が一切ないとの数学的証明ではない。原則として板書はせず図を指す。ERの結果を本研究の2D格子の測定値として説明しない。")

    add(20, "疑似臨界点の有限サイズシフト", [
        text("式(S9)からの変形", 375, 218, 535, 30, 21, BLUE, True),
        image(sources["fig_s2_a"], 35, 126, 285, 320,
              "SM PDF4 Fig.S2(a), original plot including axis display factor, points and fits unchanged"),
        image(f["s9"], 365, 126, 545, 69, definitions["s9"]),
        image(f["s9_absolute_derived"], 365, 259, 545, 61, definitions["s9_absolute_derived"]),
        text("p_cとp_c(N)のずれを\nNに対して調べる。\n両対数の傾き−1/ν̄から\n1/ν̄を推定する。", 375, 345, 355, 110, 19, BLUE, False, True),
        image(sources["fig_s2_legend"], 755, 342, 155, 125,
              "Original shared Fig.S2 legend, unchanged C=1,2,3,infinity"),
    ], sm + "IV.B、PDF4／印刷4、Fig.S2(a)・式(S9)。絶対値の式は説明用の代数変形。",
    "【原論文の内容】原図Fig.S2(a)はp_cとp_c(N)のずれの大きさをNに対して示す両対数図。S9のp_c=p_c(N)+bN^{-1/ν̄}を用いてシフト指数1/ν̄を推定する。点は平均S曲線から定めたp_c(N)に基づく結果、線は対数変換したデータへの回帰、誤差棒は混雑回避のため原図で省略されている。【説明用の数学的補足】p_c-p_c(N)=bN^{-1/ν̄}から|p_c-p_c(N)|=|b|N^{-1/ν̄}を得る。絶対値の式はS9からの変形であり、独立の原論文の式番号を付けない。b≠0かつ対数を取る縦軸値が正であることを前提とする。絶対値からbの符号は分からない。原図の表示倍率10^Xの説明は板書へ移す。各C系列内でXは固定し、C=1,2,3,N（原図表示∞）にX=0,1,2,3を用い、それぞれ1,10,100,1000で割る。ここでのXはスライド10の対数変数Xとは別記号。Y(N)=AN^αならlog[Y(N)/10^X]=log[AN^α/10^X]=αlogN+logA−Xlog10。固定Xによる表示倍率は切片だけを変え、Nに対する傾きαを変えない。この図ではα=−1/ν̄。SPPの操作からの厳密な証明ではなく、FSSと一般的な代数に基づく説明である。")

    add(23, "原論文の推定値と2D格子との区別", [
        text("Table S2：補足資料の第2表。ERネットワークのFSS推定値。\ncritical：共通のp_c　／　pseudo-critical：Nごとのp_c(N)\n評価位置の区別であり、連続・不連続の分類ではない。\n制限なしは両方法の指数比に大きな差。著者は固定p_cでの強い有限サイズ効果を指摘。\nTable Iは各試行の最大単一辺落下を基準とするevent-basedで、推定方法が異なる。", 50, 352, 860, 131, 18.5, INK, False, True),
        image(sources["table_s2"], 55, 117, 850, 228,
              "SM PDF4 full Table S2, original headings, all C rows, numerical values and uncertainty digits unchanged"),
    ], sm + "IV.B、PDF4／印刷4、Table S2。主論文PDF2–3、Table I（event-based）。",
    "【原表と読み方】Table S2は補足資料の第2表という番号であり、物理量や解析方法の名前ではない。全行・全列・見出し・数値・誤差を保った原PDFの直接cropを掲載し、表を手作業で作り直さない。ERネットワークのconventional ensembleでのFSS推定値。Cは経路長上限、p_cは無限サイズ臨界点の推定、1/ν̄は疑似臨界点の有限サイズシフトの指数。criticalは全サイズで共通のp_cを使用（21に対応）、pseudo-criticalは平均Sが最大となるNごとのp_c(N)で評価（22に対応）。これらは連続転移・不連続転移の分類ではない。C=∞ではcriticalのβ/ν̄=.04±.01、γ/ν̄=.15±.01に対し、pseudo-criticalは.24±.01、.53±.01。C=1,2,3では両方法の推定値が比較的近い。数値の差そのものを有限サイズ効果の数学的証明とはしない。SM IV.Bは固定p_cでの制限なしの指数推定に強い有限サイズ効果があると著者が評価しており、数値上の差と著者の解釈を区別する。【主論文Table Iとの違い】主論文PDF2右段は、各試行で単一辺の削除によって最大成分に生じる最大の変化に対応する構成を抽出するevent-based ensembleと定義する。経路全体を削除する要求1回の最大request落下とは同じ定義ではない。SM IV.CのS13/S14は単一辺刻みでの落下直後p^+と直前p^-を区別する。各試行の最大単一辺落下位置とそこでの観測量を用いてから試行間で集計し、先に平均S曲線を作ってその最大位置を求めるTable S2のpseudo-criticalとは異なる。Table Iを直前または直後の一方だけの定義と、この表の記載のみから断定しない。主論文Table IのC=∞はp_c=.646±.001、β/ν̄=.21±.01、γ/ν̄=.55±.01。近い数値でも解析手順は同一ではない。【質問時補足】Table S2のC=1 pseudo-critical γ/ν̄は.35±.001、主論文PDF3左段は.35±.01であり、どちらが正しいかを推測して訂正しない。指数の±はSM IIIで残差正規性の下の回帰係数標準誤差と説明されるが、p_cの±まで同一方法と断定しない。これらはERの結果で、本研究の2D格子の不連続転移や無限系の有限ジャンプをこの表から証明しない。原則として板書せず該当列を指す。")

    assert [s["id"] for s in slides] == TARGETS
    payload = dict(canvas=[960, 540], font="Meiryo", slides=slides, total_slides=23,
                   scope="Only slides 19,20,23; slides 21,22 are preserved exactly",
                   revised_slide_numbers=TARGETS, preserved_slide_numbers=list(range(1,19))+[21,22],
                   equations=definitions, protected_inputs=protected, source_images=sources)
    (BUILD / "deck_ver3.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Prepared slides 19,20,23 only; keeping 23 slides and exact original slides 21,22.")


def merge(candidate: Path):
    """Replace three slides/notes XML and their slide rels; preserve all else."""
    protect()
    replacement, additions = {}, {}
    with zipfile.ZipFile(ORIGINAL) as old, zipfile.ZipFile(candidate) as draft:
        old_names = set(old.namelist())
        definitions = json.loads((BUILD / "deck_ver3.json").read_text(encoding="utf-8"))["slides"]
        for index, i in enumerate(TARGETS):
            slide = f"ppt/slides/slide{i}.xml"
            current_text = "".join(node.text or "" for node in ET.fromstring(draft.read(slide)).iter(
                "{http://schemas.openxmlformats.org/drawingml/2006/main}t"))
            assert definitions[index]["title"] in current_text, (i, "candidate title missing")
            intro = definitions[index]["elements"][0]["text"].replace("\n", "").replace("\r", "")
            intro = re.sub(r"[_^]\{([^}]+)\}", r"\1", intro)
            assert intro in current_text.replace("\n", "").replace("\r", ""), (i, "revised text absent")
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
                    name = f"ppt/media/ver3_slide{i}_image{j}.png"
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
        for i in list(range(1,19)) + [21,22]:
            for name in [f"ppt/slides/slide{i}.xml", f"ppt/slides/_rels/slide{i}.xml.rels",
                         f"ppt/notesSlides/notesSlide{i}.xml", f"ppt/notesSlides/_rels/notesSlide{i}.xml.rels"]:
                assert name in unchanged, name
        assert new.testzip() is None
    result = dict(status="PASS", revised_slides=TARGETS, unchanged_slide_count=20,
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
