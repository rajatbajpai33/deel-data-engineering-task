import click
from utils.db_utils import create_db_connections
from cli.query_handler import QueryHandler
from utils.csv_utils import export_to_csv

@click.group()
def cli():
    """ACME Delivery Services Analytics CLI"""
    pass

@cli.command()
@click.option('--output', default='open_orders.csv', help='Output CSV file name')
def open_orders(output):
    """Export open orders by delivery date and status"""
    try:
        _, target_db = create_db_connections()
        query_handler = QueryHandler(target_db)
        results = query_handler.get_open_orders()
        export_to_csv(results, output)
        click.echo(f"Exported {len(results)} records to {output}")
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)

@cli.command()
@click.option('--output', default='top_delivery_dates.csv', help='Output CSV file name')
def top_delivery_dates(output):
    """Export top 3 delivery dates with most open orders"""
    try:
        _, target_db = create_db_connections()
        query_handler = QueryHandler(target_db)
        results = query_handler.get_top_delivery_dates()
        export_to_csv(results, output)
        click.echo(f"Exported {len(results)} records to {output}")
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)

@cli.command()
@click.option('--output', default='pending_items.csv', help='Output CSV file name')
def pending_items(output):
    """Export pending items by product ID"""
    try:
        _, target_db = create_db_connections()
        query_handler = QueryHandler(target_db)
        results = query_handler.get_pending_items()
        export_to_csv(results, output)
        click.echo(f"Exported {len(results)} records to {output}")
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)

@cli.command()
@click.option('--output', default='top_customers.csv', help='Output CSV file name')
def top_customers(output):
    """Export top 3 customers with most pending orders"""
    try:
        _, target_db = create_db_connections()
        query_handler = QueryHandler(target_db)
        results = query_handler.get_top_customers()
        export_to_csv(results, output)
        click.echo(f"Exported {len(results)} records to {output}")
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)

if __name__ == "__main__":
    cli()
