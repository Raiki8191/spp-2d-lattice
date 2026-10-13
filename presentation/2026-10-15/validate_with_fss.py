"""Verify FSS append artifacts without changing any PPTX, PDF, or board source.

Only .build/fss_append/ receives renderings and QA reports.  Scientific source
interpretation and full-page visual review are separate from these checks.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import math
import posixpath
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

import numpy as np
from PIL import Image, ImageDraw


TASK = Path(__file__).resolve().parent
ROOT = TASK.parents[1]
BUILD = TASK / ".build" / "fss_append"
PDF_RENDER = BUILD / "pdf"
DPI = 120
NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def within(path: Path, base: Path = ROOT) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(base.resolve()):
        raise ValueError(f"Path escapes the permitted workspace: {resolved}")
    return resolved


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def file_hash(path: Path) -> str:
    return digest(within(path).read_bytes())


def read_json(path: Path):
    return json.loads(within(path).read_text(encoding="utf-8-sig"))


def run(*args: str) -> str:
    return subprocess.check_output(
        list(args), text=True, encoding="utf-8", errors="replace"
    )


def pdf_pages(path: Path) -> int:
    info = run("pdfinfo", "-enc", "UTF-8", str(within(path)))
    match = re.search(r"^Pages:\s+(\d+)\s*$", info, re.MULTILINE)
    if not match:
        raise AssertionError(f"PDF page count not readable: {path}")
    return int(match.group(1))


def render_pdf(path: Path, directory: Path, first: int = 1, last: int | None = None):
    path = within(path)
    directory = within(directory, BUILD)
    directory.mkdir(parents=True, exist_ok=True)
    total = pdf_pages(path)
    last = total if last is None else last
    if not 1 <= first <= last <= total:
        raise AssertionError((path, first, last, total))
    prefix = directory / "page"
    subprocess.run(
        ["pdftoppm", "-r", str(DPI), "-f", str(first), "-l", str(last),
         "-png", str(path), str(prefix)],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    digits = len(str(total))
    pages = []
    for index in range(first, last + 1):
        generated = within(directory / f"page-{index:0{digits}d}.png", BUILD)
        normalized = within(directory / f"page-{index:02d}.png", BUILD)
        if generated != normalized:
            generated.replace(normalized)
        if not normalized.is_file():
            raise AssertionError(f"Missing rendered page: {normalized}")
        pages.append(normalized)
    return pages


def protect_inputs() -> list[dict]:
    checks = []
    manifest = read_json(BUILD / "protected_inputs.json")
    if len(manifest) != 9:
        raise AssertionError(f"Expected nine protected inputs, found {len(manifest)}")
    for item in manifest:
        path = within(ROOT / item["path"])
        actual = file_hash(path)
        if actual != item["sha256"]:
            raise AssertionError(f"Protected input changed: {item['path']}")
        checks.append({"path": item["path"], "sha256": actual, "unchanged": True})
    return checks


def part_text(element: ET.Element) -> str:
    return "".join(node.text or "" for node in element.findall(".//a:t", NS))


def normalize_note(value: str) -> str:
    return re.sub(r"\s+", "", value)


def notes_body(xml: ET.Element) -> str:
    for shape in xml.findall(".//p:sp", NS):
        placeholder = shape.find("p:nvSpPr/p:nvPr/p:ph", NS)
        if placeholder is not None and placeholder.get("type") == "body":
            return part_text(shape)
    raise AssertionError("Missing notes body placeholder")


def image_hashes(archive: zipfile.ZipFile, slide_id: int) -> Counter:
    xml = ET.fromstring(archive.read(f"ppt/slides/slide{slide_id}.xml"))
    relationships = ET.fromstring(
        archive.read(f"ppt/slides/_rels/slide{slide_id}.xml.rels")
    )
    image_parts = {}
    for relationship in relationships:
        if not relationship.get("Type", "").endswith("/image"):
            continue
        target = relationship.attrib["Target"]
        resolved = (target.lstrip("/") if target.startswith("/") else
                    posixpath.normpath(posixpath.join("ppt/slides", target)))
        if not resolved.startswith("ppt/media/"):
            raise AssertionError(f"Unexpected embedded image part: {resolved}")
        image_parts[relationship.attrib["Id"]] = resolved
    return Counter(
        digest(archive.read(image_parts[blip.attrib[f"{{{NS['r']}}}embed"]]))
        for blip in xml.findall(".//a:blip", NS)
        if f"{{{NS['r']}}}embed" in blip.attrib
    )


def counter_bounds(xml: ET.Element, index: int) -> tuple[int, int, int, int]:
    matches = [shape for shape in xml.findall(".//p:sp", NS)
               if part_text(shape) == f"{index:02d} / 10"]
    if len(matches) != 1:
        raise AssertionError((index, "unique original page-counter shape"))
    transform = matches[0].find("p:spPr/a:xfrm", NS)
    if transform is None or transform.get("rot", "0") != "0":
        raise AssertionError((index, "unsupported page-counter transform"))
    origin = transform.find("a:off", NS)
    extent = transform.find("a:ext", NS)
    x, y = int(origin.attrib["x"]), int(origin.attrib["y"])
    w, h = int(extent.attrib["cx"]), int(extent.attrib["cy"])
    # Exactly the native shape rectangle; no additional margin is masked.
    scale = DPI / 914400
    return (math.floor(x * scale), math.floor(y * scale),
            math.ceil((x + w) * scale), math.ceil((y + h) * scale))


def pdf_word_boxes(path: Path, page: int, label: str) -> list[tuple[int, int, int, int]]:
    xml_text = run("pdftotext", "-bbox", "-f", str(page), "-l", str(page),
                   "-enc", "UTF-8", str(within(path)), "-")
    directory = within(BUILD / "text_bbox", BUILD)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{label}-page-{page:02d}.xhtml").write_text(xml_text, encoding="utf-8")
    xml = ET.fromstring(xml_text)
    scale, padding = DPI / 72, 2
    boxes = []
    for element in xml.iter():
        if element.tag.rsplit("}", 1)[-1] != "word":
            continue
        boxes.append((math.floor(float(element.attrib["xMin"]) * scale) - padding,
                      math.floor(float(element.attrib["yMin"]) * scale) - padding,
                      math.ceil(float(element.attrib["xMax"]) * scale) + padding,
                      math.ceil(float(element.attrib["yMax"]) * scale) + padding))
    if not boxes:
        raise AssertionError((path, page, "no extractable word bounding boxes"))
    return boxes


def compare_pdf_text(old: Path, new: Path) -> dict:
    texts = []
    for path in (old, new):
        value = run("pdftotext", "-layout", "-f", "1", "-l", "10",
                    "-enc", "UTF-8", str(within(path)), "-")
        for index in range(1, 11):
            value = re.sub(rf"\b{index:02d}\s*/\s*(?:10|23)\b", f"PAGE_{index:02d}_TOTAL", value)
        texts.append(value)
    original, appended = texts
    compact_old, compact_new = re.sub(r"\s+", "", original), re.sub(r"\s+", "", appended)
    return {
        "counter_total_normalization_only_exact": original == appended,
        "counter_total_and_whitespace_normalization_equal": compact_old == compact_new,
        "old_extracted_characters": len(original), "new_extracted_characters": len(appended),
        "old_normalized_text_sha256": digest(original.encode()),
        "new_normalized_text_sha256": digest(appended.encode()),
    }


def compare_pixels(old: Path, new: Path, mask=None, diff_stem: Path | None = None,
                   text_boxes: list[tuple[int, int, int, int]] | None = None) -> dict:
    with Image.open(old) as image:
        first = np.array(image.convert("RGB"), dtype=np.int16)
    with Image.open(new) as image:
        second = np.array(image.convert("RGB"), dtype=np.int16)
    if first.shape != second.shape:
        raise AssertionError((old, new, "render sizes differ", first.shape, second.shape))
    delta = np.abs(first - second)
    raw_changed = np.any(delta != 0, axis=2)
    changed = raw_changed.copy()
    if mask is not None:
        x0, y0, x1, y1 = mask
        if not 0 <= x0 < x1 <= first.shape[1] or not 0 <= y0 < y1 <= first.shape[0]:
            raise AssertionError((mask, first.shape, "mask outside page"))
        changed[y0:y1, x0:x1] = False
    ys, xs = np.nonzero(changed)
    bbox = ([int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]
            if len(xs) else None)
    bands = []
    occupied_rows = np.flatnonzero(changed.any(axis=1))
    if len(occupied_rows):
        groups = np.split(occupied_rows, np.flatnonzero(np.diff(occupied_rows) > 3) + 1)
        for group in groups:
            y0, y1 = int(group[0]), int(group[-1]) + 1
            local = changed[y0:y1]
            band_y, band_x = np.nonzero(local)
            bands.append({
                "bbox": [int(band_x.min()), y0, int(band_x.max()) + 1, y1],
                "different_pixels": int(local.sum()),
                "maximum_channel_difference": int(delta[y0:y1][local].max()),
            })
    output = {
        "image_size": [int(first.shape[1]), int(first.shape[0])],
        "dpi": DPI,
        "masked_bbox_px": list(mask) if mask is not None else None,
        "different_pixels_before_mask": int(raw_changed.sum()),
        "different_pixels_after_mask": int(changed.sum()),
        "difference_bbox_after_mask": bbox,
        "maximum_channel_difference_after_mask": int(delta[changed].max()) if len(xs) else 0,
        "pixel_identical_after_mask": len(xs) == 0,
        "difference_row_bands": bands,
        "old_render_sha256": file_hash(old),
        "new_render_sha256": file_hash(new),
    }
    outside_words = None
    if text_boxes is not None:
        word_mask = np.zeros(changed.shape, dtype=bool)
        for x0, y0, x1, y1 in text_boxes:
            x0, x1 = max(0, x0), min(first.shape[1], x1)
            y0, y1 = max(0, y0), min(first.shape[0], y1)
            if x1 > x0 and y1 > y0:
                word_mask[y0:y1, x0:x1] = True
        outside_words = changed & ~word_mask
        outside_y, outside_x = np.nonzero(outside_words)
        output.update({
            "word_bbox_padding_px": 2,
            "old_and_new_word_box_count": len(text_boxes),
            "different_pixels_outside_word_boxes": int(outside_words.sum()),
            "all_differences_within_word_boxes": not len(outside_x),
            "difference_bbox_outside_word_boxes": (
                [int(outside_x.min()), int(outside_y.min()), int(outside_x.max()) + 1, int(outside_y.max()) + 1]
                if len(outside_x) else None),
        })
    if diff_stem is not None:
        diff_stem = within(diff_stem, BUILD)
        diff_stem.parent.mkdir(parents=True, exist_ok=True)
        heat = np.full(first.shape, 255, dtype=np.uint8)
        heat[changed] = [220, 45, 20]
        overlay = np.rint(first * 0.65 + 255 * 0.35).astype(np.uint8)
        overlay[changed] = [220, 45, 20]
        if outside_words is not None:
            heat[outside_words] = [170, 35, 180]
            overlay[outside_words] = [170, 35, 180]
        for label, pixels in [("difference", heat), ("overlay", overlay)]:
            image = Image.fromarray(pixels)
            if mask is not None:
                ImageDraw.Draw(image).rectangle(mask, outline=(70, 130, 190), width=1)
            target = diff_stem.with_name(diff_stem.name + f"-{label}.png")
            image.save(target)
            output[label + "_image"] = str(target.relative_to(TASK))
    return output


def verify_fonts(key: str, path: Path) -> dict:
    output = run("pdffonts", str(within(path)))
    within(BUILD / f"{key}_fonts.txt", BUILD).write_text(output, encoding="utf-8")
    rows = []
    for line in output.splitlines()[2:]:
        if not line.strip():
            continue
        match = re.search(r"\s+(yes|no)\s+(yes|no)\s+(yes|no)\s+(\d+)\s+(\d+)\s*$", line)
        if not match:
            raise AssertionError((path, "unrecognized pdffonts row", line))
        if match.group(1) != "yes":
            raise AssertionError((path, "font not embedded", line))
        rows.append(line)
    if not rows:
        raise AssertionError((path, "no font rows found"))
    return {"all_font_rows_embedded": True, "font_count": len(rows)}


def main() -> int:
    BUILD.mkdir(parents=True, exist_ok=True)
    result = {"validation_scope": "artifact fidelity and reproducible private QA", "issues": [], "render_differences": []}
    try:
        result["protected_inputs_before"] = protect_inputs()
        deck = read_json(BUILD / "deck_fss.json")
        assert deck["total_slides"] == 23 and len(deck["slides"]) == 13
        assert [slide["id"] for slide in deck["slides"]] == list(range(11, 24))
        com = read_json(BUILD / "powerpoint_com_report.json")
        assert com["slide_count"] == com["output"]["speaker_notes_count"] == 23
        assert com["output"]["reopened_successfully"] and not com["layout_warnings"]
        old_pptx = within(TASK / "slides/seminar_01-10.pptx")
        new_pptx = within(TASK / "slides/seminar_with_fss.pptx")
        masks = []
        image_checks = []
        with zipfile.ZipFile(old_pptx) as before, zipfile.ZipFile(new_pptx) as after:
            names = after.namelist()
            assert len([p for p in names if re.fullmatch(r"ppt/slides/slide\d+\.xml", p)]) == 23
            assert len([p for p in names if re.fullmatch(r"ppt/notesSlides/notesSlide\d+\.xml", p)]) == 23
            size = ET.fromstring(after.read("ppt/presentation.xml")).find("p:sldSz", NS)
            assert int(size.attrib["cx"]) * 9 == int(size.attrib["cy"]) * 16
            for i in range(1, 11):
                part = f"ppt/slides/slide{i}.xml"
                source = before.read(part)
                needle, replacement = f">{i:02d} / 10<".encode(), f">{i:02d} / 23<".encode()
                assert source.count(needle) == 1
                assert source.replace(needle, replacement) == after.read(part), (i, "original slide changed")
                masks.append(counter_bounds(ET.fromstring(source), i))
                for part in [f"ppt/slides/_rels/slide{i}.xml.rels",
                             f"ppt/notesSlides/notesSlide{i}.xml",
                             f"ppt/notesSlides/_rels/notesSlide{i}.xml.rels"]:
                    assert before.read(part) == after.read(part), part
            resources = [name for name in before.namelist() if name.startswith((
                "ppt/media/", "ppt/theme/", "ppt/slideMasters/", "ppt/slideLayouts/", "ppt/notesMasters/"))]
            for name in resources:
                assert before.read(name) == after.read(name), name
            old_fonts = [name for name in before.namelist() if name.startswith("ppt/fonts/")]
            font_changes = [{"part": name, "old_bytes": len(before.read(name)),
                             "new_bytes": len(after.read(name)),
                             "byte_identical": before.read(name) == after.read(name)} for name in old_fonts]
            for slide in deck["slides"]:
                index = slide["id"]
                xml = ET.fromstring(after.read(f"ppt/slides/slide{index}.xml"))
                assert slide["title"] in part_text(xml), (index, "title")
                assert f"{index:02d} / 23" in part_text(xml), (index, "page total")
                notes = ET.fromstring(after.read(f"ppt/notesSlides/notesSlide{index}.xml"))
                assert normalize_note(notes_body(notes)) == normalize_note(slide["notes"]), (index, "speaker notes")
                actual = image_hashes(after, index)
                expected = Counter()
                for element in slide["elements"]:
                    if element["kind"] == "image":
                        asset = within(TASK / element["path"], TASK)
                        expected[file_hash(asset)] += 1
                        image_checks.append({"slide": index, "asset": element["path"],
                                             "sha256": file_hash(asset), "byte_identical_embedding": True})
                assert not (expected - actual), (index, "missing or changed embedded image", expected - actual)
        result["pptx"] = {"slides": 23, "speaker_notes": 23, "canvas": "16:9", "reopened_by_native_powerpoint": True}
        result["legacy_objects"] = {"old_slide_xml_except_counter_total": "10/10 byte-identical",
                                    "old_notes_and_relationships": "10/10 byte-identical",
                                    "old_media_theme_master_layout_resources": len(resources),
                                    "old_font_definitions_in_slide_xml": "byte-identical",
                                    "embedded_font_resubsetting_allowed": True,
                                    "embedded_font_parts": font_changes}
        result["new_embedded_images"] = image_checks
        pdfs = {
            "slides_with_fss": TASK / "slides/seminar_with_fss.pdf",
            "slides_original": TASK / "slides/seminar_01-10.pdf",
            "board_append": TASK / "board/board_notes_fss_append.pdf",
            "board_with_fss": TASK / "board/board_notes_with_fss.pdf",
            "board_original": TASK / "board/board_notes_01-10.pdf",
        }
        expected_pages = {"slides_with_fss": 23, "slides_original": 10,
                          "board_append": 4, "board_with_fss": 7, "board_original": 3}
        result["pdf_pages"] = {}
        for key, path in pdfs.items():
            count = pdf_pages(path)
            assert count == expected_pages[key], (key, count, expected_pages[key])
            result["pdf_pages"][key] = count
        result["pdf_fonts"] = {key: verify_fonts(key, path) for key, path in pdfs.items()}
        print("Rendering the 23-slide PDF and original 10-slide PDF at 120 dpi...", flush=True)
        new_pages = render_pdf(pdfs["slides_with_fss"], PDF_RENDER)
        old_pages = render_pdf(pdfs["slides_original"], PDF_RENDER / "original")
        result["legacy_pdf_extracted_text"] = compare_pdf_text(pdfs["slides_original"], pdfs["slides_with_fss"])
        comparisons = []
        for i, (old, new, mask) in enumerate(zip(old_pages, new_pages[:10], masks), 1):
            boxes = (pdf_word_boxes(pdfs["slides_original"], i, "original") +
                     pdf_word_boxes(pdfs["slides_with_fss"], i, "appended"))
            comparison = {"page": i, **compare_pixels(old, new, mask, BUILD / "legacy_diff" / f"page-{i:02d}", boxes)}
            comparisons.append(comparison)
            if not comparison["pixel_identical_after_mask"]:
                result["render_differences"].append(f"Original PDF page {i} differs outside its page-counter rectangle")
        result["legacy_pdf_pixel_comparisons"] = comparisons
        result["legacy_pdf_strict_pixel_preservation"] = all(item["pixel_identical_after_mask"] for item in comparisons)
        result["legacy_pdf_visual_review_required"] = bool(result["render_differences"])
        result["legacy_pdf_render_difference_policy"] = (
            "Original PPTX objects, image assets, notes, and source files are unchanged. "
            "Font re-subsetting is allowed, but raster differences are reported without "
            "calling them pixel-identical. Difference images require a separate visual review."
        )
        original_md = within(TASK / "board/board_notes_01-10.md").read_bytes()
        combined_md = within(TASK / "board/board_notes_with_fss.md").read_bytes()
        assert combined_md.startswith(original_md), "The combined board markdown does not preserve the original byte prefix"
        board_agent = read_json(TASK / ".build/fss-append/board/board_validation.json")
        assert (board_agent["old_pages"], board_agent["append_pages"], board_agent["combined_pages"]) == (3, 4, 7)
        assert board_agent["old_markdown_exact_byte_prefix"]
        assert all(item["pixel_identical_at_130dpi"] for item in board_agent["page_render_comparisons"])
        print("Independently comparing the original three board PDF pages...", flush=True)
        board_old_pages = render_pdf(pdfs["board_original"], PDF_RENDER / "board_original")
        board_new_prefix = render_pdf(pdfs["board_with_fss"], PDF_RENDER / "board_combined_prefix", last=3)
        board_comparisons = []
        for i, (old, new) in enumerate(zip(board_old_pages, board_new_prefix), 1):
            comparison = {"page": i, **compare_pixels(old, new)}
            board_comparisons.append(comparison)
            if not comparison["pixel_identical_after_mask"]:
                result["issues"].append(f"Original board PDF page {i} is not pixel-identical in the combined PDF")
        result["board_preservation"] = {"original_markdown_exact_byte_prefix": True,
                                        "independent_120dpi_prefix_comparisons": board_comparisons,
                                        "board_agent_130dpi_validation": board_agent}
        result["protected_inputs_after"] = protect_inputs()
        result["artifact_sha256"] = {"pptx": file_hash(new_pptx), **{key: file_hash(path) for key, path in pdfs.items()}}
        result["status"] = ("FAIL" if result["issues"] else
                            "PASS_WITH_RENDER_DIFFERENCES" if result["render_differences"] else "PASS")
    except Exception as error:
        result["status"] = "FAIL"
        result["fatal_error"] = f"{type(error).__name__}: {error}"
        within(BUILD / "validation.json", BUILD).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        raise
    within(BUILD / "validation.json", BUILD).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": result["status"], "pptx": result["pptx"],
                      "pdf_pages": result["pdf_pages"],
                      "protected_inputs": len(result["protected_inputs_after"]),
                      "new_embedded_images": len(image_checks),
                      "legacy_pdf_pixels_outside_counter": [p["different_pixels_after_mask"] for p in comparisons],
                      "board_prefix_different_pixels": [p["different_pixels_after_mask"] for p in board_comparisons],
                      "legacy_pdf_strict_pixel_preservation": result["legacy_pdf_strict_pixel_preservation"],
                      "legacy_pdf_visual_review_required": result["legacy_pdf_visual_review_required"],
                      "legacy_pdf_different_pixels_outside_text_boxes": [p["different_pixels_outside_word_boxes"] for p in comparisons],
                      "legacy_pdf_extracted_text": result["legacy_pdf_extracted_text"],
                      "issues": result["issues"]}, ensure_ascii=False, indent=2))
    return 0 if result["status"].startswith("PASS") else 1


if __name__ == "__main__":
    sys.exit(main())
