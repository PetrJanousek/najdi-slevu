# Leaflet PDF Fixtures

Sample supermarket leaflet PDFs used for parser tests.

## Naming Convention

```
tests/fixtures/leaflets/<supermarket>/<yyyy-mm-dd>.pdf
```

- `<supermarket>` — lowercase supermarket name, e.g. `tesco`, `albert`, `lidl`, `kaufland`
- `<yyyy-mm-dd>` — leaflet validity start date (ISO 8601)

### Examples

```
tests/fixtures/leaflets/tesco/2026-04-07.pdf
tests/fixtures/leaflets/albert/2026-04-01.pdf
tests/fixtures/leaflets/lidl/2026-03-31.pdf
```

## Copyright Notice

Supermarket leaflet PDFs are copyrighted materials and are **not committed to this
repository**. They are listed in `.gitignore`. Place downloaded PDFs following the
naming convention above; tests that require them will be skipped automatically when
the files are absent.
