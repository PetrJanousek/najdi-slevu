"""Shared pytest fixtures."""
import pytest
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "leaflets"


@pytest.fixture
def sample_pdf(request):
    """Return the path to a sample leaflet PDF for the given supermarket.

    Usage::

        def test_something(sample_pdf):
            pdf_path = sample_pdf("tesco")
            # ...

    If no PDF exists for the requested supermarket the test is skipped.
    """
    def _get(supermarket: str) -> Path:
        leaflet_dir = FIXTURES_DIR / supermarket
        if not leaflet_dir.is_dir():
            pytest.skip(f"No fixture directory for supermarket '{supermarket}'")
        pdfs = sorted(leaflet_dir.glob("*.pdf"))
        if not pdfs:
            pytest.skip(
                f"No PDF fixtures found in {leaflet_dir}. "
                "Add a leaflet following the naming convention in tests/fixtures/leaflets/README.md"
            )
        return pdfs[0]

    return _get
