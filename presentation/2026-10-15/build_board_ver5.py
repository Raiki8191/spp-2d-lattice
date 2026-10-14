"""Build only Ver.5 speaker notes with explicit oral/blackboard transitions.

Existing notes, slides, original papers and the pure renderer are read-only.
LuaLaTeX and Poppler must already exist; no packages or fonts are installed.
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
SOURCE = HERE / "board" / "board_notes_ver5.md"
TARGET = SOURCE.with_suffix(".pdf")
BUILD = HERE / ".build" / "ver5_board"
RENDERER = HERE / "build_board_01_10.py"
PROTECTED = {
    "board/board_notes_ver4.md": "d8bb22cffef7d7b320a546296847e49f678e39d242f0adefee6b677d97c00597",
    "board/board_notes_ver4.pdf": "7dab98c06b2d57b9a447a38897289b377bde8d8b8c77368a38f3b48c87ac87df",
    "board/board_notes_ver3.md": "440bc77655fb036b290dc84cbfd147a25b8f969b8181276f57bca576b30d0a91",
    "board/board_notes_ver3.pdf": "ee52b830f90f7d44edf9f347824fc657dfbef699e41f5ce013b912baa5f36072",
    "slides/seminar_ver3.pptx": "ce39166f542a48cc923e23cdc7b239a45f41e0ab22218c21d44a51adaaa30421",
    "slides/seminar_ver3.pdf": "a5825e27b32bcb2f326e4c94b634b6aacd0041ed816c5166ac1129b9f3c8b652",
    "build_board_01_10.py": "4a49c1104bd772a7164b7e43c9ba1cb0ed5c68024556c6efe28aa101e89ee0bd",
    "sources_local/papers/spp_main.pdf": "832a33f7605fbb72fac0a5493bcfa5a053e9908afdb856f34c6fc5660003b6bb",
    "sources_local/papers/spp_supplement.pdf": "d6660c8a293ef8cc8856a6654eafbf8b6166ad00aa8d3edb1330b16d510764d0",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protect_inputs() -> None:
    for name, expected in PROTECTED.items():
        if digest(HERE / name) != expected:
            raise RuntimeError(f"Protected input changed; stop for review: {name}")


def command(args: list[str]) -> str:
    return subprocess.check_output(args, text=True, encoding="utf-8", errors="replace")


def page_count(path: Path) -> int:
    return int(re.search(r"Pages:\s+(\d+)", command(["pdfinfo", "-enc", "UTF-8", str(path)])).group(1))


def validate_source(text: str) -> None:
    headings = list(re.finditer(r"^## 【スライド(\d+)・([^】]+)】$", text, re.MULTILINE))
    numbers = [int(heading.group(1)) for heading in headings]
    if numbers != list(range(7, 24)):
        raise RuntimeError(f"Expected ordered slide sections 7-23; found {numbers}")
    forbidden = ["【ポイント", "【記号", "【補足", "【質問時のみ", "【前提", "書く①", "12-A", "12-B", "12-C", "12-D", "12-E"]
    if any(label in text for label in forbidden):
        raise RuntimeError("An excessive template label or obsolete 12 part remains")
    if text.count("<!-- write -->") != text.count("<!-- /write -->"):
        raise RuntimeError("Unbalanced blackboard boxes")
    blackboard_counts = {8: 1, 10: 1, 12: 3, 13: 1, 15: 1, 16: 1, 17: 1, 18: 1, 20: 2}
    oral_counts = {12: 3, 18: 2, 20: 2, 23: 2}
    for index, heading in enumerate(headings):
        number = int(heading.group(1))
        body = text[heading.end():headings[index + 1].start() if index + 1 < len(headings) else len(text)]
        if body.count("**【話す】**") < oral_counts.get(number, 1):
            raise RuntimeError(f"Slide {number}: required oral transition blocks are missing")
        if body.count("<!-- write -->") != blackboard_counts.get(number, 0):
            raise RuntimeError(f"Slide {number}: incorrect blackboard block count")
        if number == 20 and any(symbol in body for symbol in ["Y(N)", "AN^", "\\alpha"]):
            raise RuntimeError("Slide 20 must use the actual shift, not generic auxiliary variables")


def compile_tex(body: str) -> Path:
    path = BUILD / "board_notes_ver5.tex"
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


def main() -> None:
    for executable in ["lualatex", "pdfinfo", "pdftoppm", "pdftotext", "pdffonts"]:
        if shutil.which(executable) is None:
            raise RuntimeError(f"Existing tool unavailable: {executable}; no installation attempted")
    protect_inputs()
    source = SOURCE.read_text(encoding="utf-8")
    validate_source(source)
    BUILD.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location("protected_pure_board_renderer", RENDERER)
    renderer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(renderer)
    preamble = renderer.PREAMBLE.replace(
        "2026年10月15日 ゼミ発表用カンニングペーパー", "2026年10月15日 ゼミ発表用カンニングペーパー Ver.5"
    ).replace("before skip=4pt,after skip=4pt", "before skip=4pt,after skip=8pt")
    rendered = renderer.markdown_to_latex(source).replace(
        r"\fontsize{13.5}{19}", r"\fontsize{14.5}{20}"
    )
    built = compile_tex(preamble + rendered + "\n\\end{document}\n")
    shutil.copyfile(built, TARGET)
    pages = page_count(TARGET)
    subprocess.run(["pdftoppm", "-r", "130", "-png", str(TARGET), str(BUILD / "page")], check=True)
    fonts = command(["pdffonts", str(TARGET)])
    (BUILD / "fonts.txt").write_text(fonts, encoding="utf-8")
    for line in fonts.splitlines()[2:]:
        flags = re.search(r"\s+(yes|no)\s+(yes|no)\s+(yes|no)\s+\d+\s+\d+\s*$", line)
        if flags and flags.group(1) != "yes":
            raise RuntimeError(f"PDF font not embedded: {line}")
    text = command(["pdftotext", "-enc", "UTF-8", "-layout", str(TARGET), "-"])
    if "**" in text:
        raise RuntimeError("Unrendered Markdown emphasis in PDF")
    (BUILD / "text.txt").write_text(text, encoding="utf-8")
    mapping = [
        {"page": page, "slides": [int(number) for number in re.findall(r"【スライド\s*(\d+)", content)],
         "oral_blocks": content.count("【話す】"), "blackboard_blocks": content.count("【板書】")}
        for page, content in enumerate(text.split("\f")[:-1], 1)
    ]
    if [slide for page in mapping for slide in page["slides"]] != list(range(7, 24)):
        raise RuntimeError("Rendered slide heading sequence does not match 7-23")
    protect_inputs()
    report = {
        "status": "PASS_PENDING_VISUAL_REVIEW", "pages": pages,
        "body_font_pt": 11.5, "display_math_font_pt": 14.5,
        "protected_input_sha256": PROTECTED, "page_mapping": mapping,
        "font_embedding": "all listed fonts embedded", "typesetting_overflow": False,
        "all_slides_have_oral_blocks": True, "blackboard_boxes": 12,
        "slide_12_three_stages": True, "slide_20_uses_actual_shift": True,
        "output_sha256": {str(SOURCE.relative_to(HERE)): digest(SOURCE), str(TARGET.relative_to(HERE)): digest(TARGET)},
    }
    (BUILD / "validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"pages": pages, "page_mapping": mapping}, ensure_ascii=False, indent=2))
    print("Protected notes/slides/primary PDFs unchanged; fonts embedded; no missing glyphs/overflows/obsolete template labels.")
    print("Visually review all pages and the transitions in slides 12, 15-18, 20, 23 before delivery.")


if __name__ == "__main__":
    main()
