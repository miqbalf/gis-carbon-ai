-- Initialize databases for GIS Carbon AI project
-- This script creates two separate databases:
-- 1. gis_carbon - for Django application (already exists as default)
-- 2. gis_carbon_data - for GeoServer spatial data

-- Create GeoServer spatial data database
CREATE DATABASE gis_carbon_data;

-- Connect to Django database and enable PostGIS
\c gis_carbon;
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;
CREATE EXTENSION IF NOT EXISTS postgis_tiger_geocoder;

-- Connect to GeoServer database and enable PostGIS
\c gis_carbon_data;
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;
CREATE EXTENSION IF NOT EXISTS postgis_tiger_geocoder;

-- Grant permissions to gis_user for both databases
GRANT ALL PRIVILEGES ON DATABASE gis_carbon TO gis_user;
GRANT ALL PRIVILEGES ON DATABASE gis_carbon_data TO gis_user;

-- Connect back to gis_carbon and grant schema permissions
\c gis_carbon;
GRANT ALL ON SCHEMA public TO gis_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO gis_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO gis_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO gis_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO gis_user;

-- Connect to gis_carbon_data and grant schema permissions
\c gis_carbon_data;
GRANT ALL ON SCHEMA public TO gis_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO gis_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO gis_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO gis_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO gis_user;

-- Create some sample spatial tables for GeoServer
CREATE TABLE IF NOT EXISTS sample_geometries (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    description TEXT,
    geom GEOMETRY(POINT, 4326),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert sample data
INSERT INTO sample_geometries (name, description, geom) VALUES
('Sample Point 1', 'A sample point for testing', ST_GeomFromText('POINT(0 0)', 4326)),
('Sample Point 2', 'Another sample point', ST_GeomFromText('POINT(1 1)', 4326));

-- Grant permissions on the sample table
GRANT ALL PRIVILEGES ON TABLE sample_geometries TO gis_user;
GRANT ALL PRIVILEGES ON SEQUENCE sample_geometries_id_seq TO gis_user;
