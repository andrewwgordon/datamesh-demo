from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
OPENAPI_DIR = ROOT / "contracts" / "openapi"


def _load_yaml(path: Path):
    try:
        import yaml
    except Exception as exc:  # pragma: no cover
        pytest.fail(f"PyYAML is required: {exc}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_b3_openapi_files_present_and_parseable():
    for path in [OPENAPI_DIR / "openapi-data.yaml", OPENAPI_DIR / "openapi-control.yaml"]:
        doc = _load_yaml(path)
        assert doc["openapi"].startswith("3.")
        assert "paths" in doc and isinstance(doc["paths"], dict)


def test_b3_openapi_required_paths_exist():
    data_doc = _load_yaml(OPENAPI_DIR / "openapi-data.yaml")
    control_doc = _load_yaml(OPENAPI_DIR / "openapi-control.yaml")

    assert "/api/v1/assets/{assetId}" in data_doc["paths"]
    assert "/api/v1/work-orders/{workOrderId}" in data_doc["paths"]

    assert "/cp/v1" in control_doc["paths"]
    assert "/cp/v1/contract" in control_doc["paths"]
    assert "/cp/v1/interfaces" in control_doc["paths"]
    assert "/cp/v1/subscriptions" in control_doc["paths"]
    assert "/cp/v1/lineage" in control_doc["paths"]
