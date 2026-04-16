"""
Normalizer Service
Consumes CDC topics, maintains state, transforms to canonical business events,
publishes to business topics, updates canonical tables, and emits OpenLineage events.
"""

import json
import os
import logging
import time
from typing import Dict, Optional, Any
from datetime import datetime
import uuid

from kafka import KafkaConsumer, KafkaProducer
import psycopg2
from openlineage.client import OpenLineageClient
from openlineage.client.run import RunEvent, RunState, Run, Job, Dataset

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
CDC_ASSET_TOPIC = os.getenv("CDC_ASSET_TOPIC", "cdc.eam.asset.v1")
CDC_WORK_ORDER_TOPIC = os.getenv("CDC_WORK_ORDER_TOPIC", "cdc.eam.work_order.v1")
NOTIFICATION_TOPIC = os.getenv("NOTIFICATION_TOPIC", "maintenance.workorder.notification.v1")
SNAPSHOT_TOPIC = os.getenv("SNAPSHOT_TOPIC", "maintenance.workorder.snapshot.v1")

DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "eam")
DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")

OPENLINEAGE_URL = os.getenv("OPENLINEAGE_URL", "http://localhost:5000")
OPENLINEAGE_NAMESPACE = os.getenv("OPENLINEAGE_NAMESPACE", "eam-maintenance")
OPENLINEAGE_JOB_NAME = os.getenv("OPENLINEAGE_JOB_NAME", "eam-cdc-to-canonical")

class Normalizer:
    def __init__(self):
        """Initialize Normalizer with Kafka consumers/producers, DB connection, and OpenLineage client."""
        self.asset_state: Dict[str, Dict] = {}
        
        # Initialize Kafka consumers
        self.consumer = KafkaConsumer(
            CDC_ASSET_TOPIC,
            CDC_WORK_ORDER_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            group_id="normalizer-group",
            value_deserializer=lambda v: json.loads(v.decode('utf-8')),
            auto_offset_reset='earliest',
            enable_auto_commit=True
        )
        
        # Initialize Kafka producer
        self.producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        
        # Initialize DB connection
        self.db_conn = self._get_db_connection()
        
        # Initialize OpenLineage client
        self.ol_client = OpenLineageClient(OPENLINEAGE_URL)
        
        logger.info("Normalizer initialized")
    
    def _get_db_connection(self):
        """Get database connection."""
        return psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
    
    def _emit_lineage_start(self, run_id: str, inputs: list, outputs: list):
        """Emit OpenLineage START event."""
        event = RunEvent(
            eventType=RunState.START,
            eventTime=datetime.now().isoformat(),
            run=Run(runId=run_id),
            job=Job(namespace=OPENLINEAGE_NAMESPACE, name=OPENLINEAGE_JOB_NAME),
            inputs=inputs,
            outputs=outputs,
            producer="datamesh-demo/normalizer"
        )
        self.ol_client.emit(event)
        logger.debug(f"Emitted OpenLineage START event for run {run_id}")
    
    def _emit_lineage_complete(self, run_id: str, inputs: list, outputs: list):
        """Emit OpenLineage COMPLETE event."""
        event = RunEvent(
            eventType=RunState.COMPLETE,
            eventTime=datetime.now().isoformat(),
            run=Run(runId=run_id),
            job=Job(namespace=OPENLINEAGE_NAMESPACE, name=OPENLINEAGE_JOB_NAME),
            inputs=inputs,
            outputs=outputs,
            producer="datamesh-demo/normalizer"
        )
        self.ol_client.emit(event)
        logger.debug(f"Emitted OpenLineage COMPLETE event for run {run_id}")
    
    def _update_asset_state(self, asset_data: Dict):
        """Update in-memory asset state from CDC events."""
        if asset_data and 'asset_id' in asset_data:
            self.asset_state[asset_data['asset_id']] = asset_data
            logger.debug(f"Updated asset state for {asset_data['asset_id']}")
    
    def _get_asset_summary(self, asset_id: str) -> Optional[Dict]:
        """Get asset summary from state or database."""
        # First check in-memory state
        if asset_id in self.asset_state:
            asset = self.asset_state[asset_id]
            return {
                "assetId": asset.get('asset_id'),
                "name": asset.get('name'),
                "type": asset.get('type'),
                "location": asset.get('location'),
                "status": asset.get('status'),
                "href": f"/api/v1/assets/{asset_id}"
            }
        
        # Fallback to database
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute(
                    "SELECT asset_id, name, type, location, status FROM asset WHERE asset_id = %s",
                    (asset_id,)
                )
                row = cursor.fetchone()
                if row:
                    return {
                        "assetId": row[0],
                        "name": row[1],
                        "type": row[2],
                        "location": row[3],
                        "status": row[4],
                        "href": f"/api/v1/assets/{asset_id}"
                    }
        except Exception as e:
            logger.error(f"Error fetching asset from DB: {e}")
        
        return None
    
    def _transform_to_canonical_workorder(self, cdc_event: Dict) -> Optional[Dict]:
        """Transform CDC work_order event to canonical workorder."""
        try:
            op = cdc_event.get('op')
            after = cdc_event.get('after')
            
            if not after:
                # For delete operations or missing after data
                return None
            
            asset_id = after.get('asset_id')
            asset_summary = self._get_asset_summary(asset_id) if asset_id else None
            
            canonical = {
                "workOrderId": after.get('work_order_id'),
                "assetId": asset_id,
                "title": after.get('title'),
                "description": after.get('description'),
                "status": after.get('status'),
                "priority": after.get('priority'),
                "deleted": after.get('deleted', False),
                "updatedAt": after.get('updated_at'),
                "assetSummary": asset_summary
            }
            
            return canonical
        except Exception as e:
            logger.error(f"Error transforming to canonical workorder: {e}")
            return None
    
    def _publish_notification_event(self, workorder_data: Dict, event_id: str, event_time: str):
        """Publish notification event (thin event with href)."""
        notification_event = {
            "eventId": event_id,
            "eventTime": event_time,
            "topic": NOTIFICATION_TOPIC,
            "workOrderId": workorder_data.get('workOrderId'),
            "assetId": workorder_data.get('assetId'),
            "href": f"/api/v1/work-orders/{workorder_data.get('workOrderId')}"
        }
        
        self.producer.send(NOTIFICATION_TOPIC, value=notification_event)
        logger.info(f"Published notification event for work order {workorder_data.get('workOrderId')}")
    
    def _publish_snapshot_event(self, workorder_data: Dict, event_id: str, event_time: str):
        """Publish snapshot event (fat event with embedded asset summary)."""
        snapshot_event = {
            "eventId": event_id,
            "eventTime": event_time,
            "topic": SNAPSHOT_TOPIC,
            "workOrder": workorder_data
        }
        
        self.producer.send(SNAPSHOT_TOPIC, value=snapshot_event)
        logger.info(f"Published snapshot event for work order {workorder_data.get('workOrderId')}")
    
    def _update_canonical_tables(self, cdc_event: Dict, canonical_data: Dict):
        """Update canonical tables in database."""
        try:
            table = cdc_event.get('table')
            op = cdc_event.get('op')
            
            with self.db_conn.cursor() as cursor:
                if table == 'asset':
                    asset_id = canonical_data.get('assetId') if canonical_data else cdc_event.get('after', {}).get('asset_id')
                    if asset_id:
                        cursor.execute(
                            """
                            INSERT INTO canonical_asset (asset_id, payload, updated_at)
                            VALUES (%s, %s, NOW())
                            ON CONFLICT (asset_id) DO UPDATE SET
                                payload = EXCLUDED.payload,
                                updated_at = NOW()
                            """,
                            (asset_id, json.dumps(canonical_data or cdc_event.get('after', {})))
                        )
                        logger.debug(f"Updated canonical_asset for {asset_id}")
                
                elif table == 'work_order':
                    work_order_id = canonical_data.get('workOrderId') if canonical_data else cdc_event.get('after', {}).get('work_order_id')
                    if work_order_id:
                        cursor.execute(
                            """
                            INSERT INTO canonical_work_order (work_order_id, payload, updated_at)
                            VALUES (%s, %s, NOW())
                            ON CONFLICT (work_order_id) DO UPDATE SET
                                payload = EXCLUDED.payload,
                                updated_at = NOW()
                            """,
                            (work_order_id, json.dumps(canonical_data or {}))
                        )
                        logger.debug(f"Updated canonical_work_order for {work_order_id}")
            
            self.db_conn.commit()
        except Exception as e:
            logger.error(f"Error updating canonical tables: {e}")
            self.db_conn.rollback()
    
    def process_message(self, message):
        """Process a single Kafka message."""
        try:
            cdc_event = message.value
            topic = message.topic
            table = cdc_event.get('table')
            op = cdc_event.get('operation')
            event_id = cdc_event.get('eventId', str(uuid.uuid4()))
            event_time = cdc_event.get('eventTime', datetime.now().isoformat())
            
            logger.info(f"Received {cdc_event} from topic {topic} with event ID {event_id}")
            
            # Generate lineage run ID
            run_id = str(uuid.uuid4())
            
            # Define lineage inputs/outputs
            inputs = [Dataset(namespace="kafka", name=topic)]
            outputs = []
            
            if table == 'asset':
                self._emit_lineage_start(run_id, inputs, [])
                # Update asset state
                self._update_asset_state(cdc_event.get('after'))
                
                # Update canonical tables
                self._update_canonical_tables(cdc_event, None)
                
                # Assets don't generate business events, only update state
                outputs.append(Dataset(namespace="postgres", name="canonical_asset"))
            
            elif table == 'work_order':
                # Transform to canonical workorder
                canonical_workorder = self._transform_to_canonical_workorder(cdc_event)
                
                if canonical_workorder:
                    # Emit lineage START
                    self._emit_lineage_start(run_id, inputs, [])
                    
                    # Publish business events
                    self._publish_notification_event(canonical_workorder, event_id, event_time)
                    self._publish_snapshot_event(canonical_workorder, event_id, event_time)
                    
                    # Update canonical tables
                    self._update_canonical_tables(cdc_event, canonical_workorder)
                    
                    # Emit lineage COMPLETE
                    outputs.extend([
                        Dataset(namespace="kafka", name=NOTIFICATION_TOPIC),
                        Dataset(namespace="kafka", name=SNAPSHOT_TOPIC),
                        Dataset(namespace="postgres", name="canonical_work_order")
                    ])
            
            self._emit_lineage_complete(run_id, inputs, outputs)            
            logger.info(f"Successfully processed {op} operation on {table}")
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def run(self):
        """Main loop to consume and process messages."""
        logger.info("Starting Normalizer...")
        
        try:
            for message in self.consumer:
                self.process_message(message)
        except KeyboardInterrupt:
            logger.info("Shutting down Normalizer...")
        finally:
            self.consumer.close()
            self.producer.close()
            self.db_conn.close()
            logger.info("Normalizer stopped")

if __name__ == "__main__":
    normalizer = Normalizer()
    normalizer.run()