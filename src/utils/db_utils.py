import psycopg2
import time
import logging
from decouple import config
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

def create_db_connections(max_retries=10, retry_delay=10):
    """Create connections to both source and analytical databases with retry logic
    
    Args:
        max_retries (int): Maximum number of connection attempts
        retry_delay (int): Delay in seconds between attempts
        
    Returns:
        tuple: (source_db_connection, target_db_connection)
        
    Raises:
        Exception: If connection fails after max retries
    """

    source_db = None
    target_db = None
    retries = 0
    
    while retries < max_retries:
        try:
            # Source database connection
            source_db = psycopg2.connect(
                dbname=config('TRANSACTIONS_DB_NAME', default='finance_db'),
                user=config('TRANSACTIONS_DB_USER', default='finance_db_user'),
                password=config('TRANSACTIONS_DB_PASSWORD', default='1234'),
                host=config('TRANSACTIONS_DB_HOST', default='transactions-db'),
                port=config('TRANSACTIONS_DB_PORT', default='5432', cast=int),
                cursor_factory=RealDictCursor,
                connect_timeout=5
            )

            # Analytical database connection
            target_db = psycopg2.connect(
                dbname=config('ANALYTICAL_DB_NAME', default='analytics_db'),
                user=config('ANALYTICAL_DB_USER', default='analytics_user'),
                password=config('ANALYTICAL_DB_PASSWORD', default='analytics123'),
                host=config('ANALYTICAL_DB_HOST', default='analytical-db'),
                port=config('ANALYTICAL_DB_PORT', default='5432', cast=int),
                cursor_factory=RealDictCursor,
                connect_timeout=5
            )

            return source_db, target_db

        except psycopg2.OperationalError as e:
            retries += 1
            logger.warning(f"Connection attempt {retries}/{max_retries} failed: {str(e)}")
            if retries >= max_retries:
                logger.error(f"Failed to connect to database after {max_retries} attempts")
                raise Exception(f"Failed to connect to database after {max_retries} attempts: {str(e)}")
            logger.info(f"Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
            continue


        except Exception as e:
            raise Exception(f"Database connection error: {str(e)}")
