import unittest

try:
    from app.modules.knowledge.domain.files import validate_document_file
except ModuleNotFoundError:
    validate_document_file = None  # type: ignore[assignment]


class DocumentFileValidationTest(unittest.TestCase):
    def test_accepts_txt_md_pdf_under_10mb(self) -> None:
        self.assertIsNotNone(validate_document_file)
        validate_document_file("guide.md", 1024)

    def test_rejects_unsupported_extension(self) -> None:
        self.assertIsNotNone(validate_document_file)
        with self.assertRaises(ValueError):
            validate_document_file("guide.exe", 1024)

    def test_rejects_file_larger_than_10mb(self) -> None:
        self.assertIsNotNone(validate_document_file)
        with self.assertRaises(ValueError):
            validate_document_file("guide.txt", 10 * 1024 * 1024 + 1)


if __name__ == "__main__":
    unittest.main()
