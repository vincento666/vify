SUPPORTED_EXTENSIONS = {"txt", "md", "pdf"}
MAX_DOCUMENT_BYTES = 10 * 1024 * 1024


def validate_document_file(filename: str, size: int) -> None:
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError("Only TXT, MD and PDF documents are supported")
    if size > MAX_DOCUMENT_BYTES:
        raise ValueError("Document size must not exceed 10MB")


def document_extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
