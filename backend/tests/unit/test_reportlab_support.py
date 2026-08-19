"""Unit tests for app.core.document_engine.reportlab_support.build_logo_flowable
(Sprint 14: Company Profile & Organization Identity) - the shared, pure
image-decoding/scaling mechanism every ReportLab-based document renderer's
_build_header() calls to optionally prepend a tenant logo."""

from reportlab.lib.units import mm
from reportlab.platypus import Image

from app.core.document_engine.reportlab_support import build_logo_flowable

# A minimal real 2x2 PNG (generated via Pillow).
_PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000002000000020802000000fdd4"
    "9a730000001349444154789c6364f8cfc0c0c0c004221818000c1e0103acd8"
    "8ba70000000049454e44ae426082"
)

# A PNG with a genuine signature + IHDR chunk (so ImageReader.getSize()
# succeeds - it only reads the header) but a truncated IDAT stream, so
# a *full* pixel decode fails. This is not a synthetic edge case: an
# earlier version of this exact fixture (hand-typed instead of
# Pillow-generated) shipped in this test suite and passed every existing
# check here, since none of them forced a full decode - the corruption
# was only discovered when the same bytes were written to real storage
# and re-decoded by a completely different test. Regression coverage for
# that failure mode: build_logo_flowable must reject bytes like this at
# construction time, never defer the failure to ReportLab's draw-time
# decode (deep inside doc.build(), outside any of this module's error
# handling).
_HEADER_VALID_BUT_BODY_CORRUPT_PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108020000009077"
    "53de000000017352474200aece1ce90000000467414d410000b18f0bfc6105"
    "0000000970485973000016250000162501495224f00000000a4944415478da"
    "6360000002000155007fa8f4c00000000049454e44ae426082"
)


class TestBuildLogoFlowable:
    def test_returns_none_for_empty_bytes(self) -> None:
        assert build_logo_flowable(None, max_width=28 * mm, max_height=18 * mm) is None
        assert build_logo_flowable(b"", max_width=28 * mm, max_height=18 * mm) is None

    def test_returns_none_for_undecodable_bytes(self) -> None:
        assert (
            build_logo_flowable(b"not-a-real-image", max_width=28 * mm, max_height=18 * mm) is None
        )

    def test_returns_an_image_flowable_for_valid_bytes(self) -> None:
        flowable = build_logo_flowable(_PNG_BYTES, max_width=28 * mm, max_height=18 * mm)
        assert isinstance(flowable, Image)

    def test_scaled_image_fits_within_the_requested_box(self) -> None:
        flowable = build_logo_flowable(_PNG_BYTES, max_width=28 * mm, max_height=18 * mm)
        assert isinstance(flowable, Image)
        assert flowable.drawWidth <= 28 * mm
        assert flowable.drawHeight <= 18 * mm

    def test_never_upscales_a_smaller_image_beyond_its_natural_size(self) -> None:
        # The source is a 2x2 pixel PNG - far smaller than any sane
        # max_width/max_height - scaling must clamp at 1.0, never stretch
        # a tiny image up to fill the box.
        flowable = build_logo_flowable(_PNG_BYTES, max_width=1000, max_height=1000)
        assert isinstance(flowable, Image)
        assert flowable.drawWidth == 2
        assert flowable.drawHeight == 2

    def test_returns_none_for_a_header_valid_but_body_corrupt_image(self) -> None:
        """Regression guard: getSize() alone (header-only) is not enough
        to prove an image is renderable - this fixture passes that check
        but fails a full pixel decode. Must return None here, not a
        flowable that only fails later at ReportLab's own draw time."""
        flowable = build_logo_flowable(
            _HEADER_VALID_BUT_BODY_CORRUPT_PNG_BYTES, max_width=28 * mm, max_height=18 * mm
        )
        assert flowable is None
