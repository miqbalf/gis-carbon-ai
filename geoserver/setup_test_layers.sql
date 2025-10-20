-- SQL script to create test layers in PostgreSQL for GeoServer
-- This will create public and private layers for authentication testing

-- Create a test schema for our demo
CREATE SCHEMA IF NOT EXISTS auth_demo;

-- 1. PUBLIC LAYER: Sample Geometries (No authentication required)
CREATE TABLE IF NOT EXISTS auth_demo.public_sample_geometries (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    description TEXT,
    category VARCHAR(50),
    geom GEOMETRY(POINT, 4326)
);

-- Insert some public sample data
INSERT INTO auth_demo.public_sample_geometries (name, description, category, geom) VALUES
('Public Point 1', 'This is a public point visible to everyone', 'public', ST_GeomFromText('POINT(106.8456 -6.2088)', 4326)),
('Public Point 2', 'Another public point for testing', 'public', ST_GeomFromText('POINT(106.8500 -6.2100)', 4326)),
('Public Point 3', 'Third public point', 'public', ST_GeomFromText('POINT(106.8400 -6.2050)', 4326));

-- 2. PRIVATE LAYER: User Analysis Results (Authentication required)
CREATE TABLE IF NOT EXISTS auth_demo.private_analysis_results (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    analysis_name VARCHAR(100),
    analysis_type VARCHAR(50),
    result_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    geom GEOMETRY(POLYGON, 4326)
);

-- Insert some private analysis data
INSERT INTO auth_demo.private_analysis_results (user_id, analysis_name, analysis_type, result_data, geom) VALUES
(1, 'Carbon Analysis - User 1', 'carbon_calculation', '{"carbon_stock": 150.5, "area_ha": 25.3}', ST_GeomFromText('POLYGON((106.84 -6.20, 106.85 -6.20, 106.85 -6.21, 106.84 -6.21, 106.84 -6.20))', 4326)),
(2, 'FCD Analysis - User 2', 'forest_density', '{"fcd_score": 75.2, "confidence": 0.85}', ST_GeomFromText('POLYGON((106.85 -6.21, 106.86 -6.21, 106.86 -6.22, 106.85 -6.22, 106.85 -6.21))', 4326)),
(1, 'NDVI Analysis - User 1', 'vegetation_index', '{"ndvi_mean": 0.65, "ndvi_std": 0.12}', ST_GeomFromText('POLYGON((106.83 -6.19, 106.84 -6.19, 106.84 -6.20, 106.83 -6.20, 106.83 -6.19))', 4326));

-- 3. ADMIN LAYER: System Configuration (Admin only)
CREATE TABLE IF NOT EXISTS auth_demo.admin_system_config (
    id SERIAL PRIMARY KEY,
    config_name VARCHAR(100),
    config_value TEXT,
    description TEXT,
    geom GEOMETRY(POINT, 4326)
);

-- Insert admin configuration data
INSERT INTO auth_demo.admin_system_config (config_name, config_value, description, geom) VALUES
('System Center', 'Jakarta', 'Main system configuration point', ST_GeomFromText('POINT(106.8456 -6.2088)', 4326)),
('Backup Center', 'Bandung', 'Backup system configuration', ST_GeomFromText('POINT(107.6186 -6.9039)', 4326));

-- Create spatial indexes for better performance
CREATE INDEX IF NOT EXISTS idx_public_sample_geometries_geom ON auth_demo.public_sample_geometries USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_private_analysis_results_geom ON auth_demo.private_analysis_results USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_admin_system_config_geom ON auth_demo.admin_system_config USING GIST (geom);

-- Create views for different access levels
-- Public view (no restrictions)
CREATE OR REPLACE VIEW auth_demo.v_public_layers AS
SELECT 
    'public_sample_geometries' as layer_name,
    name,
    description,
    category,
    geom
FROM auth_demo.public_sample_geometries;

-- Private view (requires authentication)
CREATE OR REPLACE VIEW auth_demo.v_private_layers AS
SELECT 
    'private_analysis_results' as layer_name,
    analysis_name,
    analysis_type,
    result_data,
    created_at,
    geom
FROM auth_demo.private_analysis_results;

-- Admin view (requires admin role)
CREATE OR REPLACE VIEW auth_demo.v_admin_layers AS
SELECT 
    'admin_system_config' as layer_name,
    config_name,
    config_value,
    description,
    geom
FROM auth_demo.admin_system_config;

-- Grant permissions
-- Public access (everyone can read)
GRANT SELECT ON auth_demo.public_sample_geometries TO PUBLIC;
GRANT SELECT ON auth_demo.v_public_layers TO PUBLIC;

-- Private access (authenticated users only)
GRANT SELECT ON auth_demo.private_analysis_results TO gis_user;
GRANT SELECT ON auth_demo.v_private_layers TO gis_user;

-- Admin access (admin users only)
GRANT SELECT ON auth_demo.admin_system_config TO gis_user;
GRANT SELECT ON auth_demo.v_admin_layers TO gis_user;

-- Update table statistics
ANALYZE auth_demo.public_sample_geometries;
ANALYZE auth_demo.private_analysis_results;
ANALYZE auth_demo.admin_system_config;
