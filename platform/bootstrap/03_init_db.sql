BEGIN;

CREATE TABLE IF NOT EXISTS asset (
	asset_id TEXT PRIMARY KEY,
	name TEXT NOT NULL,
	type TEXT,
	location TEXT,
	status TEXT,
	updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS work_order (
	work_order_id TEXT PRIMARY KEY,
	asset_id TEXT NOT NULL REFERENCES asset(asset_id),
	title TEXT NOT NULL,
	description TEXT,
	status TEXT NOT NULL,
	priority TEXT,
	deleted BOOLEAN NOT NULL DEFAULT FALSE,
	updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS cdc_log (
	id BIGSERIAL PRIMARY KEY,
	table_name TEXT NOT NULL,
	operation CHAR(1) NOT NULL,
	before_data JSONB,
	after_data JSONB,
	created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
	published_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS canonical_asset (
	asset_id TEXT PRIMARY KEY,
	payload JSONB NOT NULL,
	updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS canonical_work_order (
	work_order_id TEXT PRIMARY KEY,
	payload JSONB NOT NULL,
	updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cdc_log_unpublished ON cdc_log (id) WHERE published_at IS NULL;

CREATE OR REPLACE FUNCTION fn_set_updated_at() RETURNS TRIGGER AS $$
BEGIN
	NEW.updated_at = NOW();
	RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_asset_set_updated_at ON asset;
CREATE TRIGGER trg_asset_set_updated_at
BEFORE UPDATE ON asset
FOR EACH ROW
EXECUTE FUNCTION fn_set_updated_at();

DROP TRIGGER IF EXISTS trg_work_order_set_updated_at ON work_order;
CREATE TRIGGER trg_work_order_set_updated_at
BEFORE UPDATE ON work_order
FOR EACH ROW
EXECUTE FUNCTION fn_set_updated_at();

CREATE OR REPLACE FUNCTION fn_write_cdc_log() RETURNS TRIGGER AS $$
BEGIN
	IF TG_OP = 'INSERT' THEN
		INSERT INTO cdc_log (table_name, operation, before_data, after_data)
		VALUES (TG_TABLE_NAME, 'c', NULL, to_jsonb(NEW));
		RETURN NEW;
	ELSIF TG_OP = 'UPDATE' THEN
		INSERT INTO cdc_log (table_name, operation, before_data, after_data)
		VALUES (TG_TABLE_NAME, 'u', to_jsonb(OLD), to_jsonb(NEW));
		RETURN NEW;
	ELSIF TG_OP = 'DELETE' THEN
		INSERT INTO cdc_log (table_name, operation, before_data, after_data)
		VALUES (TG_TABLE_NAME, 'd', to_jsonb(OLD), NULL);
		RETURN OLD;
	END IF;
	RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_asset_cdc ON asset;
CREATE TRIGGER trg_asset_cdc
AFTER INSERT OR UPDATE OR DELETE ON asset
FOR EACH ROW
EXECUTE FUNCTION fn_write_cdc_log();

DROP TRIGGER IF EXISTS trg_work_order_cdc ON work_order;
CREATE TRIGGER trg_work_order_cdc
AFTER INSERT OR UPDATE OR DELETE ON work_order
FOR EACH ROW
EXECUTE FUNCTION fn_write_cdc_log();

COMMIT;
