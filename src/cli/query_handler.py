import psycopg2
from psycopg2.extras import RealDictCursor
import time
from tqdm import tqdm
from datetime import datetime


class QueryHandler:
    def __init__(self, db_connection):
        self.db_connection = db_connection

    def get_open_orders(self):
        """Get open orders by delivery date and status"""
        query = """
            SELECT delivery_date, status, COUNT(*) AS order_count
            FROM analytics.fact_orders
            WHERE status IN ('PENDING', 'PROCESSING')
            GROUP BY delivery_date, status
            ORDER BY delivery_date, status;
        """
        return self._execute_query(query)

    def get_top_delivery_dates(self):
        """Get top 3 delivery dates with most open orders"""
        query = """
            SELECT delivery_date, COUNT(*) AS order_count
            FROM analytics.fact_orders
            WHERE status IN ('PENDING', 'PROCESSING')
            GROUP BY delivery_date
            ORDER BY order_count DESC
            LIMIT 3;
        """
        return self._execute_query(query)

    def get_pending_items(self):
        """Get pending items by product ID"""
        query = """
            SELECT product_id, SUM(quantity) AS pending_quantity
            FROM analytics.fact_orders
            WHERE status IN ('PENDING', 'PROCESSING')
            GROUP BY product_id;
        """
        return self._execute_query(query)

    def get_top_customers(self):
        """Get top 3 customers with most pending orders"""
        query = """
            SELECT c.customer_id, c.customer_name, COUNT(*) AS pending_order_count
            FROM analytics.fact_orders o
            JOIN analytics.dim_customers c ON o.customer_id = c.customer_id
            WHERE o.status IN ('PENDING', 'PROCESSING')
            GROUP BY c.customer_id, c.customer_name
            ORDER BY pending_order_count DESC
            LIMIT 3;
        """
        return self._execute_query(query)

    def _execute_query(self, query, timeout=30):
        """Execute query with timeout and return results"""
        try:
            start_time = time.time()
            with self.db_connection.cursor(cursor_factory=RealDictCursor) as cursor:
                # Set statement timeout
                cursor.execute(f"SET statement_timeout = {timeout * 1000};")
                
                # Execute main query with progress bar
                with tqdm(total=100, desc="Executing query", unit="%") as pbar:
                    cursor.execute(query)
                    pbar.update(50)  # Query execution started
                    results = cursor.fetchall()
                    pbar.update(50)  # Results fetched
                
                # Validate results
                if not results:
                    raise ValueError("No data returned from query")
                
                # Log query performance
                execution_time = time.time() - start_time
                self._log_query_performance(query, execution_time, len(results))
                
                return results
        except psycopg2.Error as e:
            raise Exception(f"Database error: {str(e)}")
        except Exception as e:
            raise Exception(f"Query execution error: {str(e)}")

    def _log_query_performance(self, query, execution_time, result_count):
        """Log query performance metrics"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = (
            f"[{timestamp}] Query executed in {execution_time:.2f}s, "
            f"returned {result_count} rows\n"
            f"Query: {query[:200]}..."  # Log first 200 chars of query
        )
        with open("query_performance.log", "a") as log_file:
            log_file.write(log_message + "\n")
