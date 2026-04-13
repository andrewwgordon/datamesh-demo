from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_FILE = ROOT / "contracts" / "contract" / "product.contract.yaml"
BOOTSTRAP_SCRIPT = ROOT / "platform" / "bootstrap" / "01_register_artifacts.sh"


def _load_yaml(path: Path):
    try:
        import yaml
    except Exception as exc:  # pragma: no cover
        pytest.fail(f"PyYAML is required: {exc}")
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_b4_product_contract_parseable_and_complete():
    doc = _load_yaml(CONTRACT_FILE)
    assert doc["kind"] == "DataProductContract"
    assert "interfaces" in doc["spec"]
    assert "schemas" in doc["spec"]
    assert "topics" in doc["spec"]


def test_b4_registry_bootstrap_sets_validity_rule():
    content = BOOTSTRAP_SCRIPT.read_text(encoding="utf-8")
    assert "/admin/rules/VALIDITY" in content
    assert "\"config\":\"FULL\"" in content
