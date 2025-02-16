-- Create analytical schema
CREATE SCHEMA IF NOT EXISTS analytics;

-- Dimension Tables
CREATE TABLE IF NOT EXISTS analytics.dim_customers (
    customer_id BIGINT PRIMARY KEY,
    customer_name VARCHAR(500) NOT NULL,
    is_active BOOLEAN NOT NULL,
    customer_address VARCHAR(500),
    updated_at TIMESTAMP(3)
);

CREATE TABLE IF NOT EXISTS analytics.dim_products (
    product_id BIGINT PRIMARY KEY,
    product_name VARCHAR(500) NOT NULL,
    barcode VARCHAR(26) NOT NULL,
    unity_price DECIMAL NOT NULL,
    is_active BOOLEAN,
    updated_at TIMESTAMP(3)
);

-- Fact Table with partitioning
CREATE TABLE IF NOT EXISTS analytics.fact_orders (
    order_id BIGINT,
    order_date DATE NOT NULL,
    delivery_date DATE NOT NULL,
    customer_id BIGINT REFERENCES analytics.dim_customers(customer_id),
    product_id BIGINT REFERENCES analytics.dim_products(product_id),
    status VARCHAR(20) NOT NULL,
    quantity INTEGER NOT NULL,
    updated_at TIMESTAMP(3),
    PRIMARY KEY (order_id, delivery_date)
) PARTITION BY RANGE (delivery_date);


-- Create partitions for the last 3 years and next year
CREATE TABLE analytics.fact_orders_2022 PARTITION OF analytics.fact_orders
    FOR VALUES FROM ('2022-01-01') TO ('2023-01-01');

CREATE TABLE analytics.fact_orders_2023 PARTITION OF analytics.fact_orders
    FOR VALUES FROM ('2023-01-01') TO ('2024-01-01');

CREATE TABLE analytics.fact_orders_2024 PARTITION OF analytics.fact_orders
    FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

CREATE TABLE analytics.fact_orders_2025 PARTITION OF analytics.fact_orders
    FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');

-- Default partition for older/newer data
CREATE TABLE analytics.fact_orders_default PARTITION OF analytics.fact_orders DEFAULT;


-- Materialized Views for Business Queries
CREATE MATERIALIZED VIEW analytics.open_orders_by_date_status AS
SELECT 
    delivery_date,
    status,
    COUNT(*) AS order_count
FROM analytics.fact_orders
WHERE status IN ('PENDING', 'PROCESSING')
GROUP BY delivery_date, status;

CREATE MATERIALIZED VIEW analytics.top3_delivery_dates AS
SELECT 
    delivery_date,
    COUNT(*) AS order_count
FROM analytics.fact_orders
WHERE status IN ('PENDING', 'PROCESSING')
GROUP BY delivery_date
ORDER BY order_count DESC
LIMIT 3;

CREATE MATERIALIZED VIEW analytics.pending_items_by_product AS
SELECT 
    product_id,
    SUM(quantity) AS pending_quantity
FROM analytics.fact_orders
WHERE status IN ('PENDING', 'PROCESSING')
GROUP BY product_id;

CREATE MATERIALIZED VIEW analytics.top3_customers_pending_orders AS
SELECT 
    c.customer_id,
    c.customer_name,
    COUNT(*) AS pending_order_count
FROM analytics.fact_orders o
JOIN analytics.dim_customers c ON o.customer_id = c.customer_id
WHERE o.status IN ('PENDING', 'PROCESSING')
GROUP BY c.customer_id, c.customer_name
ORDER BY pending_order_count DESC
LIMIT 3;

-- Create indexes for performance
CREATE INDEX idx_fact_orders_status ON analytics.fact_orders(status);
CREATE INDEX idx_fact_orders_delivery_date ON analytics.fact_orders(delivery_date);
CREATE INDEX idx_fact_orders_customer_id ON analytics.fact_orders(customer_id);
CREATE INDEX idx_fact_orders_product_id ON analytics.fact_orders(product_id);

-- Create index on the partition key
CREATE INDEX idx_fact_orders_partition_key ON analytics.fact_orders(delivery_date);

-- Create composite indexes for common query patterns
CREATE INDEX idx_fact_orders_status_date ON analytics.fact_orders(status, delivery_date);
CREATE INDEX idx_fact_orders_customer_status ON analytics.fact_orders(customer_id, status);
CREATE INDEX idx_fact_orders_product_status ON analytics.fact_orders(product_id, status);
