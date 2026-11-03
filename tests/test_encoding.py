import pytest

from nibs import page

SJIS_PAGE = '<html><head><meta charset="Shift_JIS"></head><body><h1>見出し</h1></body></html>'.encode("shift_jis")


@pytest.mark.parametrize(
    "ctype, body, expected",
    [
        ("text/html; charset=EUC-JP", b"<meta charset='Shift_JIS'>", "EUC-JP"),
        ('text/html; charset="utf-8"', b"", "utf-8"),
        ("text/html", SJIS_PAGE, "Shift_JIS"),
        ("text/html", b'<meta http-equiv="Content-Type" content="text/html; charset=euc-jp">', "euc-jp"),
        ("text/html", b"<html><body>no declaration</body></html>", "utf-8"),
        ("text/html", b" " * 1024 + b'<meta charset="Shift_JIS">', "utf-8"),
        ("", b'<!DOCTYPE html><meta charset="Shift_JIS">', "Shift_JIS"),
        ("text/markdown", b'# HTML basics\n\n```html\n<meta charset="Shift_JIS">\n```\n', "utf-8"),
    ],
    ids=["header wins", "quoted header", "meta charset", "meta http-equiv", "none", "past 1,024 bytes",
         "HTML without a content type", "Markdown showing a meta tag"],
)
def test_the_charset_comes_from_the_header_then_a_meta_tag_then_utf8(ctype, body, expected):
    assert page.encoding(ctype, body) == expected


def test_a_shift_jis_page_declared_in_meta_reads_as_text():
    text = page.html_to_text(page.decode("text/html", SJIS_PAGE))
    assert text == "# 見出し"


def test_a_charset_that_cannot_decode_text_falls_back_to_utf8():
    body = '<html><meta charset="idna"><h1>見出し</h1></html>'.encode()
    assert "見出し" in page.decode("text/html", body)
