"""Build only the appended FSS board notes and a page-preserving combined PDF.

The existing three-page board PDF/Markdown and its builder are read-only inputs.
LuaLaTeX and existing Poppler pdfunite/Pillow are used; no installation.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
BOARD = HERE / "board"
BUILD = HERE / ".build" / "fss-append" / "board"
SOURCE = BOARD / "board_notes_fss_append.md"
APPEND_PDF = SOURCE.with_suffix(".pdf")
COMBINED_MD = BOARD / "board_notes_with_fss.md"
COMBINED_PDF = COMBINED_MD.with_suffix(".pdf")
OLD_MD = BOARD / "board_notes_01-10.md"
OLD_PDF = OLD_MD.with_suffix(".pdf")
OLD_BUILDER = HERE / "build_board_01_10.py"
EXPECTED_INPUT_HASHES = {
    OLD_MD: "345228c1bf5180189f13973f204997c3ac7dcb472c786eda546bff8315869c7a",
    OLD_PDF: "30fb0e8b8ef72d3c5ae87318a283298323007aa21bd79a0162abd3a820699c3f",
    OLD_BUILDER: "4a49c1104bd772a7164b7e43c9ba1cb0ed5c68024556c6efe28aa101e89ee0bd",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protect_inputs() -> None:
    for path, expected in EXPECTED_INPUT_HASHES.items():
        if sha256(path) != expected:
            raise RuntimeError(f"Protected input changed; stop for review: {path}")


def command(args: list[str]) -> str:
    return subprocess.check_output(args, text=True, encoding="utf-8", errors="replace")


def page_count(path: Path) -> int:
    info = command(["pdfinfo", "-enc", "UTF-8", str(path)])
    return int(re.search(r"Pages:\s+(\d+)", info).group(1))


def compile_tex(stem: str, body: str) -> Path:
    tex_path = BUILD / f"{stem}.tex"
    tex_path.write_text(body, encoding="utf-8")
    for run in range(2):
        result = subprocess.run(
            ["lualatex", "-interaction=nonstopmode", "-halt-on-error", "-file-line-error", tex_path.name],
            cwd=BUILD, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        (BUILD / f"{stem}_run{run + 1}.log").write_bytes(result.stdout)
        if result.returncode:
            print(result.stdout.decode("utf-8", errors="replace")[-6000:])
            raise RuntimeError(f"LuaLaTeX failed: {tex_path}")
    log = tex_path.with_suffix(".log").read_text(encoding="utf-8", errors="replace")
    if any(problem in log for problem in ["Missing character:", "Overfull \\hbox", "Overfull \\vbox"]):
        raise RuntimeError(f"Missing glyph or overflow: {tex_path.with_suffix('.log')}")
    return tex_path.with_suffix(".pdf")


def render(path: Path, prefix: str) -> list[Path]:
    result = subprocess.run(
        ["pdftoppm", "-r", "130", "-png", str(path), str(BUILD / prefix)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    if result.returncode:
        raise RuntimeError(result.stdout.decode("utf-8", errors="replace"))
    return [BUILD / f"{prefix}-{number}.png" for number in range(1, page_count(path) + 1)]


def main() -> None:
    for executable in ["lualatex", "pdfunite", "pdfinfo", "pdftoppm", "pdffonts", "pdftotext"]:
        if shutil.which(executable) is None:
            raise SystemExit(f"Required existing tool unavailable: {executable}; no installation attempted.")
    protect_inputs()
    if page_count(OLD_PDF) != 3:
        raise RuntimeError("Expected the protected existing three-page PDF")
    source_text = SOURCE.read_text(encoding="utf-8")
    for block in ["11〜13", "14〜15", "16〜17", "18〜23"]:
        if source_text.count("## 【対応：スライド" + block + "】") != 1:
            raise RuntimeError(f"Expected one appended board block: {block}")
    if source_text.count("<!-- pagebreak -->") != 3:
        raise RuntimeError("Expected four planned A4 page blocks")
    if source_text.count("<!-- write -->") != source_text.count("<!-- /write -->"):
        raise RuntimeError("Unbalanced write boxes")

    # Reuse only the existing pure renderer and style; never call its main().
    spec = importlib.util.spec_from_file_location("old_board_style_readonly", OLD_BUILDER)
    old_style = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old_style)
    preamble = old_style.PREAMBLE.replace(
        "2026年10月15日 ゼミ発表用カンニングペーパー", "2026年10月15日 FSS追加板書・口頭メモ"
    ).replace("before skip=4pt,after skip=4pt", "before skip=4pt,after skip=9pt")
    BUILD.mkdir(parents=True, exist_ok=True)
    append_tex = preamble + "\n\\setcounter{page}{4}\n" + old_style.markdown_to_latex(source_text) + "\n\\end{document}\n"
    built_append = compile_tex("board_notes_fss_append", append_tex)
    append_pages = page_count(built_append)
    if not 2 <= append_pages <= 4:
        raise RuntimeError(f"Expected 2-4 appended A4 pages; got {append_pages}. Inspect the temporary PDF.")
    shutil.copyfile(built_append, APPEND_PDF)

    # Directly copy PDF page objects. pdfpages was also available, but its
    # imported-page coordinate rounding gave tiny raster differences. pdfunite
    # preserves all old pages without recomposition or added page labels.
    built_combined = BUILD / "board_notes_with_fss.pdf"
    subprocess.run(["pdfunite", str(OLD_PDF), str(APPEND_PDF), str(built_combined)], check=True)
    if page_count(built_combined) != 3 + append_pages:
        raise RuntimeError("Unexpected combined page count")
    shutil.copyfile(built_combined, COMBINED_PDF)
    old_bytes = OLD_MD.read_bytes()
    COMBINED_MD.write_bytes(old_bytes + b"\n\n" + SOURCE.read_bytes())
    if not COMBINED_MD.read_bytes().startswith(old_bytes):
        raise RuntimeError("Combined Markdown failed exact byte-prefix validation")

    from PIL import Image, ImageChops

    old_images = render(OLD_PDF, "original")
    append_images = render(APPEND_PDF, "append")
    combined_images = render(COMBINED_PDF, "combined")
    comparisons = []
    for index, source_image in enumerate(old_images + append_images):
        with Image.open(source_image) as source, Image.open(combined_images[index]) as merged:
            same = source.size == merged.size and ImageChops.difference(source.convert("RGB"), merged.convert("RGB")).getbbox() is None
        comparisons.append({"page": index + 1, "pixel_identical_at_130dpi": same})
    protect_inputs()
    report = {
        "old_pages": 3, "append_pages": append_pages, "combined_pages": len(combined_images),
        "merge_method": "Poppler pdfunite: PDF page object concatenation",
        "old_markdown_exact_byte_prefix": True,
        "protected_input_sha256": {str(path.relative_to(HERE)): value for path, value in EXPECTED_INPUT_HASHES.items()},
        "page_render_comparisons": comparisons,
    }
    (BUILD / "board_validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    if not all(item["pixel_identical_at_130dpi"] for item in comparisons):
        raise RuntimeError("Imported pages differ visually; inspect board_validation.json before delivery")
    fonts = command(["pdffonts", str(COMBINED_PDF)])
    (BUILD / "combined_fonts.txt").write_text(fonts, encoding="utf-8")
    for line in fonts.splitlines()[2:]:
        font_flags = re.search(r"\s+(yes|no)\s+(yes|no)\s+(yes|no)\s+\d+\s+\d+\s*$", line)
        if font_flags and font_flags.group(1) != "yes":
            raise RuntimeError(f"PDF font is not embedded: {line}")
    text = command(["pdftotext", "-layout", str(COMBINED_PDF), "-"])
    (BUILD / "combined_text.txt").write_text(text, encoding="utf-8")
    print(f"Appended PDF: {append_pages} A4 pages; combined PDF: {len(combined_images)} pages.")
    print("Old MD/PDF/builder hashes unchanged; exact MD byte prefix and every PDF page pixel comparison passed.")
    print("Visually inspect every append/combined PNG before delivery.")


if __name__ == "__main__":
    main()
