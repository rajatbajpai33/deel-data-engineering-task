import logging
import time
import psycopg2
import os
import fcntl

from psycopg2.extras import LogicalReplicationConnection, RealDictCursor
from psycopg2 import sql, errors
import json
from datetime import datetime

class CDCHandler:
    MAX_RETRIES = 5
    RETRY_DELAY = 5
    MATERIALIZED_VIEWS = [
        'open_orders_by_date_status',
        'top3_delivery_dates',
        'pending_items_by_product',
        'top3_customers_pending_orders'
    ]

    def __init__(self, source_db, target_db):
        self.source_db = source_db
        self.target_db = target_db
        self.logger = logging.getLogger(__name__)
        self.last_refresh = datetime.now()
        self.processed_count = 0
        self.error_count = 0
        self.lock_file = '/tmp/cdc_handler.lock'
        self.lock_fd = None

    def _verify_publication(self, cursor):
        """Verify that the publication exists"""
        query = sql.SQL("SELECT 1 FROM pg_publication WHERE pubname = {}").format(
            sql.Literal('cdc_publication')
        )
        cursor.execute(query)
        if not cursor.fetchone():
            raise Exception("Publication 'cdc_publication' does not exist")

    def _acquire_lock(self):
        """Acquire an exclusive lock to prevent multiple instances"""
        try:
            self.lock_fd = open(self.lock_file, 'w')
            fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.logger.info("Acquired exclusive lock for CDC processing")
            return True
        except (IOError, BlockingIOError):
            self.logger.error("Another CDC process is already running")
            return False

    def _release_lock(self):
        """Release the exclusive lock"""
        if self.lock_fd:
            try:
                fcntl.flock(self.lock_fd, fcntl.LOCK_UN)
                self.lock_fd.close()
                os.remove(self.lock_file)
                self.logger.info("Released exclusive lock")
            except Exception as e:
                self.logger.warning(f"Error releasing lock: {str(e)}")

    def _force_cleanup_slot(self, cursor):
        """Forcefully clean up the replication slot"""
        try:
            cursor.execute("""
                SELECT slot_name, active_pid 
                FROM pg_replication_slots 
                WHERE slot_name = %s
            """, ('cdc_pgoutput2',))
            slot_info = cursor.fetchone()
            
            if slot_info:
                slot_name, active_pid = slot_info
                self.logger.warning(f"Forcibly cleaning up replication slot '{slot_name}'")
                
                if active_pid:
                    max_attempts = 3
                    for attempt in range(max_attempts):
                        try:
                            cursor.execute("SELECT pg_terminate_backend(%s)", (active_pid,))
                            self.logger.info(f"Terminated process {active_pid}")
                            time.sleep(1)
                            break
                        except Exception as e:
                            if attempt == max_attempts - 1:
                                raise
                            self.logger.warning(f"Failed to terminate process {active_pid}, retrying...")
                            time.sleep(1)
                
                max_attempts = 3
                for attempt in range(max_attempts):
                    try:
                        cursor.execute("SELECT pg_drop_replication_slot(%s)", (slot_name,))
                        self.logger.info(f"Successfully dropped replication slot '{slot_name}'")
                        break
                    except Exception as e:
                        if attempt == max_attempts - 1:
                            raise
                        self.logger.warning(f"Failed to drop slot '{slot_name}', retrying...")
                        time.sleep(1)
                        
        except Exception as e:
            self.logger.error(f"Error during forced slot cleanup: {str(e)}")
            raise

    def process_changes(self):
        """Process changes from the source database"""
        if not self._acquire_lock():
            raise Exception("Could not acquire lock - another CDC process may be running")

        conn = None
        cursor = None
        retry_count = 0

        while retry_count < self.MAX_RETRIES:
            try:
                conn = self.source_db
                if conn.closed:
                    conn = psycopg2.connect(
                        connection_factory=LogicalReplicationConnection,
                        **self.source_db.get_dsn_parameters(),
                        connect_timeout=5,
                        client_encoding='LATIN1'
                    )

                cursor = conn.cursor()
                self._verify_publication(cursor)
                self._force_cleanup_slot(cursor)

                cursor.execute("""
                    SELECT active_pid 
                    FROM pg_replication_slots 
                    WHERE slot_name = %s AND active
                """, ('cdc_pgoutput2',))
                active_slot = cursor.fetchone()
                
                if active_slot:
                    self.logger.error(f"Replication slot 'cdc_pgoutput2' is still active for PID {active_slot[0]}")
                    raise Exception("Failed to clean up active replication slot")

                cursor.start_replication(
                    slot_name='cdc_pgoutput2',
                    decode=False,
                    status_interval=10,
                    options={
                        'proto_version': '1',
                        'publication_names': 'cdc_publication'
                    }
                )

                self.logger.info("Listening for changes...")
                cursor.consume_stream(self._process_replication_message)
                return
                
            except psycopg2.OperationalError as e:
                retry_count += 1
                if retry_count >= self.MAX_RETRIES:
                    self.logger.error(f"Database connection error after {retry_count} attempts: {str(e)}")
                    raise Exception(f"Failed to connect to database after {retry_count} attempts: {str(e)}")
                self.logger.warning(f"Database connection error, retrying in {self.RETRY_DELAY} seconds...")
                time.sleep(self.RETRY_DELAY)
                
            except Exception as e:
                self.logger.error(f"Error in CDC processing: {str(e)}")
                raise
            finally:
                try:
                    if cursor:
                        try:
                            self._force_cleanup_slot(cursor)
                        except Exception as e:
                            self.logger.error(f"Error during final slot cleanup: {str(e)}")
                        cursor.close()
                    if conn:
                        conn.close()
                    self._release_lock()
                except Exception as e:
                    self.logger.warning(f"Error closing connection: {str(e)}")

    def _parse_payload(self, payload):
        """Parse PostgreSQL logical replication message"""
        try:
            if isinstance(payload, bytes):
                try:
                    payload = payload.decode('utf-8')
                except UnicodeDecodeError:
                    payload = payload.decode('latin1')

            if payload.startswith('table operations.'):  # Updated to use operations schema
                table_name = payload.split(' ')[1].split('.')[1]
                operation = payload.split(' ')[2]
                
                columns = {}
                for part in payload.split(' ')[3:]:
                    if ':' in part:
                        key, value = part.split(':', 1)
                        columns[key] = value.strip("'")
                
                return {
                    'table': table_name,
                    'operation': operation,
                    'data': columns
                }
                
            return None
            
        except Exception as e:
            self.logger.error(f"Error parsing WAL message: {str(e)}")
            self.logger.debug(f"Payload content: {payload[:200]}...")
            return None

    def _process_order_items(self, order_id):
        """Process order items for a given order"""
        try:
            with self.source_db.cursor() as cursor:
                cursor.execute("""
                    SELECT oi.order_id, oi.product_id, oi.quanity, 
                           o.order_date, o.delivery_date, o.customer_id, o.status
                    FROM operations.order_items oi
                    JOIN operations.orders o ON o.order_id = oi.order_id
                    WHERE oi.order_id = %s
                """, (order_id,))
                items = cursor.fetchall()
                
                for item in items:
                    self._process_order_change({
                        'order_id': item[0],
                        'product_id': item[1],
                        'quantity': item[2],
                        'order_date': item[3],
                        'delivery_date': item[4],
                        'customer_id': item[5],
                        'status': item[6]
                    })
        except Exception as e:
            self.logger.error(f"Error processing order items: {str(e)}")
            raise

    def _process_order_change(self, change_data):
        """Process changes to the orders table"""
        try:
            with self.target_db.cursor() as cursor:
                query = sql.SQL("""
                    INSERT INTO analytics.fact_orders 
                    (order_id, order_date, delivery_date, customer_id, product_id, status, quantity, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (order_id, delivery_date) DO UPDATE SET
                        order_date = EXCLUDED.order_date,
                        delivery_date = EXCLUDED.delivery_date,
                        customer_id = EXCLUDED.customer_id,
                        product_id = EXCLUDED.product_id,
                        status = EXCLUDED.status,
                        quantity = EXCLUDED.quantity,
                        updated_at = NOW();
                """)
                cursor.execute(query, (
                    change_data['order_id'],
                    change_data['order_date'],
                    change_data['delivery_date'],
                    change_data['customer_id'],
                    change_data['product_id'],
                    change_data['status'],
                    change_data['quantity']
                ))
                self.target_db.commit()
                self.processed_count += 1

        except Exception as e:
            self.target_db.rollback()
            self.logger.error(f"Error processing order change: {str(e)}")
            raise

    def _process_customer_change(self, change_data):
        """Process changes to the customers table"""
        try:
            with self.target_db.cursor() as cursor:
                query = sql.SQL("""
                    INSERT INTO analytics.dim_customers 
                    (customer_id, customer_name, is_active, customer_address, updated_at)
                    VALUES (%s, %s, %s, %s, NOW())
                    ON CONFLICT (customer_id) DO UPDATE SET
                        customer_name = EXCLUDED.customer_name,
                        is_active = EXCLUDED.is_active,
                        customer_address = EXCLUDED.customer_address,
                        updated_at = NOW();
                """)
                cursor.execute(query, (
                    change_data['customer_id'],
                    change_data['customer_name'],
                    change_data['is_active'],
                    change_data['customer_address']
                ))
                self.target_db.commit()
                self.processed_count += 1

        except Exception as e:
            self.target_db.rollback()
            self.logger.error(f"Error processing customer change: {str(e)}")
            raise

    def _process_product_change(self, change_data):
        """Process changes to the products table"""
        try:
            with self.target_db.cursor() as cursor:
                query = sql.SQL("""
                    INSERT INTO analytics.dim_products 
                    (product_id, product_name, barcode, unity_price, is_active, updated_at)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (product_id) DO UPDATE SET
                        product_name = EXCLUDED.product_name,
                        barcode = EXCLUDED.barcode,
                        unity_price = EXCLUDED.unity_price,
                        is_active = EXCLUDED.is_active,
                        updated_at = NOW();
                """)
                cursor.execute(query, (
                    change_data['product_id'],
                    change_data['product_name'],
                    change_data['barcode'],
                    change_data['unity_price'],
                    change_data['is_active']
                ))
                self.target_db.commit()
                self.processed_count += 1

        except Exception as e:
            self.target_db.rollback()
            self.logger.error(f"Error processing product change: {str(e)}")
            raise

    def _refresh_materialized_views(self):
        """Refresh materialized views if needed"""
        try:
            now = datetime.now()
            if (now - self.last_refresh).total_seconds() > 300:  # Refresh every 5 minutes
                with self.target_db.cursor() as cursor:
                    for view in self.MATERIALIZED_VIEWS:
                        cursor.execute(f"REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.{view};")
                    self.target_db.commit()
                    self.last_refresh = now
                    self.logger.info("Materialized views refreshed")
        except Exception as e:
            self.target_db.rollback()
            self.logger.error(f"Error refreshing materialized views: {str(e)}")
            raise

    def _process_replication_message(self, msg):
        """Process individual replication message"""
        try:
            if msg.payload:
                payload = msg.payload
                self.logger.debug(f"Processing WAL message: {payload[:200]}...")
                
                change_data = self._parse_payload(payload)
                
                if change_data and change_data['operation'] in ('INSERT', 'UPDATE'):
                    data = change_data['data']
                    
                    if change_data['table'] == 'orders':
                        self._process_order_change(data)
                        # Process associated order items
                        self._process_order_items(data['order_id'])
                    elif change_data['table'] == 'order_items':
                        # When order items change, process the full order
                        self._process_order_items(data['order_id'])
                    elif change_data['table'] == 'customers':
                        self._process_customer_change(data)
                    elif change_data['table'] == 'products':
                        self._process_product_change(data)
                    
                    self._refresh_materialized_views()

        except Exception as e:
            self.logger.error(f"Error processing message: {str(e)}")
            if not self._handle_processing_error(msg, e):
                raise

    def _handle_processing_error(self, msg, error):
        """Handle processing errors with retry logic"""
        try:
            self.logger.warning(f"Retrying failed message: {msg.payload}")
            self.logger.debug(f"Error details: {str(error)}")
            
            if self.error_count < self.MAX_RETRIES:
                time.sleep(self.RETRY_DELAY)
                self.error_count += 1
                return True
            else:
                self.logger.error(f"Max retries reached for message: {msg.payload}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error handling failed message: {str(e)}")
            return False
