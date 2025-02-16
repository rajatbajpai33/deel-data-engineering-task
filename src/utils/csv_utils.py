import csv
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

def export_to_csv(data: List[Dict], file_path: str):
    """Export data to CSV file"""
    try:
        if not data:
            logger.warning("No data to export")
            return

        # Get fieldnames from first dictionary
        fieldnames = data[0].keys()

        with open(file_path, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
            
        logger.info(f"Successfully exported {len(data)} records to {file_path}")

    except Exception as e:
        logger.error(f"Error exporting to CSV: {str(e)}")
        raise
