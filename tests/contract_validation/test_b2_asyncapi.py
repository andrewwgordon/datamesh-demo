from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ASYNCAPI_DIR = ROOT / "contracts" / "asyncapi"


def _load_yaml(path: Path):
    try:
        import yaml
    except Exception as exc:  # pragma: no cover
        pytest.fail(f"PyYAML is required: {exc}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_b2_asyncapi_files_present_and_parseable():
    for path in [ASYNCAPI_DIR / "asyncapi-cdc.yaml", ASYNCAPI_DIR / "asyncapi-business.yaml"]:
        doc = _load_yaml(path)
        assert doc["asyncapi"].startswith("2.")
        assert "channels" in doc and isinstance(doc["channels"], dict)


def test_b2_asyncapi_topics_exist():
    cdc_doc = _load_yaml(ASYNCAPI_DIR / "asyncapi-cdc.yaml")
    business_doc = _load_yaml(ASYNCAPI_DIR / "asyncapi-business.yaml")

    assert "cdc.eam.asset.v1" in cdc_doc["channels"]
    assert "cdc.eam.work_order.v1" in cdc_doc["channels"]
    assert "maintenance.workorder.notification.v1" in business_doc["channels"]
    assert "maintenance.workorder.snapshot.v1" in business_doc["channels"]
