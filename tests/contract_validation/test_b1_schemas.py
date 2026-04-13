import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "contracts" / "schemas"


def _load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.parametrize(
    "schema_name,sample",
    [
        (
            "cdc.asset.v1.schema.json",
            {
                "eventId": "evt-1",
                "eventTime": "2026-01-01T00:00:00Z",
                "source": "eam",
                "topic": "cdc.eam.asset.v1",
                "table": "asset",
                "op": "u",
                "before": {"asset_id": "A-1", "name": "Pump"},
                "after": {"asset_id": "A-1", "name": "Pump-2"},
            },
        ),
        (
            "cdc.work_order.v1.schema.json",
            {
                "eventId": "evt-2",
                "eventTime": "2026-01-01T00:00:00Z",
                "source": "eam",
                "topic": "cdc.eam.work_order.v1",
                "table": "work_order",
                "op": "u",
                "before": {
                    "work_order_id": "WO-1",
                    "asset_id": "A-1",
                    "title": "Inspect",
                    "status": "OPEN",
                    "deleted": False,
                },
                "after": {
                    "work_order_id": "WO-1",
                    "asset_id": "A-1",
                    "title": "Inspect",
                    "status": "IN_PROGRESS",
                    "deleted": False,
                },
            },
        ),
        (
            "canonical.asset.summary.v1.schema.json",
            {"assetId": "A-1", "name": "Pump", "status": "ACTIVE"},
        ),
        (
            "canonical.workorder.notification.v1.schema.json",
            {
                "eventId": "evt-3",
                "eventTime": "2026-01-01T00:00:00Z",
                "topic": "maintenance.workorder.notification.v1",
                "workOrderId": "WO-1",
                "assetId": "A-1",
                "status": "OPEN",
                "op": "u",
                "href": "/api/v1/work-orders/WO-1",
                "changedFields": ["status"],
            },
        ),
        (
            "canonical.workorder.snapshot.v1.schema.json",
            {
                "eventId": "evt-4",
                "eventTime": "2026-01-01T00:00:00Z",
                "topic": "maintenance.workorder.snapshot.v1",
                "workOrder": {
                    "workOrderId": "WO-1",
                    "assetId": "A-1",
                    "title": "Inspect",
                    "status": "OPEN",
                    "deleted": False,
                    "assetSummary": {"assetId": "A-1", "name": "Pump"},
                },
            },
        ),
    ],
)
def test_b1_json_schemas_validate_examples(schema_name, sample):
    schema = _load_json(SCHEMA_DIR / schema_name)
    Draft202012Validator(schema).validate(sample)
