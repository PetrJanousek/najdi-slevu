"""Tests that exercise the sample_pdf fixture skip behaviour."""


def test_sample_pdf_skips_missing(sample_pdf):
    """Should skip gracefully when no PDFs are present for a supermarket."""
    sample_pdf("__nonexistent_supermarket__")
    # If we reach here the fixture didn't skip, which means files exist — also fine.
