# -*- coding: utf-8 -*-
"""CORAX Blind Brief stripper.

Removes conclusion paragraphs from Producer output to create a blind brief
for Codex-Reviewer. See references/blind-brief-template.md.
"""

import re
from pathlib import Path
from typing import Any

# Conclusion keywords — paragraph containing any of these gets stripped
_CONCLUSION_EN = re.compile(
    r"\b(therefore|thus|hence|consequently|as a result"
    r"|we find|we show|we demonstrate|we conclude|the analysis shows"
    r"|significantly|significant improvement|outperforms?|beats|superior to"
    r"|best|optimal|state-of-the-art|novel|revolutionary"
    r"|evidence suggests|supports the hypothesis|validates)\b",
    re.IGNORECASE,
)
_CONCLUSION_CN = re.compile(
    r"(因此|所以|从而|综上|综合来看"
    r"|证明|表明|说明|证实|验证"
    r"|显著|大幅|明显优于|超过|击败"
    r"|最佳|最优|突破性|创新)"
)
_SUBJECTIVE_EN = re.compile(
    r"\bI (think|believe)\b|\bseems\b|\barguably\b|\bin my opinion\b",
    re.IGNORECASE,
)
_SUBJECTIVE_CN = re.compile(r"(我认为|我相信|看起来)")

# Code block pattern (multi-line)
_CODE_BLOCK = re.compile(r"```[\s\S]*?```")
# Table row
_TABLE_ROW = re.compile(r"^\|.*\|$")


def strip_brief(phase_output_path: str, out_path: str) -> dict[str, Any]:
    """Strip conclusions from phase-output.md and write blind-brief.md.

    Returns {brief_path, stripped_sections, original_lines, brief_lines}.
    """
    src = Path(phase_output_path)
    if not src.exists():
        return {"error": f"File not found: {phase_output_path}"}
    if not src.is_file():
        return {"error": f"Not a file: {phase_output_path}"}

    content = src.read_text(encoding="utf-8")
    original_lines = len(content.splitlines())

    # Protect code blocks — replace with placeholders
    code_blocks: list[str] = []

    def _save_code(m: re.Match) -> str:
        idx = len(code_blocks)
        code_blocks.append(m.group(0))
        return f"__CODEBLOCK_{idx}__"

    protected = _CODE_BLOCK.sub(_save_code, content)

    # Parse into sections (heading + content)
    sections = _parse_sections(protected)
    stripped_sections: list[str] = []
    output_sections: list[str] = []

    for heading, body in sections:
        filtered_paras = []
        paragraphs = _split_paragraphs(body)
        section_stripped = False

        for para in paragraphs:
            # Table rows are exempt
            if _is_table(para):
                filtered_paras.append(para)
                continue

            # Check for conclusion keywords
            if _has_conclusion(para):
                filtered_paras.append("<REDACTED: conclusion paragraph>")
                section_stripped = True
            else:
                filtered_paras.append(para)

        if section_stripped:
            stripped_sections.append(heading or "(top-level)")

        # If all non-table paragraphs were redacted
        real_paras = [p for p in filtered_paras if not p.startswith("<REDACTED")]
        if not real_paras and paragraphs:
            output_sections.append(
                f"{heading}\n\n<REDACTED: entire section stripped>\n"
                if heading
                else "<REDACTED: entire section stripped>\n"
            )
            stripped_sections.append(heading or "(top-level)")
        else:
            section_text = "\n\n".join(filtered_paras)
            if heading:
                output_sections.append(f"{heading}\n\n{section_text}\n")
            else:
                output_sections.append(f"{section_text}\n")

    result_text = "\n".join(output_sections)

    # Restore code blocks
    for idx, block in enumerate(code_blocks):
        result_text = result_text.replace(f"__CODEBLOCK_{idx}__", block)

    # Prepend blind brief header
    header = (
        "> **Note for Reviewer**: This brief has been stripped of Producer's "
        "conclusions and subjective judgments.\n"
        "> You are seeing data, methodology, and raw metrics only. "
        "Draw your own conclusions from the facts.\n"
        "> Placeholder markers like `<REDACTED: ...>` indicate where "
        "conclusion paragraphs were removed.\n\n"
    )
    result_text = header + result_text

    # Write output
    dst = Path(out_path)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(result_text, encoding="utf-8")
    brief_lines = len(result_text.splitlines())

    return {
        "brief_path": str(dst),
        "stripped_sections": stripped_sections,
        "original_lines": original_lines,
        "brief_lines": brief_lines,
    }


def _parse_sections(text: str) -> list[tuple[str | None, str]]:
    """Split markdown text into (heading, body) pairs."""
    lines = text.split("\n")
    sections: list[tuple[str | None, str]] = []
    current_heading: str | None = None
    current_body: list[str] = []

    for line in lines:
        if line.startswith("#"):
            if current_heading is not None or current_body:
                sections.append((current_heading, "\n".join(current_body)))
            current_heading = line
            current_body = []
        else:
            current_body.append(line)

    if current_heading is not None or current_body:
        sections.append((current_heading, "\n".join(current_body)))

    return sections


def _split_paragraphs(text: str) -> list[str]:
    """Split text into paragraphs by double newlines."""
    raw = re.split(r"\n\s*\n", text.strip())
    return [p.strip() for p in raw if p.strip()]


def _is_table(para: str) -> bool:
    """Check if paragraph is a markdown table."""
    lines = para.strip().split("\n")
    return all(_TABLE_ROW.match(line.strip()) for line in lines if line.strip())


def _has_conclusion(para: str) -> bool:
    """Check if paragraph contains conclusion/subjective keywords."""
    return bool(
        _CONCLUSION_EN.search(para)
        or _CONCLUSION_CN.search(para)
        or _SUBJECTIVE_EN.search(para)
        or _SUBJECTIVE_CN.search(para)
    )
