"""Bound native payload decoding independently of advertised frame sizes."""

import zlib

import pikepdf
import pytest
import zstandard as zstd

from arch_line_weights import apply_saas


def native_pdf(framed, *, flate=False):
    pdf = pikepdf.new()
    page = pdf.add_blank_page()
    stream = pdf.make_stream(framed)
    if flate:
        stream.write(zlib.compress(framed), filter=pikepdf.Name.FlateDecode)
    page.obj["/PieceInfo"] = pikepdf.Dictionary(Illustrator=pikepdf.Dictionary(
        Private=pikepdf.Dictionary(NumBlock=1, AIPrivateData1=stream)))
    return pdf


@pytest.mark.parametrize("declared", [True, False])
def test_alw23_native_frame_limit_applies_with_or_without_declared_size(monkeypatch, declared):
    monkeypatch.setattr(apply_saas, "MAX_NATIVE_DECODED_BYTES", 1024)
    frame = zstd.ZstdCompressor(write_content_size=declared).compress(b"x" * 4096)
    with native_pdf(apply_saas.PREFIX + frame) as pdf, pytest.raises((ValueError, zstd.ZstdError)):
        apply_saas._read_payload(pdf)


def test_alw23_outer_pdf_filter_is_bounded(monkeypatch):
    monkeypatch.setattr(apply_saas, "MAX_NATIVE_COMPRESSED_BYTES", 1024)
    # Fail before decoding a large Flate stream, rather than checking after read_bytes allocates it.
    with native_pdf(b"x" * 4096, flate=True) as pdf:
        stream = pdf.pages[0].obj["/PieceInfo"]["/Illustrator"]["/Private"]["/AIPrivateData1"]
        original = pikepdf.Object.read_bytes

        def forbidden_read_bytes(self, *args, **kwargs):
            if self.objgen == stream.objgen:
                pytest.fail("unbounded outer PDF decoding")
            return original(self, *args, **kwargs)

        monkeypatch.setattr(pikepdf.Object, "read_bytes", forbidden_read_bytes)
        with pytest.raises(ValueError, match="safe limit"):
            apply_saas._read_payload(pdf)


@pytest.mark.parametrize("declared", [True, False])
@pytest.mark.parametrize("flate", [True, False])
def test_alw23_exact_limit_roundtrips(monkeypatch, declared, flate):
    monkeypatch.setattr(apply_saas, "MAX_NATIVE_DECODED_BYTES", 1024)
    frame = zstd.ZstdCompressor(write_content_size=declared).compress(b"x" * 1024)
    with native_pdf(apply_saas.PREFIX + frame, flate=flate) as pdf:
        assert apply_saas._read_payload(pdf) == b"x" * 1024
