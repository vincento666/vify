import unittest

from app.modules.knowledge.domain.parser import parse_document_content


class DocumentParserTest(unittest.TestCase):
    def test_txt_parser_normalizes_line_endings_and_spacing(self) -> None:
        parsed = parse_document_content("guide.txt", b" Intro   guide\r\n\r\n  Contact\t support ")

        self.assertEqual("txt", parsed.file_type)
        self.assertEqual("Intro guide\n\nContact support", parsed.text)

    def test_markdown_parser_removes_common_markup_without_losing_content(self) -> None:
        parsed = parse_document_content(
            "guide.md",
            b"# Reset Guide\r\n\r\n- Reset password\r\n- Contact **support**",
        )

        self.assertEqual("md", parsed.file_type)
        self.assertEqual("Reset Guide\n\nReset password\nContact support", parsed.text)

    def test_pdf_parser_extracts_text(self) -> None:
        parsed = parse_document_content("guide.pdf", _minimal_text_pdf("Reset password guide"))

        self.assertEqual("pdf", parsed.file_type)
        self.assertIn("Reset password guide", parsed.text)

    def test_parser_rejects_empty_documents(self) -> None:
        with self.assertRaises(ValueError):
            parse_document_content("empty.txt", b"   \r\n\t")

def _minimal_text_pdf(text: str) -> bytes:
    stream = f"BT /F1 18 Tf 72 720 Td ({text}) Tj ET".encode()
    objects = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        b"3 0 obj\n"
        b"<< /Type /Page /Parent 2 0 R "
        b"/Resources << /Font << /F1 4 0 R >> >> "
        b"/MediaBox [0 0 612 792] /Contents 5 0 R >>\nendobj\n",
        b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
        b"5 0 obj\n<< /Length "
        + str(len(stream)).encode()
        + b" >>\nstream\n"
        + stream
        + b"\nendstream\nendobj\n",
    ]
    pdf = b"%PDF-1.4\n"
    offsets: list[int] = []
    for obj in objects:
        offsets.append(len(pdf))
        pdf += obj
    xref = len(pdf)
    pdf += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for offset in offsets:
        pdf += f"{offset:010d} 00000 n \n".encode()
    pdf += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref}\n%%EOF\n"
    ).encode()
    return pdf


if __name__ == "__main__":
    unittest.main()
