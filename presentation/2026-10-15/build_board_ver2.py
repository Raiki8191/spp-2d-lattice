"""Build Ver.2 notes while keeping Ver.1 PDF pages 1-7 as native PDF pages.

Inputs, including Ver.1, are read-only. The public protection manifest stores
their pre-task SHA-256 values. LuaLaTeX and Poppler must already be installed.
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
BUILD = HERE / ".build" / "ver2_board"
SOURCE = BOARD / "board_notes_ver2.md"
TARGET = SOURCE.with_suffix(".pdf")
VER1_MD = BOARD / "board_notes_ver1.md"
VER1_PDF = VER1_MD.with_suffix(".pdf")
STYLE_BUILDER = HERE / "build_board_01_10.py"
STYLE_SHA256 = "4a49c1104bd772a7164b7e43c9ba1cb0ed5c68024556c6efe28aa101e89ee0bd"
PROTECTION = HERE / "ver2_protected_inputs.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protect_inputs() -> dict[str, str]:
    protected = json.loads(PROTECTION.read_text(encoding="utf-8-sig"))
    for name, expected in protected.items():
        if digest(HERE / name) != expected:
            raise RuntimeError(f"Protected input changed; stop for review: {name}")
    if digest(STYLE_BUILDER) != STYLE_SHA256:
        raise RuntimeError("Established pure renderer/style changed; stop for review")
    return protected


def command(args: list[str]) -> str:
    return subprocess.check_output(args, text=True, encoding="utf-8", errors="replace")


def page_count(path: Path) -> int:
    return int(re.search(r"Pages:\s+(\d+)", command(["pdfinfo", "-enc", "UTF-8", str(path)])).group(1))


def preserved_content() -> tuple[bytes, bytes]:
    old = VER1_MD.read_bytes()
    prefix = old[:old.index("## 【対応：スライド15】".encode("utf-8"))]
    suffix = old[old.index("### 【19】".encode("utf-8")):]
    return prefix, suffix


def validate_source() -> tuple[str, bytes, bytes]:
    prefix, suffix = preserved_content()
    new = SOURCE.read_bytes()
    if not new.startswith(prefix):
        raise RuntimeError("Ver.1 Markdown through slide 14 must be an exact byte prefix")
    if not new.endswith(suffix):
        raise RuntimeError("Existing slide 19-23 content must remain byte-verbatim")
    appended = new[len(prefix):].decode("utf-8")
    for label in ["15", "15（続き）", "16", "17", "18", "19〜23"]:
        if appended.count(f"## 【対応：スライド{label}】") != 1:
            raise RuntimeError(f"Missing or repeated Ver.2 board section: {label}")
    if appended.count("<!-- write -->") != appended.count("<!-- /write -->"):
        raise RuntimeError("Unbalanced blackboard boxes")
    return appended, prefix, suffix


def compile_tex(body: str) -> Path:
    path = BUILD / "board_notes_ver2_append.tex"
    path.write_text(body, encoding="utf-8")
    for run in range(2):
        result = subprocess.run(
            ["lualatex", "-interaction=nonstopmode", "-halt-on-error", "-file-line-error", path.name],
            cwd=BUILD, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        (BUILD / f"compile_{run + 1}.log").write_bytes(result.stdout)
        if result.returncode:
            raise RuntimeError(result.stdout.decode("utf-8", errors="replace")[-6500:])
    log = path.with_suffix(".log").read_text(encoding="utf-8", errors="replace")
    for issue in ["Missing character:", "Overfull \\hbox", "Overfull \\vbox"]:
        if issue in log:
            raise RuntimeError(f"Typesetting problem: {issue}; inspect {path.with_suffix('.log')}")
    return path.with_suffix(".pdf")


def render(path: Path, prefix: str, last: int | None = None) -> list[Path]:
    args = ["pdftoppm", "-r", "130", "-png"]
    if last is not None:
        args += ["-f", "1", "-l", str(last)]
    subprocess.run(args + [str(path), str(BUILD / prefix)], check=True)
    count = page_count(path)
    width = len(str(count))
    return [BUILD / f"{prefix}-{page:0{width}d}.png" for page in range(1, (last or count) + 1)]


def main() -> None:
    for executable in ["lualatex", "pdfseparate", "pdfunite", "pdfinfo", "pdftoppm", "pdftotext", "pdffonts"]:
        if shutil.which(executable) is None:
            raise RuntimeError(f"Existing tool unavailable: {executable}; no installation attempted")
    protected = protect_inputs()
    appended, prefix, suffix = validate_source()
    if page_count(VER1_PDF) != 10:
        raise RuntimeError("Expected the protected 10-page Ver.1 board PDF")
    BUILD.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location("protected_original_board_style", STYLE_BUILDER)
    style = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(style)
    preamble = style.PREAMBLE.replace(
        "2026年10月15日 ゼミ発表用カンニングペーパー", "2026年10月15日 ゼミ発表用カンニングペーパー Ver.2"
    ).replace("before skip=4pt,after skip=4pt", "before skip=4pt,after skip=9pt")
    append_pdf = compile_tex(preamble + "\n\\setcounter{page}{8}\n" + style.markdown_to_latex(appended) + "\n\\end{document}\n")
    # Extract PDF objects, never rasterize or re-typeset the protected pages.
    subprocess.run(["pdfseparate", "-f", "1", "-l", "7", str(VER1_PDF), str(BUILD / "preserved-%d.pdf")], check=True)
    kept_pages = [BUILD / f"preserved-{number}.pdf" for number in range(1, 8)]
    built = BUILD / "board_notes_ver2.pdf"
    subprocess.run(["pdfunite", *map(str, kept_pages), str(append_pdf), str(built)], check=True)
    if page_count(built) != 7 + page_count(append_pdf):
        raise RuntimeError("Unexpected concatenated page count")
    shutil.copyfile(built, TARGET)
    old_images = render(VER1_PDF, "original", last=7)
    append_images = render(append_pdf, "append")
    final_images = render(TARGET, "final")
    from PIL import Image, ImageChops

    comparisons = []
    for index, original in enumerate(old_images + append_images):
        with Image.open(original) as source, Image.open(final_images[index]) as final:
            equal = source.size == final.size and ImageChops.difference(source.convert("RGB"), final.convert("RGB")).getbbox() is None
        comparisons.append({"page": index + 1, "pixel_identical_at_130dpi": equal})
    if not all(item["pixel_identical_at_130dpi"] for item in comparisons):
        raise RuntimeError("PDF page concatenation altered visual content")
    fonts = command(["pdffonts", str(TARGET)])
    (BUILD / "fonts.txt").write_text(fonts, encoding="utf-8")
    for line in fonts.splitlines()[2:]:
        flags = re.search(r"\s+(yes|no)\s+(yes|no)\s+(yes|no)\s+\d+\s+\d+\s*$", line)
        if flags and flags.group(1) != "yes":
            raise RuntimeError(f"PDF font not embedded: {line}")
    text = command(["pdftotext", "-enc", "UTF-8", "-layout", str(TARGET), "-"])
    (BUILD / "text.txt").write_text(text, encoding="utf-8")
    mapping = [
        {"page": number, "section_labels": re.findall(r"【対応：スライド([^】]+)】", content)}
        for number, content in enumerate(text.split("\f")[:-1], 1)
    ]
    protect_inputs()
    report = {
        "status": "PASS_PENDING_VISUAL_REVIEW", "pages": page_count(TARGET),
        "protected_first_pages": 7, "new_append_pages": page_count(append_pdf),
        "body_font_pt": 11.5, "display_math_font_pt": 13.5,
        "protected_input_sha256": protected,
        "style_builder_sha256": STYLE_SHA256,
        "old_markdown_exact_byte_prefix": True, "prefix_bytes": len(prefix),
        "old_19_to_23_verbatim": True, "suffix_bytes": len(suffix),
        "merge_method": "Poppler pdfseparate + pdfunite: native PDF page objects",
        "page_render_comparisons": comparisons, "page_mapping": mapping,
        "output_sha256": {str(SOURCE.relative_to(HERE)): digest(SOURCE), str(TARGET.relative_to(HERE)): digest(TARGET)},
    }
    (BUILD / "validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"pages": report["pages"], "append_pages": report["new_append_pages"], "page_mapping": mapping}, ensure_ascii=False, indent=2))
    print("All protected hashes unchanged; exact 1-14 Markdown prefix; 19-23 byte-verbatim; first 7 PDF pages pixel-identical at 130 dpi.")
    print("Visually inspect the final PNGs before delivery.")


if __name__ == "__main__":
    main()
