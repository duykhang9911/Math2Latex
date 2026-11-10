import pytest

from app.services.upload_validation import sanitize_filename


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("bai1.pdf", "bai1.pdf"),
        ("de thi 2025.pdf", "de thi 2025.pdf"),
        ("C:\\Users\\a\\bai1.pdf", "bai1.pdf"),
        ("../../etc/passwd.pdf", "passwd.pdf"),
        ("/abs/path/bai1.pdf", "bai1.pdf"),
        ("bai\r\n1.pdf", "bai1.pdf"),
        ("  bai1.pdf  ", "bai1.pdf"),
        ("bai1.pdf. .", "bai1.pdf"),
        ("", ""),
        ("../", ""),
    ],
)
def test_sanitize_filename(raw, expected):
    assert sanitize_filename(raw) == expected


def test_sanitize_filename_truncates_the_stem_and_keeps_the_extension():
    name = sanitize_filename("a" * 500 + ".pdf")

    assert len(name) == 255
    assert name.endswith(".pdf")
