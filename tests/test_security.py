import pytest
from io import BytesIO
import pypdf  
from src.security import (
    verify_pdf_magic_bytes,
    decrypt_pdf_in_memory,
    attest_mpesa_structure,
    DecryptionError,
    StructuralAttestationError
)


# 1. DEEP BYTE AUDIT TESTS (MAGIC NUMBERS)

def test_verify_pdf_magic_bytes_accepts_valid_header():
    """Passes valid %PDF binary headers to ensure the surface checkpoint holds."""
    valid_pdf_stream = BytesIO(b"%PDF-1.4\n1 0 obj...")
    # Should run and exit cleanly without raising an exception
    verify_pdf_magic_bytes(valid_pdf_stream)

def test_verify_pdf_magic_bytes_rejects_spoofed_files():
    """Ensures a renamed malicious file (e.g. script.txt to script.pdf) is caught."""
    spoofed_stream = BytesIO(b"import os\nos.system('malware')")
    with pytest.raises(ValueError, match="Invalid file signature: Not a valid PDF document"):
        verify_pdf_magic_bytes(spoofed_stream)



# 2. ENCRYPTION BOUNDARY TESTS (RAM DECRYPTION CHECKPOINTS)

def test_decrypt_pdf_in_memory_passes_unencrypted_corporate_portal_files():
    """Verifies that unencrypted server-to-server portal files pass straight through."""
    unencrypted_stream = _create_mock_pdf_bytes(encrypted=False)
    
    # Should return the exact same stream untouched, requiring no password input
    result_stream = decrypt_pdf_in_memory(unencrypted_stream, password=None)
    assert result_stream == unencrypted_stream

def test_decrypt_pdf_in_memory_fails_on_missing_password_for_locked_files():
    """Ensures personal encrypted statements demand a passphrase gate."""
    encrypted_stream = _create_mock_pdf_bytes(encrypted=True, correct_password="123456")
    
    with pytest.raises(DecryptionError, match="Password required for encrypted statement"):
        decrypt_pdf_in_memory(encrypted_stream, password=None)

def test_decrypt_pdf_in_memory_catches_incorrect_passwords():
    """Asserts that wrong identification numbers trigger a clean boundary failure."""
    encrypted_stream = _create_mock_pdf_bytes(encrypted=True, correct_password="123456")
    
    with pytest.raises(DecryptionError, match="Invalid 6-digit statement password provided"):
        decrypt_pdf_in_memory(encrypted_stream, password="wrong_pass")



# 3. CONTENT DIGITAL DNA ATTESTATION TESTS (M-PESA SIGNATURES)

def test_attest_mpesa_structure_rejects_generic_pdf_books():
    """Ensures valid, unencrypted PDFs (like text books or resumes) are rejected instantly."""
    # Valid PDF structure but completely wrong page text contents
    generic_pdf = _create_mock_pdf_bytes(encrypted=False, text_content="Chapter 1: The History of Kenya")
    
    with pytest.raises(StructuralAttestationError, match="Invalid document layout: Not an authentic M-Pesa statement"):
        attest_mpesa_structure(generic_pdf)

def test_attest_mpesa_structure_extracts_verification_token():
    """Validates that authentic statements pass checkpoints and yield token keys."""
    authentic_text = (
        "Safaricom M-PESA Statement\n"
        "To verify the validity of this M-PESA statement dial *334#, "
        "select My account and follow the prompts to enter the code. JRZ3TLGT"
    )
    authentic_pdf = _create_mock_pdf_bytes(encrypted=False, text_content=authentic_text)
    
    token = attest_mpesa_structure(authentic_pdf)
    assert token == "JRZ3TLGT"



# MOCK BINARY GENERATION HELPERS (Prevents local disk dependency)
def _create_mock_pdf_bytes(encrypted: bool, correct_password: str = None, text_content: str = "") -> BytesIO:
    """Helper to dynamically generate in-memory valid PDF layout byte signatures."""
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=200, height=200)
    
    # In a real environment, pypdf writes metadata or content layers.
    # For testing, we ensure metadata hooks align with text contents if provided
    if text_content:
        writer.add_metadata({"/Comment": text_content})
        
    if encrypted and correct_password:
        writer.encrypt(correct_password)
        
    stream = BytesIO()
    writer.write(stream)
    stream.seek(0)
    return stream