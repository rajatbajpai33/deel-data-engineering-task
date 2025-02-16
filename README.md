## ACME Delivery Services Analytics Platform

## Overview
This platform provides real-time analytics and reporting capabilities for ACME Delivery Services. It processes Change Data Capture (CDC) events from the transactional database and loads them into the analytical database for reporting. The system includes:

- CDC Pipeline: Captures changes from the transactional database
- Analytical Database: Stores processed data for analytics
- CLI Application: Provides query capabilities and data export

## Prerequisites
- Docker 20.10.0+
- Docker Compose 1.29.0+
- Python 3.8+

## Setup Instructions
1. Clone the repository:
   ```bash
   git clone https://github.com/acme/delivery-analytics.git
   cd delivery-analytics
   ```

2. Build and start the services:
   ```bash
   docker-compose up -d
   ```

3. Initialize the CDC pipeline:
   ```bash
   docker exec -it data-pipeline python src/pipeline/main.py
   ```

4. Run queries using the CLI:
   ```bash
   docker exec -it data-pipeline python src/cli/main.py --help
   ```

## Available Queries
- Get open orders by delivery date and status:
  ```bash
  docker exec -it data-pipeline python src/cli/main.py open_orders --output open_orders.csv
  ```

- Get top 3 delivery dates with most open orders:
  ```bash
  docker exec -it data-pipeline python src/cli/main.py top_delivery_dates --output top_dates.csv
  ```

- Get pending items by product ID:
  ```bash
  docker exec -it data-pipeline python src/cli/main.py pending_items --output pending_items.csv
  ```

- Get top 3 customers with most pending orders:
  ```bash
  docker exec -it data-pipeline python src/cli/main.py top_customers --output top_customers.csv
  ```

## Monitoring
- Check database status:
  ```bash
  docker exec -it transactions-db pg_isready -U finance_db_user -d finance_db
  docker exec -it analytical-db pg_isready -U analytics_user -d analytics_db
  ```

- View pipeline logs:
  ```bash
  docker logs data-pipeline
  ```

## Database Backups
- Create backup:
  ```bash
  docker exec -it transactions-db pg_dump -U finance_db_user -Fc finance_db > backup.dump
  docker exec -it analytical-db pg_dump -U analytics_user -Fc analytics_db > analytics_backup.dump
  ```

- Restore backup:
  ```bash
  docker exec -i transactions-db pg_restore -U finance_db_user -d finance_db < backup.dump
  docker exec -i analytical-db pg_restore -U analytics_user -d analytics_db < analytics_backup.dump
  ```

## Future Enhancements
- Setting up monitoring and alerting
- Scaling the pipeline using Kubernetes
- Implementing proper security measures

### Overview

This platform provides real-time analytics and reporting capabilities for ACME Delivery Services. It processes Change Data Capture (CDC) events from the transactional database and loads them into the analytical database for reporting. The system includes:

1. Transactional Database (PostgreSQL)
2. Analytical Database (PostgreSQL)
3. Data Pipeline (Python)
4. CLI Application for Business Queries

![System Architecture](./diagrams/system-architecture.png)

### Prerequisites

- Docker (v20.10+)
- Docker Compose (v2.1+)
- Python 3.9+ (for local development)
- Minimum 4GB RAM
- Minimum 10GB disk space
- Unix-based system (Linux/MacOS) or Windows with WSL2

### Detailed Installation Guide

1. Clone the repository:
   ```bash
   git clone https://github.com/acme-delivery/analytics-platform.git
   cd analytics-platform
   ```

2. Verify Docker and Docker Compose versions:
   ```bash
   docker --version
   docker-compose --version
   ```

3. Start the services:
   ```bash
   docker-compose up -d
   ```

4. Monitor service initialization:
   ```bash
   docker-compose logs -f
   ```

5. Verify services are healthy:
   ```bash
   docker-compose ps
   ```

6. Initialize the CDC pipeline:
   ```bash
   docker exec -it data-pipeline python src/pipeline/main.py
   ```

7. Access the CLI application:
   ```bash
   docker exec -it data-pipeline python src/cli/main.py --help
   ```

8. Verify data exports:
   ```bash
   ls -l data-exports/
   ```

### System Architecture & Data Model

The platform consists of three main components:

#### Database Schema Overview

**Transactional Database Schema:**
```sql
CREATE SCHEMA IF NOT EXISTS operations;

CREATE TABLE IF NOT EXISTS operations.customers(
    customer_id      BIGSERIAL NOT NULL PRIMARY KEY,
    customer_name    VARCHAR(500) NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS operations.orders(
    order_id         BIGSERIAL NOT NULL PRIMARY KEY,
    customer_id      BIGINT NOT NULL REFERENCES operations.customers(customer_id),
    order_date       TIMESTAMP NOT NULL,
    delivery_date   TIMESTAMP,
    status          VARCHAR(50) NOT NULL
);
```

**Analytical Database Schema:**
```sql
CREATE SCHEMA IF NOT EXISTS analytics;

CREATE TABLE IF NOT EXISTS analytics.dim_customers (
    customer_id BIGINT PRIMARY KEY,
    customer_name VARCHAR(500),
    is_active BOOLEAN
);

CREATE TABLE IF NOT EXISTS analytics.fact_orders (
    order_id BIGINT PRIMARY KEY,
    customer_id BIGINT,
    order_date TIMESTAMP,
    delivery_date TIMESTAMP,
    status VARCHAR(50)
);
```

1. **Transactional Database**
   - Stores operational data
   - Host: `transactions-db`
   - Port: 5432
   - Database: `finance_db`
   - User: `finance_db_user`
   - Password: `1234`

2. **Analytical Database**
   - Stores processed data for analytics
   - Host: `analytical-db`
   - Port: 5433
   - Database: `analytics_db`
   - User: `analytics_user`
   - Password: `analytics123`

3. **Data Pipeline**
   - Processes CDC events
   - Transforms and loads data
   - Runs continuously

### Using the CLI Application

The CLI application provides commands for exporting business insights. Here are detailed examples with expected output formats:

1. **Export Open Orders**
```bash
docker exec -it data-pipeline python src/cli/main.py open_orders --output open_orders.csv
```
Example Output (CSV):
```csv
order_id,customer_id,order_date,delivery_date,status
1001,501,2023-01-15 10:30:00,2023-01-20 09:00:00,PENDING
1002,502,2023-01-16 14:15:00,2023-01-21 10:30:00,PROCESSING
```

2. **Top Delivery Dates**
```bash
docker exec -it data-pipeline python src/cli/main.py top_delivery_dates --output top_dates.csv
```
Example Output (CSV):
```csv
delivery_date,order_count
2023-01-20,150
2023-01-21,120
2023-01-22,100
```

3. **Pending Items**
```bash
docker exec -it data-pipeline python src/cli/main.py pending_items --output pending_items.csv
```
Example Output (CSV):
```csv
product_id,quantity,last_updated
P1001,50,2023-01-15 10:30:00
P1002,30,2023-01-16 14:15:00
```

4. **Top Customers**
```bash
docker exec -it data-pipeline python src/cli/main.py top_customers --output top_customers.csv
```
Example Output (CSV):
```csv
customer_id,customer_name,total_orders
501,Acme Corp,150
502,Globex Inc,120
503,Initech LLC,100
```

```bash
# Export open orders by delivery date and status
docker exec -it data-pipeline python src/cli/main.py open_orders --output open_orders.csv

# Export top 3 delivery dates with most open orders
docker exec -it data-pipeline python src/cli/main.py top_delivery_dates --output top_dates.csv

# Export pending items by product ID
docker exec -it data-pipeline python src/cli/main.py pending_items --output pending_items.csv

# Export top 3 customers with most pending orders
docker exec -it data-pipeline python src/cli/main.py top_customers --output top_customers.csv
```

### Development & Contribution Guide

#### Local Development Setup

1. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -r dev-requirements.txt
   ```

3. Run tests:
   ```bash
   pytest tests/
   ```

4. Start development services:
   ```bash
   docker-compose -f docker-compose.dev.yml up -d
   ```

#### Contribution Guidelines

1. Fork the repository and create a feature branch
2. Follow the coding style guidelines
3. Write unit tests for new features
4. Update documentation
5. Submit a pull request with detailed description

#### Production Deployment

For production deployment, consider:
- Using managed PostgreSQL services
- Implementing proper backup strategies
- Setting up monitoring and alerting
- Scaling the pipeline using Kubernetes
- Implementing proper security measures

### Monitoring & Maintenance

#### Log Management

Access database logs:
```bash
docker logs transactions-db
docker logs analytical-db
```

View pipeline logs:
```bash
docker logs data-pipeline
```

#### Health Checks

Verify database health:
```bash
docker exec -it transactions-db pg_isready -U finance_db_user -d finance_db
docker exec -it analytical-db pg_isready -U analytics_user -d analytics_db
```

Check pipeline status:
```bash
docker exec -it data-pipeline python src/pipeline/main.py --status
```

#### Backup Strategy

1. Create database backups:
```bash
docker exec -it transactions-db pg_dump -U finance_db_user -Fc finance_db > backup.dump
docker exec -it analytical-db pg_dump -U analytics_user -Fc analytics_db > analytics_backup.dump
```

2. Restore from backup:
```bash
docker exec -i transactions-db pg_restore -U finance_db_user -d finance_db < backup.dump
docker exec -i analytical-db pg_restore -U analytics_user -d analytics_db < analytics_backup.dump
```

### Troubleshooting

**Issue**: CDC not processing changes
- Verify replication slot exists:
  ```sql
  SELECT * FROM pg_replication_slots;
  ```
- Check publication:
  ```sql
  SELECT * FROM pg_publication;
  ```

**Issue**: CLI commands failing
- Verify database connections:
  ```bash
  docker exec -it data-pipeline python src/utils/db_utils.py
  ```

### Support

For assistance, contact:
- Email: support@acme-delivery.com
- Slack: #analytics-platform-support
