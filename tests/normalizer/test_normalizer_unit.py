"""
Unit tests for Normalizer service.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import uuid

# Mock the imports before importing the module
with patch('psycopg2.connect'), \
     patch('kafka.KafkaConsumer'), \
     patch('kafka.KafkaProducer'), \
     patch('openlineage.client.OpenLineageClient'):
    from services.normalizer.main import Normalizer


class TestNormalizer:
    """Test Normalizer class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        with patch('psycopg2.connect') as mock_db, \
             patch('kafka.KafkaConsumer') as mock_consumer, \
             patch('kafka.KafkaProducer') as mock_producer, \
             patch('openlineage.client.OpenLineageClient') as mock_ol:
            
            self.mock_db_conn = Mock()
            self.mock_cursor = Mock()
            self.mock_db_conn.cursor.return_value = self.mock_cursor
            mock_db.return_value = self.mock_db_conn
            
            self.mock_consumer = Mock()
            mock_consumer.return_value = self.mock_consumer
            
            self.mock_producer = Mock()
            mock_producer.return_value = self.mock_producer
            
            self.mock_ol_client = Mock()
            mock_ol.return_value = self.mock_ol_client
            
            self.normalizer = Normalizer()
    
    def test_update_asset_state(self):
        """Test updating asset state."""
        asset_data = {
            'asset_id': 'A-10001',
            'name': 'Test Asset',
            'type': 'Motor',
            'location': 'Plant A',
            'status': 'OPERATIONAL'
        }
        
        self.normalizer._update_asset_state(asset_data)
        
        assert 'A-10001' in self.normalizer.asset_state
        assert self.normalizer.asset_state['A-10001'] == asset_data
    
    def test_get_asset_summary_from_state(self):
        """Test getting asset summary from in-memory state."""
        asset_data = {
            'asset_id': 'A-10001',
            'name': 'Test Asset',
            'type': 'Motor',
            'location': 'Plant A',
            'status': 'OPERATIONAL'
        }
        
        self.normalizer.asset_state['A-10001'] = asset_data
        
        summary = self.normalizer._get_asset_summary('A-10001')
        
        assert summary is not None
        assert summary['assetId'] == 'A-10001'
        assert summary['name'] == 'Test Asset'
        assert summary['type'] == 'Motor'
        assert summary['location'] == 'Plant A'
        assert summary['status'] == 'OPERATIONAL'
        assert summary['href'] == '/api/v1/assets/A-10001'
    
    def test_get_asset_summary_from_db(self):
        """Test getting asset summary from database fallback."""
        # Clear in-memory state
        self.normalizer.asset_state = {}
        
        # Mock database response
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = (
            'A-10001', 'Test Asset', 'Motor', 'Plant A', 'OPERATIONAL'
        )
        
        # Create a mock context manager using MagicMock
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__.return_value = mock_cursor
        mock_context_manager.__exit__.return_value = None
        
        # Mock the cursor method to return the context manager
        self.mock_db_conn.cursor.return_value = mock_context_manager
        
        summary = self.normalizer._get_asset_summary('A-10001')
        
        assert summary is not None
        assert summary['assetId'] == 'A-10001'
        assert summary['name'] == 'Test Asset'
        assert summary['href'] == '/api/v1/assets/A-10001'
        
        # Verify database query was made
        mock_cursor.execute.assert_called_once_with(
            "SELECT asset_id, name, type, location, status FROM asset WHERE asset_id = %s",
            ('A-10001',)
        )
    
    def test_transform_to_canonical_workorder(self):
        """Test transforming CDC event to canonical workorder."""
        cdc_event = {
            'op': 'c',
            'after': {
                'work_order_id': 'WO-90001',
                'asset_id': 'A-10001',
                'title': 'Repair Motor',
                'description': 'Fix the broken motor',
                'status': 'OPEN',
                'priority': 'HIGH',
                'deleted': False,
                'updated_at': '2024-01-01T10:00:00Z'
            }
        }
        
        # Mock asset summary
        asset_summary = {
            'assetId': 'A-10001',
            'name': 'Test Asset',
            'type': 'Motor',
            'location': 'Plant A',
            'status': 'OPERATIONAL',
            'href': '/api/v1/assets/A-10001'
        }
        
        with patch.object(self.normalizer, '_get_asset_summary', return_value=asset_summary):
            result = self.normalizer._transform_to_canonical_workorder(cdc_event)
            
            assert result is not None
            assert result['workOrderId'] == 'WO-90001'
            assert result['assetId'] == 'A-10001'
            assert result['title'] == 'Repair Motor'
            assert result['description'] == 'Fix the broken motor'
            assert result['status'] == 'OPEN'
            assert result['priority'] == 'HIGH'
            assert result['deleted'] is False
            assert result['updatedAt'] == '2024-01-01T10:00:00Z'
            assert result['assetSummary'] == asset_summary
    
    def test_transform_to_canonical_workorder_delete_op(self):
        """Test transforming delete operation CDC event."""
        cdc_event = {
            'op': 'd',
            'before': {
                'work_order_id': 'WO-90001',
                'asset_id': 'A-10001'
            },
            'after': None
        }
        
        result = self.normalizer._transform_to_canonical_workorder(cdc_event)
        
        assert result is None
    
    def test_publish_notification_event(self):
        """Test publishing notification event."""
        workorder_data = {
            'workOrderId': 'WO-90001',
            'assetId': 'A-10001'
        }
        
        event_id = str(uuid.uuid4())
        event_time = datetime.now().isoformat()
        
        # Mock the producer send method
        with patch.object(self.normalizer.producer, 'send') as mock_send:
            self.normalizer._publish_notification_event(workorder_data, event_id, event_time)
            
            # Verify producer was called
            mock_send.assert_called_once()
            
            call_args = mock_send.call_args
            assert call_args[0][0] == 'maintenance.workorder.notification.v1'
            
            event_value = call_args[1]['value']
            assert event_value['eventId'] == event_id
            assert event_value['eventTime'] == event_time
            assert event_value['topic'] == 'maintenance.workorder.notification.v1'
            assert event_value['workOrderId'] == 'WO-90001'
            assert event_value['assetId'] == 'A-10001'
            assert event_value['href'] == '/api/v1/work-orders/WO-90001'
    
    def test_publish_snapshot_event(self):
        """Test publishing snapshot event."""
        workorder_data = {
            'workOrderId': 'WO-90001',
            'assetId': 'A-10001',
            'title': 'Repair Motor',
            'assetSummary': {
                'assetId': 'A-10001',
                'name': 'Test Asset'
            }
        }
        
        event_id = str(uuid.uuid4())
        event_time = datetime.now().isoformat()
        
        # Mock the producer send method
        with patch.object(self.normalizer.producer, 'send') as mock_send:
            self.normalizer._publish_snapshot_event(workorder_data, event_id, event_time)
            
            # Verify producer was called
            mock_send.assert_called_once()
            
            call_args = mock_send.call_args
            assert call_args[0][0] == 'maintenance.workorder.snapshot.v1'
            
            event_value = call_args[1]['value']
            assert event_value['eventId'] == event_id
            assert event_value['eventTime'] == event_time
            assert event_value['topic'] == 'maintenance.workorder.snapshot.v1'
            assert event_value['workOrder'] == workorder_data
    
    def test_update_canonical_tables_asset(self):
        """Test updating canonical asset table."""
        cdc_event = {
            'table': 'asset',
            'op': 'c',
            'after': {
                'asset_id': 'A-10001',
                'name': 'Test Asset'
            }
        }
        
        # Mock the cursor context manager
        mock_cursor = Mock()
        mock_cursor.execute = Mock()
        
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__.return_value = mock_cursor
        mock_context_manager.__exit__.return_value = None
        
        with patch.object(self.normalizer.db_conn, 'cursor', return_value=mock_context_manager):
            self.normalizer._update_canonical_tables(cdc_event, None)
            
            # Verify database update
            mock_cursor.execute.assert_called_once()
            
            call_args = mock_cursor.execute.call_args
            sql = call_args[0][0]
            params = call_args[0][1]
            
            assert 'canonical_asset' in sql
            assert params[0] == 'A-10001'
            assert json.loads(params[1]) == {'asset_id': 'A-10001', 'name': 'Test Asset'}
    
    def test_update_canonical_tables_work_order(self):
        """Test updating canonical work order table."""
        cdc_event = {
            'table': 'work_order',
            'op': 'c',
            'after': {
                'work_order_id': 'WO-90001'
            }
        }
        
        canonical_data = {
            'workOrderId': 'WO-90001',
            'assetId': 'A-10001',
            'title': 'Repair Motor'
        }
        
        # Mock the cursor context manager
        mock_cursor = Mock()
        mock_cursor.execute = Mock()
        
        mock_context_manager = MagicMock()
        mock_context_manager.__enter__.return_value = mock_cursor
        mock_context_manager.__exit__.return_value = None
        
        with patch.object(self.normalizer.db_conn, 'cursor', return_value=mock_context_manager):
            self.normalizer._update_canonical_tables(cdc_event, canonical_data)
            
            # Verify database update
            mock_cursor.execute.assert_called_once()
            
            call_args = mock_cursor.execute.call_args
            sql = call_args[0][0]
            params = call_args[0][1]
            
            assert 'canonical_work_order' in sql
            assert params[0] == 'WO-90001'
            assert json.loads(params[1]) == canonical_data
    
    def test_process_message_asset_event(self):
        """Test processing asset CDC event."""
        message = Mock()
        message.value = {
            'table': 'asset',
            'op': 'c',
            'after': {
                'asset_id': 'A-10001',
                'name': 'Test Asset'
            },
            'eventId': 'test-event-id',
            'eventTime': '2024-01-01T10:00:00Z'
        }
        message.topic = 'cdc.eam.asset.v1'
        
        with patch.object(self.normalizer, '_update_asset_state') as mock_update_state, \
             patch.object(self.normalizer, '_update_canonical_tables') as mock_update_tables:
            
            self.normalizer.process_message(message)
            
            # Verify asset state was updated
            mock_update_state.assert_called_once_with(message.value['after'])
            
            # Verify canonical tables were updated
            mock_update_tables.assert_called_once_with(message.value, None)
    
    def test_process_message_work_order_event(self):
        """Test processing work order CDC event."""
        message = Mock()
        message.value = {
            'table': 'work_order',
            'op': 'c',
            'after': {
                'work_order_id': 'WO-90001',
                'asset_id': 'A-10001',
                'title': 'Repair Motor'
            },
            'eventId': 'test-event-id',
            'eventTime': '2024-01-01T10:00:00Z'
        }
        message.topic = 'cdc.eam.work_order.v1'
        
        canonical_workorder = {
            'workOrderId': 'WO-90001',
            'assetId': 'A-10001',
            'title': 'Repair Motor'
        }
        
        with patch.object(self.normalizer, '_transform_to_canonical_workorder', 
                         return_value=canonical_workorder) as mock_transform, \
             patch.object(self.normalizer, '_emit_lineage_start') as mock_lineage_start, \
             patch.object(self.normalizer, '_emit_lineage_complete') as mock_lineage_complete, \
             patch.object(self.normalizer, '_publish_notification_event') as mock_publish_notif, \
             patch.object(self.normalizer, '_publish_snapshot_event') as mock_publish_snapshot, \
             patch.object(self.normalizer, '_update_canonical_tables') as mock_update_tables:
            
            self.normalizer.process_message(message)
            
            # Verify transformation was called
            mock_transform.assert_called_once_with(message.value)
            
            # Verify lineage events were emitted
            mock_lineage_start.assert_called_once()
            mock_lineage_complete.assert_called_once()
            
            # Verify business events were published
            mock_publish_notif.assert_called_once()
            mock_publish_snapshot.assert_called_once()
            
            # Verify canonical tables were updated
            mock_update_tables.assert_called_once_with(message.value, canonical_workorder)