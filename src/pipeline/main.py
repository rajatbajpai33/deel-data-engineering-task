import logging
from decouple import config
from pipeline.cdc_handler import CDCHandler
from utils.db_utils import create_db_connections

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Create database connections
        source_db, target_db = create_db_connections()
        
        # Initialize CDC handler
        cdc_handler = CDCHandler(source_db, target_db)
        
        logger.info("Starting CDC processing...")
        cdc_handler.process_changes()
        
    except Exception as e:
        logger.error(f"Error in pipeline: {str(e)}")
        raise

if __name__ == "__main__":
    main()
