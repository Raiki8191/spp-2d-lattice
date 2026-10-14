"""Read-only checks and private rendering for the four-slide Ver.2 revision."""

from __future__ import annotations

import hashlib
import json
import posixpath
import re
import subprocess
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from PIL import Image, ImageChops

HERE = Path(__file__).resolve().parent
BUILD = HERE / ".build" / "ver2"
NS = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main",
      "p": "http://schemas.openxmlformats.org/presentationml/2006/main"}
CHANGED = {15, 16, 17, 18}
UNCHANGED = sorted(set(range(1, 24)) - CHANGED)
EXPECTED_TITLES = {15: "臨界点と疑似臨界点の関係",
                   16: "臨界点でのサイズ依存性",
                   17: "疑似臨界点での臨界指数推定",
                   18: "原論文の臨界点推定：C=1"}
FIGURE_SHA256 = "8ce89bec8d31cd046c9c6e231bd38196e60d4a1fe770cbe2cbdf1f3fe50efdc8"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(*args: str) -> str:
    return subprocess.check_output(args, encoding="utf-8", errors="replace")


def pages(path: Path) -> int:
    return int(re.search(r"Pages:\s+(\d+)", run("pdfinfo", str(path))).group(1))


def render(path: Path, name: str, last: int | None = None) -> list[Path]:
    directory = BUILD / name
    directory.mkdir(parents=True, exist_ok=True)
    count = min(last or pages(path), pages(path))
    subprocess.run(["pdftoppm", "-f", "1", "-l", str(count), "-r", "120",
                    "-png", str(path), str(directory / "page")], check=True)
    output = []
    for i in range(1, count + 1):
        choices = list(directory.glob(f"page-{i:02d}.png")) or list(directory.glob(f"page-{i}.png"))
        if len(choices) != 1:
            raise AssertionError((name, i, choices))
        output.append(choices[0])
    return output


def same_pixels(old: Path, new: Path) -> bool:
    with Image.open(old) as a, Image.open(new) as b:
        return a.size == b.size and ImageChops.difference(a.convert("RGB"), b.convert("RGB")).getbbox() is None


def font_check(path: Path) -> dict:
    output = run("pdffonts", str(path))
    entries = []
    for row in output.splitlines()[2:]:
        if not row.strip():
            continue
        flags = re.search(r"\s+(yes|no)\s+(yes|no)\s+(yes|no)\s+\d+\s+\d+\s*$", row)
        assert flags and flags.group(1) == "yes", (path, row)
        entries.append(row)
    assert entries, (path, "No font entries")
    return {"all_embedded": True, "font_rows": len(entries)}


def main() -> None:
    BUILD.mkdir(parents=True, exist_ok=True)
    baseline = json.loads((HERE / "ver2_protected_inputs.json").read_text("utf-8"))
    assert all(sha(HERE / name) == value for name, value in baseline.items()), "Protected input changed"
    old_pptx = HERE / "slides/seminar_ver1.pptx"
    new_pptx = HERE / "slides/seminar_ver2.pptx"
    com = json.loads((HERE / ".build/ver2_slides/powerpoint_com_report.json").read_text("utf-8-sig"))
    assert "fatal_error" not in com and com["slide_count"] == 23
    assert com["output"]["reopened_successfully"] and com["output"]["speaker_notes_count"] == 23
    assert not com["layout_warnings"], "Native PowerPoint reports layout overflow"
    preservation = json.loads((HERE / ".build/ver2_slides/package_preservation.json").read_text("utf-8"))
    assert preservation["final_sha256"] == sha(new_pptx), "Stale native package report"
    with zipfile.ZipFile(old_pptx) as old, zipfile.ZipFile(new_pptx) as new:
        old_names, new_names = set(old.namelist()), set(new.namelist())
        assert old_names <= new_names, "Original package parts removed"
        assert len([n for n in new_names if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)]) == 23
        assert len([n for n in new_names if re.fullmatch(r"ppt/notesSlides/notesSlide\d+\.xml", n)]) == 23
        allowed = {"[Content_Types].xml"}
        for i in CHANGED:
            allowed.update({f"ppt/slides/slide{i}.xml", f"ppt/slides/_rels/slide{i}.xml.rels",
                            f"ppt/notesSlides/notesSlide{i}.xml", f"ppt/notesSlides/_rels/notesSlide{i}.xml.rels"})
        changed_parts = sorted(n for n in old_names if old.read(n) != new.read(n))
        assert set(changed_parts) <= allowed, ("Unexpected package changes", set(changed_parts) - allowed)
        assert all(f"ppt/slides/slide{i}.xml" in changed_parts for i in CHANGED)
        additions = sorted(new_names - old_names)
        assert all(n.startswith("ppt/media/") for n in additions), additions
        figure_rels = ET.fromstring(new.read("ppt/slides/_rels/slide18.xml.rels"))
        slide18_images = []
        for rel in figure_rels:
            if rel.attrib["Type"].endswith("/image"):
                target = posixpath.normpath(posixpath.join("ppt/slides", rel.attrib["Target"]))
                slide18_images.append(hashlib.sha256(new.read(target)).hexdigest())
        assert FIGURE_SHA256 in slide18_images, "Fig. S1(a)(b) differs from independently verified direct crop"
        for i in range(1, 24):
            root = ET.fromstring(new.read(f"ppt/slides/slide{i}.xml"))
            text = "".join(t.text or "" for t in root.findall(".//a:t", NS))
            assert f"{i:02d} / 23" in text, (i, "Page counter")
            if i in EXPECTED_TITLES:
                assert EXPECTED_TITLES[i] in text, (i, "Revised slide title missing")
        size = ET.fromstring(new.read("ppt/presentation.xml")).find("p:sldSz", NS)
        assert int(size.attrib["cx"]) * 9 == int(size.attrib["cy"]) * 16

    old_md = (HERE / "board/board_notes_ver1.md").read_bytes()
    marker = "## 【対応：スライド15】".encode("utf-8")
    old_prefix = old_md[:old_md.index(marker)]
    new_md_bytes = (HERE / "board/board_notes_ver2.md").read_bytes()
    assert new_md_bytes.startswith(old_prefix), "Original first seven board pages Markdown byte prefix changed"
    new_md = new_md_bytes.decode("utf-8").replace("\r\n", "\n")
    old_md_text = old_md.decode("utf-8").replace("\r\n", "\n")
    old_19_23 = old_md_text[old_md_text.index("### 【19】"):]
    assert old_19_23.strip() in new_md, "Slides19–23 explanatory content changed"

    old_pdf = HERE / "slides/seminar_ver1.pdf"
    new_pdf = HERE / "slides/seminar_ver2.pdf"
    old_board = HERE / "board/board_notes_ver1.pdf"
    new_board = HERE / "board/board_notes_ver2.pdf"
    assert pages(new_pdf) == 23
    board_count = pages(new_board)
    assert board_count > 7
    print("Rendering all 23 revised slides, 23 reference slides and complete board notes...", flush=True)
    new_images = render(new_pdf, "slides")
    old_images = render(old_pdf, "slides_reference")
    slide_checks = [{"slide": i, "pixel_identical_at_120dpi": same_pixels(old_images[i-1], new_images[i-1])}
                    for i in UNCHANGED]
    assert all(x["pixel_identical_at_120dpi"] for x in slide_checks), slide_checks
    board_images = render(new_board, "board")
    old_board_images = render(old_board, "board_reference", last=7)
    board_checks = [{"page": i+1, "pixel_identical_at_120dpi": same_pixels(a, b)}
                    for i, (a, b) in enumerate(zip(old_board_images, board_images))]
    assert len(board_checks) == 7 and all(x["pixel_identical_at_120dpi"] for x in board_checks)
    text_checks = []
    for i in UNCHANGED:
        text_a = run("pdftotext", "-layout", "-f", str(i), "-l", str(i), str(old_pdf), "-")
        text_b = run("pdftotext", "-layout", "-f", str(i), "-l", str(i), str(new_pdf), "-")
        assert text_a == text_b, (i, "Extracted PDF text changed")
        text_checks.append(i)
    for name, path in [("slides", new_pdf), ("board", new_board)]:
        (BUILD / f"{name}_text.txt").write_text(run("pdftotext", "-layout", str(path), "-"), "utf-8")
    assert all(sha(HERE / name) == value for name, value in baseline.items())
    result = {"status": "PASS", "slides": 23, "board_pages": board_count,
              "native_powerpoint_reopened": True, "speaker_notes": 23, "native_layout_warnings": 0,
              "protected_inputs_sha256": baseline, "protected_inputs_unchanged": True,
              "changed_existing_pptx_parts": changed_parts, "added_pptx_parts": additions,
              "unchanged_19_slides_notes_relationships_shared_resources": "byte-identical",
              "unchanged_19_pdf_pages": slide_checks, "unchanged_19_pdf_text": text_checks,
              "fig_s1_ab_final_embedding_matches_verified_direct_crop_sha256": FIGURE_SHA256,
              "board_original_seven_pages": board_checks, "board_original_seven_page_md_byte_prefix": True,
              "board_slide19_23_content_preserved_verbatim": True,
              "pdf_fonts": {"slides": font_check(new_pdf), "board": font_check(new_board)},
              "output_sha256": {str(p.relative_to(HERE)): sha(p) for p in [new_pptx, new_pdf, HERE / "board/board_notes_ver2.md", new_board]},
              "visual_review": "Separate manual review of rendered PNGs required; this script checks structure and identity."}
    (BUILD / "validation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), "utf-8")
    print(json.dumps({k: result[k] for k in ["status", "slides", "board_pages", "protected_inputs_unchanged"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
