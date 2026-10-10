#!/bin/bash
# Print the live schema_migrations version, with " DIRTY" when the last migration failed.
docker exec openctemio-postgres-1 psql -U openctem -d openctem -tAc \
  "select version || case when dirty then ' DIRTY' else '' end from schema_migrations"
