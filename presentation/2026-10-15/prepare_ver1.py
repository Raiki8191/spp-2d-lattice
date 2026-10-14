"""Prepare only slides 11-14; transplant them into an otherwise exact old package."""
from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import re
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

TASK = Path(__file__).resolve().parent
ROOT = TASK.parents[1]
BUILD = TASK / ".build/ver1_slides"
ASSETS = BUILD / "assets"
BLUE, INK = "#17365D", "#263746"
ORIGINAL = TASK / "slides/seminar_with_fss.pptx"
FINAL = TASK / "slides/seminar_ver1.pptx"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def protect() -> list[dict]:
    paths = [
        TASK / "slides/seminar_with_fss.pptx",
        TASK / "slides/seminar_with_fss.pdf",
        TASK / "board/board_notes_with_fss.md",
        TASK / "board/board_notes_with_fss.pdf",
        TASK / "board/board_notes_01-10.md",
        TASK / "board/board_notes_01-10.pdf",
    ]
    public_baseline = json.loads((TASK / "ver1_protected_inputs.json").read_text(encoding="utf-8"))
    for p in paths:
        assert sha(p.read_bytes()) == public_baseline[p.relative_to(TASK).as_posix()], p
    manifest = BUILD / "protected_inputs.json"
    if not manifest.exists():
        manifest.write_text(json.dumps([
            dict(path=p.relative_to(ROOT).as_posix(), sha256=sha(p.read_bytes()))
            for p in paths], indent=2), encoding="utf-8")
    records = json.loads(manifest.read_text(encoding="utf-8"))
    for item in records:
        p = (ROOT / item["path"]).resolve()
        assert p.is_relative_to(ROOT) and sha(p.read_bytes()) == item["sha256"], item
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


def prepare():
    ASSETS.mkdir(parents=True, exist_ok=True)
    protected = protect()
    definitions = {
        "s6": r"\langle P(p,N)\rangle=N^{-\beta/\bar\nu}F^{(1)}[(p-p_c)N^{1/\bar\nu}]\qquad\mathrm{(S6)}",
        "s7": r"\langle S(p,N)\rangle=N^{\gamma/\bar\nu}F^{(2)}[(p-p_c)N^{1/\bar\nu}]\qquad\mathrm{(S7)}",
        "s8": r"p_c(N)=\underset{p}{\operatorname{arg\,max}}\,\langle S(p,N)\rangle\qquad\mathrm{(S8)}",
        "s9": r"p_c=p_c(N)+bN^{-1/\bar\nu}\qquad\mathrm{(S9)}",
        "s10_explicit": r"\langle P(p=p_c,N)\rangle\sim N^{-\beta/\bar\nu}\qquad\mathrm{(S10)}",
        "p_prefactor": r"N^{-\beta/\bar\nu}",
        "u": r"u=(p-p_c)N^{1/\bar\nu}",
        "s_infinity_background": r"S_\infty(p)\propto|p-p_c|^{-\gamma}",
        "maximum_height": r"\max_p\,\langle S(p,N)\rangle",
        "maximum_position": r"\underset{p}{\operatorname{arg\,max}}\,\langle S(p,N)\rangle",
    }
    f = {key: formula("eq_" + key, val) for key, val in definitions.items()}
    slides = []
    sm = "Kim & Radicchi (2024), Supplemental Material "

    def add(id, title, elements, source, notes):
        slides.append(dict(id=id, title=title, elements=elements, footer=source,
                           notes=notes, header=True))

    add(11, "有限サイズスケーリング（FSS）", [
        text("SPP原論文では、相転移の臨界点と臨界指数を推定するために、\n有限サイズスケーリング（FSS）を用いる。", 50, 121, 860, 58, 22),
        text("ネットワークサイズNに対する依存性の例", 50, 190, 860, 31, 22, BLUE, True),
        text("① 疑似臨界点の位置", 50, 232, 860, 30, 20),
        image(f["s9"], 145, 266, 670, 49, definitions["s9"]),
        text("② 臨界点における最大連結成分の割合", 50, 327, 860, 30, 20),
        image(f["s10_explicit"], 145, 359, 670, 49, definitions["s10_explicit"]),
        text("（S10）を明示的に書いた形：原文の省略記法P(p_c)について、\n試行間平均とN依存性を明示している。", 50, 411, 860, 40, 14, INK, False, True),
        text("異なるサイズの測定結果から、臨界点や臨界指数を推定する。", 50, 454, 860, 29, 20, BLUE),
    ], sm + "IV.A・IV.B、PDF3／印刷3。後続の式(S9)・(S10)を先に紹介。記号・導出は後述。",
    "【原論文の内容】Supplemental Material IV.A/IV.B（PDF3）のS9、S10を先に紹介する。S9は有限サイズの疑似臨界点と無限サイズの臨界点の関係、S10は臨界点でのPのサイズ依存。p_c：無限サイズの臨界点、p_c(N)：有限サイズの疑似臨界点、N：頂点数、β（ベータ）とν̄（ニューバー）：臨界指数、b：係数。画面の2式を指す。詳細な意味と導出は後続で説明するので追加板書は不要。S10の画面表記は説明用に平均とN依存性を明示したもので、原文はP(p_c)=〈P(p=p_c,N)〉〜N^{-β/ν̄}。原文の左辺を厳密にそのまま引用したと誤認させない。【補足】FSSの仮定に基づく関係であり、SPPの操作規則から厳密に導かれた恒等式ではない。")

    add(12, "最大連結成分の有限サイズスケーリング", [
        text("原論文では、最大連結成分の割合Pについて次のFSSを仮定する。", 50, 121, 860, 35, 21),
        image(f["s6"], 50, 165, 860, 68, definitions["s6"]),
        image(f["p_prefactor"], 65, 260, 170, 54, definitions["p_prefactor"]),
        text("① 引数uが一定のときの、\n　 Pのサイズ依存性を表す。", 270, 259, 640, 59, 21),
        image(f["u"], 50, 331, 420, 54, definitions["u"]),
        text("② 臨界点からの距離を、Nに応じて調整。\n　 uは説明用に導入した補助記号。", 490, 330, 420, 59, 19),
        text("β（ベータ）：Pの臨界指数\nν̄（ニューバー）：相関体積の臨界指数\np_c：無限サイズの臨界点", 50, 402, 450, 78, 18, INK, False, True),
        text("F⁽¹⁾：Pに対応するスケーリング関数\n〈P(p,N)〉：削除率p、サイズNでの\n　　　　　 Pの試行間平均", 510, 402, 400, 78, 18),
    ], sm + "IV.A、PDF2／印刷2、式(S6)。右辺を2つの役割に分けて説明。",
    "【原論文の内容】Supplemental Material IV.A（PDF2）は式S6をFSSの仮定として採用する。βはP、ν̄は相関体積の指数。右辺の前因子N^{-β/ν̄}はスケーリング関数の引数を一定にしたときのサイズ依存、u=(p-p_c)N^{1/ν̄}は説明用補助記号である。【一般理論に基づく補足：原論文掲載の導出ではない】通常の連続パーコレーションの連結側p<p_cでδ=p_c-p>0、P_∞∝δ^βを想定する。相関体積V_corr∝|p-p_c|^{-ν̄}、有限サイズ効果が重要となる規模V_corr〜Nから、|p-p_c|〜N^{-1/ν̄}と考える。この幅を基準にした符号付き距離がu=(p-p_c)/N^{-1/ν̄}。u固定ならp-p_c=uN^{-1/ν̄}とともにpも変化する。代表的大きさP_scale〜(N^{-1/ν̄})^β=N^{-β/ν̄}。uによる変化をF^{(1)}で表すことでS6の形を動機づける。これは厳密な証明ではなく、無制限SPPや本研究の2D格子で連続転移の描像が必ず成立するとの主張でもない。ERのV_corrを自然な実空間体積と同一視しない。FSSが成立すればN^{β/ν̄}〈P〉=F^{(1)}(u)としてデータコラプスを考えられる。質問時のみ、連結側の漸近形F^{(1)}(u)∝(-u)^βによるP_∞との整合性を説明する。")

    add(13, "平均クラスターサイズの有限サイズスケーリング", [
        text("原論文では、平均クラスターサイズSについて次のFSSを仮定する。", 50, 121, 860, 35, 21),
        image(f["s7"], 50, 165, 860, 68, definitions["s7"]),
        text("通常の連続転移の背景（原論文の式とは別）", 50, 236, 860, 30, 20, BLUE, True),
        image(f["s_infinity_background"], 50, 275, 390, 52, definitions["s_infinity_background"]),
        text("臨界点付近で、有限クラスターの\n平均サイズが増大する（γ>0）。", 490, 275, 420, 54, 20),
        text("S_{∞}は無限系の有限クラスターの平均。有限系で最大成分1個を\n除く定義と、無条件に同一視しない。", 50, 340, 860, 47, 17, INK, False, True),
        text("有限サイズの転移領域では、Sの代表的な大きさがN^{γ/ν̄}に従うと考える。", 50, 397, 860, 32, 21, BLUE, False, True),
        text("γ（ガンマ）：Sの臨界指数　F⁽²⁾：Sのスケーリング関数\nν̄（ニューバー）：相関体積の臨界指数（スライド12と共通）", 50, 439, 860, 46, 17),
    ], sm + "IV.A、PDF2／印刷2、式(S7)。S∞の関係は一般理論に基づく補足。",
    "【原論文の内容】Supplemental Material IV.A（PDF2）のS7。γ（ガンマ）は平均クラスターサイズSの指数、ν̄はスライド12と共通の相関体積の指数、F^{(2)}はSの関数。【一般理論に基づく補足：原論文の式ではない】通常の連続転移の無限系で、有限クラスターの平均S_∞∝|p-p_c|^{-γ}（γ>0）。S_∞は無限系の有限クラスターについての平均であり、有限系で最大成分を1個除く定義と無条件に同一視しない。スライド12の幅|p-p_c|〜N^{-1/ν̄}を用い、代表的大きさS_scale〜(N^{-1/ν̄})^{-γ}=N^{γ/ν̄}を動機づける。Pは小さくなる、Sは増大するという通常の連続転移の臨界挙動の違いが、前因子の符号に対応する。同じuを使うがF^{(1)}とF^{(2)}は異なる。S7も仮定であり、2D制限なしSPPへの適用や厳密証明を主張しない。相関体積の導出は繰り返さない。")

    add(14, "疑似臨界点：平均クラスターサイズの最大位置", [
        text("有限サイズNの疑似臨界点を、平均クラスターサイズが\n最大となる辺の削除率として定義する。", 50, 121, 860, 58, 22),
        image(f["s8"], 70, 186, 820, 74, definitions["s8"]),
        image(f["maximum_height"], 65, 290, 365, 53, definitions["maximum_height"]),
        image(f["maximum_position"], 510, 290, 365, 53, definitions["maximum_position"]),
        text("ピークの高さ", 65, 351, 365, 31, 22, BLUE, True),
        text("ピークを与える削除率p", 510, 351, 365, 31, 22, BLUE, True),
        text("argmax（アーグマックス）：最大値を取る変数の値を求める演算。", 50, 402, 860, 31, 19),
        text("同じNとpでSを試行間平均し、\nその平均曲線が最大となる削除率をp_c(N)とする。", 50, 434, 860, 52, 19, INK, False, True),
    ], sm + "IV.A、PDF3／印刷3、式(S8)。p_c(N)は有限Nごとの量。",
    "【原論文の内容】Supplemental Material IV.A（PDF3）のS8は、平均S最大位置を有限サイズの疑似臨界点と定義する。最大クラスターの最大減少位置を使う定義とは区別する。【一般的な説明】通常の連続パーコレーションでは転移付近にさまざまなサイズのクラスターが現れ、有限クラスターの平均サイズSが大きくなりやすい。N固定でpを変化させ、各pでSを試行平均し、その平均曲線の最大位置pを求める。各試行のピーク位置を先に求めて平均する操作とは一般に異なる。maxは関数の最大値、argmax（argument of the maximum）はそれを与える変数の値を求める一つの演算であり、argとmaxを別々に計算しない。複素数の偏角argとは区別。必要なら数学例f(p)=5-(p-0.6)^2、max f=5、argmax f=0.6を使うが、SPP実測データではないと明示。S8自体は画面を指し、書き写さない。p_c(N)は無限サイズのp_cと同じとは限らず、スライド15で関係を説明する。同率最大が複数ならargmaxは集合となることがあるため、数値解析では選択規則が必要。Sのピーク位置とPの最大減少位置は必ずしも一致しない。")

    payload = dict(canvas=[960, 540], font="Meiryo", slides=slides, total_slides=23,
                   scope="Only slides 11-14 and their speaker notes", equations=definitions,
                   protected_inputs=protected)
    (BUILD / "deck_ver1.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Prepared only slides 11-14; other 19 slide parts will be copied unchanged.")


def merge(candidate: Path):
    """Use every original part except the four slide/notes XML and slide rels."""
    protect()
    replacement = {}
    additions = {}
    with zipfile.ZipFile(ORIGINAL) as old, zipfile.ZipFile(candidate) as draft:
        old_names = set(old.namelist())
        definitions = json.loads((BUILD / "deck_ver1.json").read_text(encoding="utf-8"))["slides"]
        for i in range(11, 15):
            slide = f"ppt/slides/slide{i}.xml"
            current_text = "".join(node.text or "" for node in ET.fromstring(draft.read(slide)).iter(
                "{http://schemas.openxmlformats.org/drawingml/2006/main}t"))
            assert definitions[i - 11]["title"] in current_text, (i, "candidate title does not contain the revision")
            intro = definitions[i - 11]["elements"][0]["text"].replace("\n", "").replace("\r", "")
            assert intro in current_text.replace("\n", "").replace("\r", ""), (i, "candidate revised introduction absent")
            replacement[slide] = draft.read(slide)
            notes = f"ppt/notesSlides/notesSlide{i}.xml"
            replacement[notes] = draft.read(notes)
            relpart = f"ppt/slides/_rels/slide{i}.xml.rels"
            reltree = ET.fromstring(draft.read(relpart))
            oldrels = ET.fromstring(old.read(relpart))
            original_nonimages = {r.attrib["Type"]: r.attrib["Target"] for r in oldrels
                                  if not r.attrib["Type"].endswith("/image")}
            for j, rel in enumerate(reltree):
                if rel.attrib["Type"].endswith("/image"):
                    target = posixpath.normpath(posixpath.join("ppt/slides", rel.attrib["Target"]))
                    data = draft.read(target)
                    ext = Path(target).suffix.lower()
                    assert ext == ".png", (i, target, "new equation must be PNG")
                    name = f"ppt/media/ver1_slide{i}_image{j}{ext}"
                    assert name not in old_names, name
                    additions[name] = data
                    rel.attrib["Target"] = "../media/" + posixpath.basename(name)
                else:
                    assert rel.attrib["Type"] in original_nonimages, rel.attrib
                    assert rel.attrib["Target"] == original_nonimages[rel.attrib["Type"]], rel.attrib
            ET.register_namespace("", REL_NS)
            replacement[relpart] = ET.tostring(reltree, encoding="utf-8", xml_declaration=True)
            # Notes continue to use the original notes master and original slide.
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
        for i in list(range(1, 11)) + list(range(15, 24)):
            for name in [f"ppt/slides/slide{i}.xml", f"ppt/slides/_rels/slide{i}.xml.rels",
                         f"ppt/notesSlides/notesSlide{i}.xml", f"ppt/notesSlides/_rels/notesSlide{i}.xml.rels"]:
                assert name in unchanged, name
        assert new.testzip() is None
    result = dict(status="PASS", revised_slides=[11,12,13,14], unchanged_slide_count=19,
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
