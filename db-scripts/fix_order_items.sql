-- Fix the typo in order_items table
ALTER TABLE operations.order_items RENAME COLUMN quanity TO quantity;

-- Drop existing publication
DROP PUBLICATION IF EXISTS cdc_publication;

-- Create new publication with correct schema
CREATE PUBLICATION cdc_publication FOR TABLE 
    operations.customers,
    operations.products,
    operations.orders,
    operations.order_items;

-- Refresh materialized views
REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.open_orders_by_date_status;
REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.top3_delivery_dates;
REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.pending_items_by_product;
REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.top3_customers_pending_orders;
