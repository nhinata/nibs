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
    ],
    ids=["header wins", "quoted header", "meta charset", "meta http-equiv", "none", "past 1,024 bytes"],
)
def test_the_charset_comes_from_the_header_then_a_meta_tag_then_utf8(ctype, body, expected):
    assert page.encoding(ctype, body) == expected


def test_a_shift_jis_page_declared_in_meta_reads_as_text():
    text = page.html_to_text(SJIS_PAGE.decode(page.encoding("text/html", SJIS_PAGE)))
    assert text == "# 見出し"
