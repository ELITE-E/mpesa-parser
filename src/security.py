import re
from io import BytesIO

import pypdf


class DecryptionError(Exception):
    """Raised when an encrypted file fails decryption due to bad or missing keys."""

    pass


class StructuralAttestationError(Exception):
    """Raised when a valid PDF document layout fails our digital fingerprint checks."""

    pass


def verify_pdf_magic_bytes(file_stream: BytesIO) -> None:
    """Performs a deep binary signature audit on the incoming memory buffer."""
    file_stream.seek(0)
    magic_header = file_stream.read(4)
    file_stream.seek(0)

    if magic_header != b"%PDF":
        raise ValueError("Invalid file signature: Not a valid PDF document.")


def decrypt_pdf_in_memory(file_stream: BytesIO, password: str = None) -> BytesIO:
    """Safely manages the passphrase validation loop in RAM."""
    file_stream.seek(0)
    reader = pypdf.PdfReader(file_stream)

    if not reader.is_encrypted:
        file_stream.seek(0)
        return file_stream

    return _execute_pdf_decryption(reader, password)


def attest_mpesa_structure(decrypted_stream: BytesIO) -> str:
    """Verifies document layout authenticity and extracts the verification token."""
    corpus = _extract_document_text_corpus(decrypted_stream)

    _validate_mpesa_branding_signature(corpus)

    return _extract_verification_token(corpus)


def _execute_pdf_decryption(reader: pypdf.PdfReader, password: str) -> BytesIO:
    """Unlocks a verified encrypted PDF object and exports its decrypted bytes."""
    if not password:
        raise DecryptionError("Password required for encrypted statement.")

    decryption_status = reader.decrypt(password)
    if decryption_status == 0:
        raise DecryptionError("Invalid 6-digit statement password provided.")

    decrypted_buffer = BytesIO()
    writer = pypdf.PdfWriter(clone_from=reader)
    writer.write(decrypted_buffer)
    decrypted_buffer.seek(0)

    return decrypted_buffer


def _extract_document_text_corpus(decrypted_stream: BytesIO) -> str:
    """Combines metadata catalogs and page 1 content strings into a unified 
    search corpus."""
    decrypted_stream.seek(0)
    reader = pypdf.PdfReader(decrypted_stream)

    metadata_string = str(reader.metadata) if reader.metadata else ""
    first_page_text = reader.pages[0].extract_text() or ""

    return f"{metadata_string}\n{first_page_text}"


def _validate_mpesa_branding_signature(corpus: str) -> None:
    """Fails fast if the text corpus lacks standard M-Pesa tracking nomenclature."""
    if "M-PESA" not in corpus.upper():
        raise StructuralAttestationError(
            "Invalid document layout: Not an authentic M-Pesa statement-1."
        )


def _extract_verification_token(corpus: str) -> str:
    """Uses text search constraints to isolate the 8-digit verification code."""
    print("="*80)
    #print("corpus received :")
    #print(repr(corpus))
    idx = corpus.lower().find("enter the code")
    print("Next 300 chars:")
    print (idx)
    print(repr(corpus[idx:idx+300]))
    print('-'*80)
    print("Every 8-char candidate:")
    for m in re.finditer(r"\b[A-Z0-9]{8}\b", corpus):  
       print(m.group(), m.span())

    print('-'*80)
    print(repr(corpus[-500:]))
    print("="*80)

    token_pattern = r"enter\s+the\s+code\.?\s*([A-Z0-9]{8})"
    match = re.search(token_pattern, corpus, re.IGNORECASE)

    print("Match :",match)

    
    if not match:
         raise StructuralAttestationError(
             "Invalid document layout: Not an authentic M-Pesa statement-2."
         )

    return match.group(1)
