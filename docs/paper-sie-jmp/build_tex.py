"""
Assemble the JMP (Elsevier elsarticle) LaTeX project from the Markdown sections.

The Markdown under docs/paper-sie-jmp/ remains the SOURCE OF TRUTH: every number
in it traces to a named experiments/ script and a runs/ artifact under the
HANDOFF protocol. The LaTeX tree this script writes is a DERIVED artifact. Edit
the Markdown and re-run; do not hand-edit the generated .tex.

The eight sections live on five branches (the case sections were reviewed and
committed on their own branches). This script reads each from its branch with
`git show`, so it works from any checkout without merging first.

Usage:
    python docs/paper-sie-jmp/build_tex.py [--out docs/paper-sie-jmp/tex]

Requires pandoc. Does not compile: no LaTeX toolchain is assumed (Overleaf
compiles). Deterministic: same inputs produce byte-identical output.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# (section file, source branch, output stem). Section 07 is an uncommitted stub
# in the working tree; None means "read from disk".
SECTIONS = [
    ("docs/paper-sie-jmp/01-intro.md", "paper/synthesis-sections", "01-intro"),
    ("docs/paper-sie-jmp/02-machinery.md", "paper/synthesis-sections", "02-machinery"),
    ("docs/paper-sie-jmp/03-case-A-external-validation.md", "paper/case-a-vanbork", "03-case-A"),
    ("docs/paper-sie-jmp/04-case-B-occam-dial.md", "paper/case-b-occam-dial", "04-case-B"),
    ("docs/paper-sie-jmp/05-case-C-nested-constraints.md", "paper/case-c-haaf", "05-case-C"),
    ("docs/paper-sie-jmp/06-case-D-mopen-calibration.md", "paper/case-d-mopen", "06-case-D"),
    ("docs/paper-sie-jmp/07-debias-bridge.md", "paper/case-e-debias", "07-debias"),
    ("docs/paper-sie-jmp/08-discussion.md", "paper/synthesis-sections", "08-discussion"),
]

# Figures: (repo path, source branch, filename in the LaTeX tree).
FIGURES = [
    ("runs/vanbork_external_validation/target_figure.png", "paper/case-a-vanbork", "vanbork_targets.png"),
    ("runs/occam_dial/occam_dial.png", "paper/case-b-occam-dial", "occam_dial.png"),
    ("runs/regret_curves_mopen/regret_curves.png", "paper/case-d-mopen", "regret_curves.png"),
    ("runs/toy_debias_demo/debias_figure.png", "paper/case-e-debias", "debias_figure.png"),
]

# Markdown image path -> filename in figures/.
FIGURE_PATHS = {
    "../../runs/vanbork_external_validation/target_figure.png": "vanbork_targets.png",
    "../../runs/occam_dial/occam_dial.png": "occam_dial.png",
    "../../runs/regret_curves_mopen/regret_curves.png": "regret_curves.png",
    "../../runs/toy_debias_demo/debias_figure.png": "debias_figure.png",
}

NOTATION_MD = "docs/paper-sie-jmp/00-notation.md"

# The Markdown carries Greek and mathematical symbols as literal Unicode, in
# prose as well as inside math. pdfLaTeX cannot set those glyphs in text mode,
# so each maps to \ensuremath{...}, which is correct in either mode and so is
# safe to apply blindly. Letters that T1/utf8 handles (ü, en/em dashes) stay.
UNICODE_MATH = {
    "τ": r"\ensuremath{\tau}",
    "φ": r"\ensuremath{\phi}",
    "ψ": r"\ensuremath{\psi}",
    "σ": r"\ensuremath{\sigma}",
    "θ": r"\ensuremath{\theta}",
    "ℓ": r"\ensuremath{\ell}",
    "Ḡ": r"\ensuremath{\bar{G}}",
    "²": r"\ensuremath{^{2}}",
    "₀": r"\ensuremath{_{0}}",
    "≈": r"\ensuremath{\approx}",
    "≥": r"\ensuremath{\geq}",
    "≤": r"\ensuremath{\leq}",
    "⊂": r"\ensuremath{\subset}",
    "⊆": r"\ensuremath{\subseteq}",
    "∫": r"\ensuremath{\int}",
    "−": r"\ensuremath{-}",
    "→": r"\ensuremath{\rightarrow}",
}


def read_source(path, branch):
    if branch is None:
        with open(os.path.join(REPO, path), encoding="utf-8") as fh:
            return fh.read()
    out = subprocess.run(
        ["git", "-C", REPO, "show", f"{branch}:{path}"],
        capture_output=True, text=True, check=True,
    )
    return out.stdout


def read_binary(path, branch):
    out = subprocess.run(
        ["git", "-C", REPO, "show", f"{branch}:{path}"],
        capture_output=True, check=True,
    )
    return out.stdout


def strip_heading_numbers(text):
    """LaTeX numbers sections itself; drop the Markdown's manual numbers."""
    text = re.sub(r"^(#+)\s+\d+(?:\.\d+)*\.?\s+", r"\1 ", text, flags=re.M)
    return text


def extract_provenance(text):
    """Pull the trailing provenance footer out of the body.

    Returns (body_without_footer, footer_text_or_None). The footer is an
    italic block after a horizontal rule at end of file.
    """
    m = re.search(r"\n---\n+\*(Provenance[^*]*)\*\s*$", text, flags=re.S)
    if not m:
        return text, None
    footer = re.sub(r"\s+", " ", m.group(1)).strip()
    return text[: m.start()].rstrip() + "\n", footer


def preprocess(text):
    """Markdown fixes that must happen before pandoc sees the text."""
    # Evidence tiers: the emoji do not survive pdflatex. Keep the tier word.
    text = text.replace("🟢 peer-reviewed —", r"\evidencetier{peer-reviewed}")
    text = text.replace("🟠 empirical —", r"\evidencetier{empirical}")
    text = text.replace("🟡 thesis —", r"\evidencetier{thesis}")
    text = text.replace("🟣 framework —", r"\evidencetier{framework}")
    text = text.replace("🔵 textbook —", r"\evidencetier{textbook}")
    for emoji in ("🟢", "🟠", "🟡", "🟣", "🔵"):
        text = text.replace(emoji, "")
    # Figure paths point into runs/ from the Markdown tree; the LaTeX tree keeps
    # its own copies under figures/.
    for md_path, fname in FIGURE_PATHS.items():
        text = text.replace(md_path, f"figures/{fname}")
    text = strip_heading_numbers(text)
    for ch, macro in UNICODE_MATH.items():
        text = text.replace(ch, macro)
    return text


def pandoc(text):
    proc = subprocess.run(
        ["pandoc", "-f", "markdown+tex_math_single_backslash", "-t", "latex",
         "--top-level-division=section", "--wrap=preserve"],
        input=text, capture_output=True, text=True, check=True,
    )
    body = proc.stdout
    # pandoc emits \label{...} slugs on every heading; keep them stable and
    # short so cross-references stay readable.
    body = re.sub(r"\\label\{[^}]*\}", "", body)
    # Images: give every figure a float with a caption drawn from the alt text.
    body = re.sub(
        r"\\includegraphics\[[^\]]*\]\{(figures/[^}]+)\}",
        r"\\includegraphics[width=\\linewidth]{\1}",
        body,
    )
    return body.strip() + "\n"


def notation_appendix():
    """The frozen notation table, minus the repo-internal source column."""
    text = read_source(NOTATION_MD, None)
    rows = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        if set("".join(cells)) <= set("-: "):
            continue
        rows.append(cells[:2])  # symbol, meaning; drop "source of truth"
    if not rows:
        return ""
    header, body_rows = rows[0], rows[1:]
    md = ["| " + " | ".join(header) + " |", "|---|---|"]
    md += ["| " + " | ".join(r) + " |" for r in body_rows]
    return pandoc(preprocess("\n".join(md)))


def references_bib(sec_dir_texts):
    """Starter bibliography extracted verbatim from the peer-reviewed footnotes.

    Nothing here is invented: each entry's `note` is the exact reference string
    the Markdown already carries, so the author can promote fields (journal,
    volume, pages) by hand without trusting a machine's guess. Keys are
    firstauthor+year. The footnote text of the two writing passes uses two
    citation styles for several works; a later editorial pass unifies them by
    switching the prose to \\citep and activating this file.
    """
    marker = r"\evidencetier{peer-reviewed}"
    seen = {}
    for text in sec_dir_texts:
        start = text.find(marker)
        while start != -1:
            # Read to the close of the enclosing \footnote{...}, counting braces
            # so nested \texttt{} and \emph{} do not end the scan early.
            i = start + len(marker)
            depth = 1
            while i < len(text) and depth > 0:
                if text[i] == "{" and text[i - 1] != "\\":
                    depth += 1
                elif text[i] == "}" and text[i - 1] != "\\":
                    depth -= 1
                i += 1
            ref = re.sub(r"\s+", " ", text[start + len(marker):i - 1]).strip()
            start = text.find(marker, i)
            ym = re.search(r"\((\d{4})\)", ref)
            year = ym.group(1) if ym else "n.d."
            am = re.match(r"([A-Za-z\-']+)", ref.replace("van Bork", "vanBork"))
            key = f"{am.group(1).lower() if am else 'ref'}{year}"
            n = 2
            base = key
            while key in seen and seen[key] != ref:
                key = f"{base}{chr(95)}{n}"; n += 1
            seen[key] = ref
    lines = ["% Starter bibliography for the JMP manuscript.",
             "% AUTO-EXTRACTED verbatim from the evidence-tier footnotes by",
             "% docs/paper-sie-jmp/build_tex.py. No field was inferred or invented:",
             "% each `note` is the reference string the Markdown source already",
             "% carries. Promote to @article with explicit journal/volume/pages",
             "% before activating \\bibliography in main.tex.", ""]
    for key in sorted(seen):
        lines += [f"@misc{{{key},", f"  note = {{{seen[key]}}}", "}", ""]
    return "\n".join(lines)


MAIN_TEX = r"""%% BI*/BMS*-GP manuscript — Journal of Mathematical Psychology (Elsevier)
%%
%% GENERATED FILE. Source of truth: docs/paper-sie-jmp/*.md in the bistar_gp_c
%% repository, where every reported number traces to a named experiments/
%% script and a committed runs/ artifact. Regenerate with:
%%     python docs/paper-sie-jmp/build_tex.py
%%
%% elsarticle.cls ships with Overleaf and with TeX Live; it is not vendored here.
%% Options: `review` double-spaces for submission; `preprint` is the default
%% single-column preprint layout.

\documentclass[preprint,12pt]{elsarticle}

\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{booktabs}
\usepackage{graphicx}
\usepackage{longtable}
\usepackage{array}
\usepackage{calc}
\usepackage[hidelinks]{hyperref}
\usepackage{url}

%% Evidence-tier marker used by the footnote citations carried over from the
%% Markdown source: each footnote states the tier of its support.
\newcommand{\evidencetier}[1]{\textsc{#1}~---~}

%% pandoc emits these when a document contains tightly spaced lists or images.
\providecommand{\tightlist}{%
  \setlength{\itemsep}{0pt}\setlength{\parskip}{0pt}}

\journal{Journal of Mathematical Psychology}

\begin{document}

\begin{frontmatter}

%% TODO(author): confirm title, authors, affiliations, abstract, keywords.
\title{Data priors without hand-specified model priors:\\
Gaussian-process BI*/BMS* and the evaluation dials it makes explicit}

\author[inst1]{AUTHOR NAME}
\ead{AUTHOR@EMAIL}
\affiliation[inst1]{organization={AFFILIATION},
                    city={CITY},
                    country={COUNTRY}}

\begin{abstract}
TODO(author): abstract. The manuscript constructs a stand-alone data prior from
Gaussian-process hyperpriors, induces parameter and model priors from it without
hand-specified per-model priors, and reports four case studies: external
validation against published closed-form targets, the reference-measure
(\texttt{occam}) dial on nested models, a satisfied ordinal constraint scored
against PSIS-LOO, and M-open calibration through regret localization. The cases
are organized around the evaluative choices the framework makes explicit as
dials: temperature, reference measure, and aggregation convention.
\end{abstract}

\begin{keyword}
model evaluation \sep data priors \sep Bayesian induction \sep Gaussian processes
\sep model selection \sep simplicity
\end{keyword}

\end{frontmatter}

%% ---------------------------------------------------------------- body ----
SECTION_INPUTS

%% ------------------------------------------------------------ appendices ----
\appendix

APPENDIX_INPUTS

%% Citations currently travel as evidence-tier footnotes, the convention of the
%% source repository. references.bib carries the works those footnotes name, so
%% a later editorial pass can switch to \citep{...} by uncommenting:
%% \bibliographystyle{elsarticle-harv}
%% \bibliography{references}

\end{document}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join("docs", "paper-sie-jmp", "tex"))
    args = ap.parse_args()

    out_dir = os.path.join(REPO, args.out)
    sec_dir = os.path.join(out_dir, "sections")
    fig_dir = os.path.join(out_dir, "figures")
    for d in (sec_dir, fig_dir):
        os.makedirs(d, exist_ok=True)

    provenance = []
    inputs = []
    for path, branch, stem in SECTIONS:
        raw = read_source(path, branch)
        body, footer = extract_provenance(raw)
        if footer:
            title = re.sub(r"^#\s+", "", body.splitlines()[0]).strip()
            provenance.append((title, footer))
        tex = pandoc(preprocess(body))
        origin = branch if branch else "working tree (uncommitted)"
        header = (f"%% Generated from {path}\n%% Source branch: {origin}\n"
                  f"%% Do not hand-edit; see docs/paper-sie-jmp/build_tex.py\n")
        with open(os.path.join(sec_dir, stem + ".tex"), "w", encoding="utf-8") as fh:
            fh.write(header + tex)
        inputs.append(f"\\input{{sections/{stem}}}")

    for path, branch, fname in FIGURES:
        with open(os.path.join(fig_dir, fname), "wb") as fh:
            fh.write(read_binary(path, branch))

    # Appendix A: notation. Appendix B: computational provenance.
    appendices = []
    notation = notation_appendix()
    if notation:
        with open(os.path.join(sec_dir, "A-notation.tex"), "w", encoding="utf-8") as fh:
            fh.write("\\section{Notation}\n\n" + notation)
        appendices.append("\\input{sections/A-notation}")

    lines = ["\\section{Computational provenance}\n",
             "Every number reported in this manuscript regenerates from a named "
             "script in the source repository into a committed run artifact. The "
             "sections and their sources follow.\n", "\\begin{description}"]
    for title, footer in provenance:
        safe_title = title.replace("&", r"\&").replace("_", r"\_")
        safe_footer = (footer.replace("&", r"\&").replace("_", r"\_")
                             .replace("·", r"$\cdot$"))
        safe_footer = re.sub(r"`([^`]*)`", r"\\texttt{\1}", safe_footer)
        for ch, macro in UNICODE_MATH.items():
            safe_title = safe_title.replace(ch, macro)
            safe_footer = safe_footer.replace(ch, macro)
        lines.append(f"\\item[{safe_title}] {safe_footer}")
    lines.append("\\end{description}")
    with open(os.path.join(sec_dir, "B-provenance.tex"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    appendices.append("\\input{sections/B-provenance}")

    section_texts = []
    for stem in [x[2] for x in SECTIONS]:
        with open(os.path.join(sec_dir, stem + ".tex"), encoding="utf-8") as fh:
            section_texts.append(fh.read())
    with open(os.path.join(out_dir, "references.bib"), "w", encoding="utf-8") as fh:
        fh.write(references_bib(section_texts))

    main_tex = (MAIN_TEX
                .replace("SECTION_INPUTS", "\n".join(inputs))
                .replace("APPENDIX_INPUTS", "\n".join(appendices)))
    with open(os.path.join(out_dir, "main.tex"), "w", encoding="utf-8") as fh:
        fh.write(main_tex)

    print(f"wrote {out_dir}")
    print(f"  main.tex, {len(inputs)} sections, {len(appendices)} appendices, "
          f"{len(FIGURES)} figures")


if __name__ == "__main__":
    main()
