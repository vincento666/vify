from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import re

from pypdf import PdfReader

from app.modules.knowledge.domain.files import document_extension


@dataclass(frozen=True)
class ParsedDocument:
    file_type: str
    text: str


def parse_document_content(filename: str, content: bytes) -> ParsedDocument:
    file_type = document_extension(filename)
    if file_type == "txt":
        text = _normalize_text(_decode_text(content))
    elif file_type == "md":
        text = _normalize_markdown(_decode_text(content))
    elif file_type == "pdf":
        text = _normalize_text(_extract_pdf_text(content))
    else:
        raise ValueError("Only TXT, MD and PDF documents are supported")

    if not text.strip():
        raise ValueError("Document is empty")
    return ParsedDocument(file_type=file_type, text=text)


def _decode_text(content: bytes) -> str:
    return content.decode("utf-8-sig", errors="ignore")


def _extract_pdf_text(content: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(content))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as exc:
        raise ValueError("Unable to parse PDF document") from exc


def _normalize_markdown(text: str) -> str:
    normalized = _normalize_text(text)
    lines: list[str] = []
    in_fence = False
    for line in normalized.splitlines():
        stripped = line.strip()
        if stripped.startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if in_fence:
            lines.append(line)
            continue
        lines.append(_strip_markdown_line(line))
    return _normalize_text("\n".join(lines))


def _strip_markdown_line(line: str) -> str:
    line = re.sub(r"^\s{0,3}#{1,6}\s+", "", line)
    line = re.sub(r"^\s*[-*+]\s+", "", line)
    line = re.sub(r"^\s*\d+[.)]\s+", "", line)
    line = re.sub(r"^>\s?", "", line)
    line = re.sub(r"`([^`]+)`", r"\1", line)
    line = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", line)
    line = re.sub(r"\*\*([^*]+)\*\*", r"\1", line)
    line = re.sub(r"\*([^*]+)\*", r"\1", line)
    line = re.sub(r"__([^_]+)__", r"\1", line)
    line = re.sub(r"_([^_]+)_", r"\1", line)
    return line


def _normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\x00", "")
    normalized_lines: list[str] = []
    previous_blank = True
    for line in text.split("\n"):
        normalized_line = re.sub(r"[ \t\f\v]+", " ", line).strip()
        if not normalized_line:
            if normalized_lines and not previous_blank:
                normalized_lines.append("")
            previous_blank = True
            continue
        normalized_lines.append(normalized_line)
        previous_blank = False
    while normalized_lines and normalized_lines[-1] == "":
        normalized_lines.pop()
    return "\n".join(normalized_lines)
