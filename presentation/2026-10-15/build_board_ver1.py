"""Build Ver.1 integrated A4 speaker notes; never write protected inputs.

The first three pages are concatenated from the established PDF with pdfunite.
Only the Ver.1 Markdown and the generated Ver.1 PDF are task deliverables.
LuaLaTeX, Poppler and Pillow must already be installed; nothing is installed.
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
BUILD = HERE / ".build" / "ver1_board"
SOURCE = BOARD / "board_notes_ver1.md"
TARGET = SOURCE.with_suffix(".pdf")
OLD_MD = BOARD / "board_notes_01-10.md"
OLD_PDF = OLD_MD.with_suffix(".pdf")
OLD_APPEND = BOARD / "board_notes_fss_append.md"
OLD_BUILDER = HERE / "build_board_01_10.py"
PROTECTED = {
    "slides/seminar_with_fss.pptx": "24d2209f6e00504a0c071392331b9efcb8b9f7b316ecf92bf6169562b610fe9c",
    "slides/seminar_with_fss.pdf": "30839964c7c9d7cc5a5f6559071bf5a7bd4a03376cb820ff2c6843f96d3182a1",
    "board/board_notes_with_fss.md": "a5ab02fa4ea28bd31fabc307a7f89938f26dc62b9b33bc7f4726b2590a27c4af",
    "board/board_notes_with_fss.pdf": "5123e2b602971d3f87bb023d53452f250f97cafd78c5a67087ec4d4387c5a2bd",
    "board/board_notes_01-10.md": "345228c1bf5180189f13973f204997c3ac7dcb472c786eda546bff8315869c7a",
    "board/board_notes_01-10.pdf": "30fb0e8b8ef72d3c5ae87318a283298323007aa21bd79a0162abd3a820699c3f",
    "build_board_01_10.py": "4a49c1104bd772a7164b7e43c9ba1cb0ed5c68024556c6efe28aa101e89ee0bd",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protect_inputs() -> None:
    for name, expected in PROTECTED.items():
        if digest(HERE / name) != expected:
            raise RuntimeError(f"Protected input changed; review before proceeding: {name}")


def command(args: list[str]) -> str:
    return subprocess.check_output(args, text=True, encoding="utf-8", errors="replace")


def page_count(path: Path) -> int:
    return int(re.search(r"Pages:\s+(\d+)", command(["pdfinfo", "-enc", "UTF-8", str(path)])).group(1))


def preserved_blocks() -> tuple[bytes, bytes]:
    """Old 15 starts after the old 14-only argmax paragraph; 16-23 are intact."""
    old = OLD_APPEND.read_bytes()
    start = old.index("### 【書く前の追加前提】".encode("utf-8"))
    end = old.index(b"<!-- pagebreak -->", start)
    old15 = old[start:end]
    old16 = old[old.index("## 【対応：スライド16〜17】".encode("utf-8")):]
    return old15, old16


def validate_source() -> tuple[str, bytes, bytes]:
    old_bytes = OLD_MD.read_bytes()
    source_bytes = SOURCE.read_bytes()
    if not source_bytes.startswith(old_bytes):
        raise RuntimeError("Ver.1 Markdown must retain old 1-10 as an exact byte prefix")
    old15, old16 = preserved_blocks()
    if source_bytes.count(old15) != 1 or not source_bytes.endswith(old16):
        raise RuntimeError("Existing 15-23 content must be retained verbatim")
    appended = source_bytes[len(old_bytes):].decode("utf-8")
    for label in ["11", "12-A", "12-B", "12-C", "12-D", "12-E", "13", "14", "15", "16〜17", "18〜23"]:
        if appended.count(f"## 【対応：スライド{label}】") != 1:
            raise RuntimeError(f"Missing or repeated Ver.1 section: {label}")
    if appended.count("<!-- write -->") != appended.count("<!-- /write -->"):
        raise RuntimeError("Unbalanced blackboard boxes")
    return appended, old15, old16


def compile_tex(body: str) -> Path:
    tex_path = BUILD / "board_notes_ver1_append.tex"
    tex_path.write_text(body, encoding="utf-8")
    for run in range(2):
        result = subprocess.run(
            ["lualatex", "-interaction=nonstopmode", "-halt-on-error", "-file-line-error", tex_path.name],
            cwd=BUILD, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        (BUILD / f"compile_{run + 1}.log").write_bytes(result.stdout)
        if result.returncode:
            raise RuntimeError(result.stdout.decode("utf-8", errors="replace")[-6000:])
    log = tex_path.with_suffix(".log").read_text(encoding="utf-8", errors="replace")
    for error in ["Missing character:", "Overfull \\hbox", "Overfull \\vbox"]:
        if error in log:
            raise RuntimeError(f"PDF typography error: {error}; inspect {tex_path.with_suffix('.log')}")
    return tex_path.with_suffix(".pdf")


def render(path: Path, prefix: str) -> list[Path]:
    subprocess.run(["pdftoppm", "-r", "130", "-png", str(path), str(BUILD / prefix)], check=True)
    count = page_count(path)
    width = len(str(count))
    return [BUILD / f"{prefix}-{page:0{width}d}.png" for page in range(1, count + 1)]


def main() -> None:
    for executable in ["lualatex", "pdfunite", "pdfinfo", "pdftoppm", "pdftotext", "pdffonts"]:
        if shutil.which(executable) is None:
            raise RuntimeError(f"Required existing tool unavailable: {executable}; no installation attempted")
    protect_inputs()
    appended, old15, old16 = validate_source()
    if page_count(OLD_PDF) != 3:
        raise RuntimeError("Expected the established 3-page board PDF")
    BUILD.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location("protected_board_style", OLD_BUILDER)
    style = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(style)
    # Reuse the existing pure renderer and 11.5/13.5 pt style, not its main().
    preamble = style.PREAMBLE.replace(
        "2026年10月15日 ゼミ発表用カンニングペーパー", "2026年10月15日 ゼミ発表用カンニングペーパー Ver.1"
    ).replace("before skip=4pt,after skip=4pt", "before skip=4pt,after skip=9pt")
    append_pdf = compile_tex(preamble + "\n\\setcounter{page}{4}\n" + style.markdown_to_latex(appended) + "\n\\end{document}\n")
    # Page object concatenation keeps the original first 3 pages unchanged.
    built_pdf = BUILD / "board_notes_ver1.pdf"
    subprocess.run(["pdfunite", str(OLD_PDF), str(append_pdf), str(built_pdf)], check=True)
    if page_count(built_pdf) != 3 + page_count(append_pdf):
        raise RuntimeError("Unexpected combined page count")
    shutil.copyfile(built_pdf, TARGET)
    original_images = render(OLD_PDF, "original")
    append_images = render(append_pdf, "append")
    final_images = render(TARGET, "final")
    from PIL import Image, ImageChops

    comparisons = []
    for index, input_image in enumerate(original_images + append_images):
        with Image.open(input_image) as source, Image.open(final_images[index]) as final:
            same = source.size == final.size and ImageChops.difference(source.convert("RGB"), final.convert("RGB")).getbbox() is None
        comparisons.append({"page": index + 1, "pixel_identical_at_130dpi": same})
    if not all(item["pixel_identical_at_130dpi"] for item in comparisons):
        raise RuntimeError("Concatenation changed page rendering")
    fonts = command(["pdffonts", str(TARGET)])
    (BUILD / "fonts.txt").write_text(fonts, encoding="utf-8")
    for line in fonts.splitlines()[2:]:
        flags = re.search(r"\s+(yes|no)\s+(yes|no)\s+(yes|no)\s+\d+\s+\d+\s*$", line)
        if flags and flags.group(1) != "yes":
            raise RuntimeError(f"Font not embedded: {line}")
    extracted = command(["pdftotext", "-enc", "UTF-8", "-layout", str(TARGET), "-"])
    (BUILD / "text.txt").write_text(extracted, encoding="utf-8")
    page_mapping = []
    for page, text in enumerate(extracted.split("\f")[:-1], 1):
        labels = re.findall(r"【対応：スライド([^】]+)】", text)
        page_mapping.append({"page": page, "section_labels": labels})
    protect_inputs()
    report = {
        "status": "PASS_PENDING_VISUAL_REVIEW",
        "pages": page_count(TARGET), "old_pages": 3, "append_pages": page_count(append_pdf),
        "body_font_pt": 11.5, "display_math_font_pt": 13.5,
        "protected_input_sha256": PROTECTED,
        "old_markdown_exact_byte_prefix": True,
        "old_15_verbatim_bytes": len(old15), "old_16_to_23_verbatim_bytes": len(old16),
        "preserved_15_to_23_verbatim": True,
        "merge_method": "Poppler pdfunite: PDF page object concatenation",
        "render_comparisons": comparisons,
        "page_mapping": page_mapping,
        "output_sha256": {str(SOURCE.relative_to(HERE)): digest(SOURCE), str(TARGET.relative_to(HERE)): digest(TARGET)},
    }
    (BUILD / "validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"pages": report["pages"], "append_pages": report["append_pages"], "page_mapping": page_mapping}, ensure_ascii=False, indent=2))
    print("Protected inputs unchanged; exact old Markdown prefix; old 15-23 verbatim; first 3 PDF pages pixel-identical at 130 dpi.")
    print("Review every final PNG visually before delivery.")


if __name__ == "__main__":
    main()
