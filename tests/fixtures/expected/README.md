# Expected Parser Output (Golden Files)

This directory stores hand-curated golden files used by baseline parser tests.

## File Naming

```
tests/fixtures/expected/<supermarket>.json
```

## Format

Each JSON file is a list of discount objects (subset of fields, minimum required set):

```json
[
  {
    "name_contains": "Mléko",
    "discounted_price": 19.90
  },
  ...
]
```

Fields:
- `name_contains` — substring that must appear in the matched discount's `name` (case-insensitive)
- `discounted_price` — expected discounted price (float, tolerance ±0.01)

## Generating a Draft

Run the helper script to dump raw parser output for a given supermarket:

```bash
python scripts/dump_parser_output.py tesco
```

Then hand-curate the output, keeping only items you can verify against the actual leaflet,
and save it as `tests/fixtures/expected/tesco.json`.
