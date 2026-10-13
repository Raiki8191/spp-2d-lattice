"""Build the A4 speaker cheat sheet using the existing local LuaLaTeX.

Only board/board_notes_01-10.pdf and .build/ten-slide/board_cheatsheet intermediates
are written. No third-party Python packages or installation are required.
The editable source is board/board_notes_01-10.md.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "board" / "board_notes_01-10.md"
TARGET = HERE / "board" / "board_notes_01-10.pdf"
BUILD = HERE / ".build" / "ten-slide" / "board_cheatsheet"


def escape_text(value: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
        "<": r"\textless{}",
        ">": r"\textgreater{}",
    }
    return "".join(replacements.get(char, char) for char in value)


INLINE = re.compile(r"(\$[^$\n]+\$|`[^`\n]+`|\*\*[^*\n]+\*\*)")


def inline(value: str) -> str:
    pieces = []
    for piece in INLINE.split(value):
        if piece.startswith("$") and piece.endswith("$"):
            pieces.append(piece)
        elif piece.startswith("`") and piece.endswith("`"):
            # nolinkurl wraps path names and literal underscores without links.
            pieces.append(r"\nolinkurl{" + piece[1:-1] + "}")
        elif piece.startswith("**") and piece.endswith("**"):
            pieces.append(r"\textbf{" + inline(piece[2:-2]) + "}")
        else:
            pieces.append(escape_text(piece))
    return "".join(pieces)


def table_cells(line: str) -> list[str]:
    # Vertical bars inside inline math (e.g. set cardinality) are not separators.
    cells, current = [], []
    in_math = in_code = False
    for char in line.strip().strip("|"):
        if char == "$" and not in_code:
            in_math = not in_math
        elif char == "`" and not in_math:
            in_code = not in_code
        if char == "|" and not in_math and not in_code:
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    cells.append("".join(current).strip())
    return cells


def render_table(lines: list[str]) -> str:
    rows = [table_cells(line) for line in lines]
    rows = [row for row in rows if not all(re.fullmatch(r"[-: ]+", c) for c in row)]
    count = len(rows[0])
    if any(len(row) != count for row in rows):
        raise ValueError(f"Inconsistent table columns: {rows}")
    widths = {3: [0.25, 0.23, 0.52], 6: [0.055, 0.23, 0.14, 0.19, 0.235, 0.15]}[count]
    if abs(sum(widths) - 1) > 1e-9:
        raise ValueError("Table widths must sum to one")
    columns = "".join(
        r">{\raggedright\arraybackslash}p{\dimexpr"
        + str(width)
        + r"\linewidth-2\tabcolsep\relax}"
        for width in widths
    )
    result = [r"\begingroup", r"\fontsize{9.2}{13.5}\selectfont", r"\setlength{\tabcolsep}{3pt}"]
    result += [r"\begin{longtable}{" + columns + "}", r"\toprule"]
    header = " & ".join(r"\textbf{" + inline(cell) + "}" for cell in rows[0]) + r" \\"
    result += [header, r"\midrule", r"\endfirsthead", r"\toprule", header, r"\midrule", r"\endhead"]
    result += [r"\bottomrule", r"\endfoot"]
    for row in rows[1:]:
        result += [" & ".join(inline(cell) for cell in row) + r" \\[3pt]"]
    result += [r"\end{longtable}", r"\endgroup"]
    return "\n".join(result)


def markdown_to_latex(markdown: str) -> str:
    lines = markdown.splitlines()
    output, paragraph = [], []

    def flush() -> None:
        if paragraph:
            output.append(inline(" ".join(paragraph)) + "\n")
            paragraph.clear()

    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            flush()
            index += 1
            continue
        if line == "<!-- pagebreak -->":
            flush()
            output.append(r"\clearpage")
        elif line == "<!-- write -->":
            flush()
            output.append(r"\begin{writebox}")
        elif line == "<!-- /write -->":
            flush()
            output.append(r"\end{writebox}")
        elif line == "$$":
            flush()
            math_lines = []
            index += 1
            while index < len(lines) and lines[index].strip() != "$$":
                math_lines.append(lines[index])
                index += 1
            if index >= len(lines):
                raise ValueError("Unclosed display math")
            output.append("{\\fontsize{13.5}{19}\\selectfont\\[\n" + "\n".join(math_lines) + "\n\\]}")
        elif line.startswith("```"):
            flush()
            code = []
            index += 1
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code.append(lines[index])
                index += 1
            output.append("\\begin{small}\n\\begin{verbatim}\n" + "\n".join(code) + "\n\\end{verbatim}\n\\end{small}")
        elif line.startswith("|"):
            flush()
            table = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table.append(lines[index])
                index += 1
            output.append(render_table(table))
            continue
        elif line.startswith("#"):
            flush()
            match = re.fullmatch(r"(#{1,4}) (.+)", line)
            if not match:
                raise ValueError(f"Unsupported heading: {line}")
            level, title = len(match[1]), inline(match[2])
            command = {1: "DocTitle", 2: "section", 3: "subsection", 4: "subsubsection"}[level]
            if level == 1:
                output.append(r"\DocTitle{" + title + "}")
            else:
                needed_lines = 4 if level == 2 else 3
                output.append("\\needspace{" + str(needed_lines) + "\\baselineskip}\\" + command + "*{" + title + "}")
        elif line.startswith("- "):
            flush()
            items = []
            while index < len(lines) and lines[index].strip().startswith("- "):
                items.append(r"\item " + inline(lines[index].strip()[2:]))
                index += 1
            output.append("\\begin{itemize}\n" + "\n".join(items) + "\n\\end{itemize}")
            continue
        else:
            paragraph.append(line)
        index += 1
    flush()
    return "\n\n".join(output)


PREAMBLE = r"""\documentclass[a4paper,11pt]{ltjsarticle}
\usepackage[left=18mm,right=18mm,top=16mm,bottom=16mm]{geometry}
\usepackage{luatexja-fontspec}
\setmainjfont{Meiryo}
\setsansjfont{Meiryo}
\setmainfont{TeX Gyre Termes}
\setsansfont{TeX Gyre Heros}
\usepackage{amsmath,amssymb}
\usepackage{booktabs,longtable,array,enumitem,needspace,xcolor,url,tcolorbox}
\usepackage[unicode,hidelinks]{hyperref}
\hypersetup{pdftitle={2026年10月15日 ゼミ発表用カンニングペーパー},pdfauthor={}}
\definecolor{HeadingBlue}{HTML}{17365D}
\newcommand{\DocTitle}[1]{{\color{HeadingBlue}\sffamily\bfseries\fontsize{17}{23}\selectfont #1\par}\vspace{2mm}}
\newtcolorbox{writebox}{colback=HeadingBlue!3,colframe=HeadingBlue!60,
  boxrule=.5pt,sharp corners,left=5pt,right=5pt,top=4pt,bottom=4pt,
  before skip=4pt,after skip=4pt}
\makeatletter
\renewcommand{\section}{\@startsection{section}{1}{\z@}{1.1ex plus .3ex minus .1ex}{.6ex}{\normalfont\fontsize{14}{19}\selectfont\sffamily\bfseries\color{HeadingBlue}}}
\renewcommand{\subsection}{\@startsection{subsection}{2}{\z@}{.7ex plus .2ex minus .1ex}{.3ex}{\normalfont\fontsize{11.5}{15.2}\selectfont\sffamily\bfseries\color{HeadingBlue}}}
\renewcommand{\subsubsection}{\@startsection{subsubsection}{3}{\z@}{.9ex plus .2ex minus .1ex}{.4ex}{\normalfont\normalsize\bfseries}}
\makeatother
\setlength{\parindent}{0pt}
\setlength{\parskip}{1.5pt}
\setlength{\emergencystretch}{2em}
\setlength{\LTpre}{.5em}
\setlength{\LTpost}{.5em}
\setlist[itemize]{leftmargin=1.4em,itemsep=3pt,topsep=3pt}
\renewcommand{\arraystretch}{1.13}
\AtBeginDocument{\fontsize{11.5}{15.2}\selectfont
  \setlength{\abovedisplayskip}{5pt}\setlength{\belowdisplayskip}{5pt}
  \setlength{\abovedisplayshortskip}{3pt}\setlength{\belowdisplayshortskip}{3pt}}
\urlstyle{tt}
\pagestyle{plain}
\begin{document}
"""


def main() -> None:
    latex = shutil.which("lualatex")
    if not latex:
        raise SystemExit("LuaLaTeX not found; no installation will be attempted.")
    source_text = SOURCE.read_text(encoding="utf-8")
    for slide_block in ["1〜6", "7", "8", "9", "10"]:
        if source_text.count("## 【対応：スライド" + slide_block + "】") != 1:
            raise ValueError(f"Expected one block for slides {slide_block}")
    if source_text.count("<!-- write -->") != source_text.count("<!-- /write -->"):
        raise ValueError("Unbalanced blackboard boxes")
    BUILD.mkdir(parents=True, exist_ok=True)
    tex_path = BUILD / "board_notes_01-10.tex"
    tex_path.write_text(PREAMBLE + markdown_to_latex(source_text) + "\n\\end{document}\n", encoding="utf-8")
    logs = []
    for run in range(2):
        result = subprocess.run(
            [latex, "-interaction=nonstopmode", "-halt-on-error", "-file-line-error", tex_path.name],
            cwd=BUILD, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        logs.append(result.stdout)
        (BUILD / f"lualatex_run_{run + 1}.log").write_bytes(result.stdout)
        if result.returncode:
            print(result.stdout.decode("utf-8", errors="replace")[-7000:])
            raise SystemExit(f"LuaLaTeX failed; see {BUILD}")
    built = BUILD / TARGET.name
    if not built.is_file() or built.stat().st_size < 10000:
        raise SystemExit("Expected a nonempty board-notes PDF.")
    info = subprocess.check_output(["pdfinfo", "-enc", "UTF-8", str(built)],
                                   text=True, encoding="utf-8", errors="replace")
    pages = int(re.search(r"Pages:\s+(\d+)", info).group(1))
    if not 3 <= pages <= 4:
        raise SystemExit(f"Expected 3-4 A4 pages, got {pages}; inspect {BUILD}")
    log_text = tex_path.with_suffix(".log").read_text(encoding="utf-8", errors="replace")
    if "Missing character:" in log_text or "Overfull \\hbox" in log_text or "Overfull \\vbox" in log_text:
        raise SystemExit(f"Missing glyph or overflow; inspect {BUILD}")
    shutil.copyfile(built, TARGET)
    print(f"Built: {TARGET.relative_to(HERE)} ({TARGET.stat().st_size:,} bytes)")
    print(f"A4 pages: {pages}; body: 11.5 pt; display math: 13.5 pt.")
    print("Re-render and visually review every PDF page after content changes.")


if __name__ == "__main__":
    main()
