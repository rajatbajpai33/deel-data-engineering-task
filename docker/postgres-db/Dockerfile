FROM postgres:15

RUN apt-get update && apt-get install -y postgresql-15-cron

# Configure authentication
RUN echo "host all all localhost/0 md5" >> /usr/share/postgresql/pg_hba.conf
RUN echo "local all all md5" >> /usr/share/postgresql/pg_hba.conf

# Configure replication settings
RUN echo "shared_preload_libraries = 'pg_cron'" >> /usr/share/postgresql/postgresql.conf.sample
RUN echo "cron.database_name = 'finance_db'" >> /usr/share/postgresql/postgresql.conf.sample
RUN echo "wal_level = logical" >> /usr/share/postgresql/postgresql.conf.sample
RUN echo "max_wal_senders = 10" >> /usr/share/postgresql/postgresql.conf.sample
RUN echo "max_replication_slots = 10" >> /usr/share/postgresql/postgresql.conf.sample


USER postgres
