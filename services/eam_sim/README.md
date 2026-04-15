# EAM Simulator Service

Minimal REST API to create and update Assets and WorkOrders.

## Running

```bash
pip install -r requirements.txt
python main.py
```

The service runs on port 8001 by default.

## API Endpoints

- `POST /assets` - Create asset
- `GET /assets/{asset_id}` - Get asset
- `PUT /assets/{asset_id}` - Update asset
- `POST /work-orders` - Create work order
- `GET /work-orders/{work_order_id}` - Get work order
- `PUT /work-orders/{work_order_id}` - Update work order
- `GET /health` - Health check
