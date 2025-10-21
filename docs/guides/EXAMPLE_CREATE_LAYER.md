# Example: Create Your First GeoServer Layer

## Step-by-Step Guide

### Step 1: Create a Spatial Table in PostgreSQL

```bash
# Connect to the gis_carbon_data database
docker exec -it gis_postgres_dev psql -U gis_user -d gis_carbon_data
```

Inside psql, run:

```sql
-- Create a table for forest monitoring plots
CREATE TABLE forest_monitoring_plots (
    id SERIAL PRIMARY KEY,
    plot_name VARCHAR(255) NOT NULL,
    plot_type VARCHAR(50),
    area_hectares DECIMAL(10,2),
    carbon_stock_tons DECIMAL(12,2),
    measurement_date DATE,
    notes TEXT,
    geom GEOMETRY(POINT, 4326)
);

-- Insert some sample data
INSERT INTO forest_monitoring_plots 
(plot_name, plot_type, area_hectares, carbon_stock_tons, measurement_date, geom) 
VALUES
    ('Plot A - Primary Forest', 'Primary', 10.5, 450.25, '2024-01-15', 
     ST_GeomFromText('POINT(106.8270 -6.1751)', 4326)),
    
    ('Plot B - Secondary Forest', 'Secondary', 8.3, 320.80, '2024-01-15',
     ST_GeomFromText('POINT(106.8350 -6.1820)', 4326)),
    
    ('Plot C - Reforestation', 'Planted', 5.2, 125.50, '2024-01-15',
     ST_GeomFromText('POINT(106.8420 -6.1700)', 4326)),
    
    ('Plot D - Primary Forest', 'Primary', 12.8, 580.00, '2024-01-16',
     ST_GeomFromText('POINT(106.8500 -6.1900)', 4326)),
    
    ('Plot E - Agroforestry', 'Mixed', 6.5, 210.75, '2024-01-16',
     ST_GeomFromText('POINT(106.8200 -6.1650)', 4326));

-- Verify the data
SELECT plot_name, plot_type, carbon_stock_tons, 
       ST_AsText(geom) as coordinates
FROM forest_monitoring_plots;

-- Exit psql
\q
```

### Step 2: Publish as GeoServer Layer

```bash
# Publish the table as a layer
./geoserver/create-datastore.sh create-layer \
    gis_carbon \
    gis_carbon_postgis \
    forest_monitoring_plots \
    "Forest Monitoring Plots - Carbon Stock Data"
```

Expected output:
```
✅ Layer 'forest_monitoring_plots' created successfully
   WMS URL: http://localhost:8080/geoserver/gis_carbon/wms?service=WMS&version=1.1.0&request=GetMap&layers=gis_carbon:forest_monitoring_plots&styles=&bbox=-180,-90,180,90&width=768&height=330&srs=EPSG:4326&format=image/png
```

### Step 3: Verify in GeoServer

```bash
# Check layer exists
curl -s -u admin:admin \
  "http://localhost:8080/geoserver/rest/layers/gis_carbon:forest_monitoring_plots.json" \
  | python3 -m json.tool

# Get layer preview URL
echo "Layer Preview: http://localhost:8080/geoserver/gis_carbon/wms?service=WMS&version=1.1.0&request=GetMap&layers=gis_carbon:forest_monitoring_plots&bbox=106.81,-6.20,106.86,-6.16&width=768&height=768&srs=EPSG:4326&format=image/png"
```

### Step 4: Test WMS GetMap Request

```bash
# Download a map image
curl -s -u admin:admin \
  "http://localhost:8080/geoserver/gis_carbon/wms?service=WMS&version=1.1.0&request=GetMap&layers=gis_carbon:forest_monitoring_plots&bbox=106.81,-6.20,106.86,-6.16&width=512&height=512&srs=EPSG:4326&format=image/png" \
  -o forest_plots.png

echo "✅ Map saved to forest_plots.png"
open forest_plots.png  # On macOS
# Or: xdg-open forest_plots.png  # On Linux
```

### Step 5: Test WFS GetFeature Request (Get GeoJSON)

```bash
# Get features as GeoJSON
curl -s -u admin:admin \
  "http://localhost:8080/geoserver/gis_carbon/wfs?service=WFS&version=1.0.0&request=GetFeature&typeName=gis_carbon:forest_monitoring_plots&outputFormat=application/json" \
  | python3 -m json.tool > forest_plots.geojson

echo "✅ GeoJSON saved to forest_plots.geojson"
```

### Step 6: Add to MapStore

1. Open MapStore: http://localhost:8082/mapstore
2. Login with test credentials (demo@example.com / demo123)
3. Create a new map
4. Click "Add Layer" → "Add Layer from Catalog"
5. Select "GeoServer" catalog
6. Search for "forest_monitoring_plots"
7. Click "Add to Map"

### Step 7: Style the Layer (Optional)

Create a simple SLD style:

```bash
cat > /tmp/forest_plots_style.xml << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<StyledLayerDescriptor version="1.0.0" 
    xmlns="http://www.opengis.net/sld" 
    xmlns:ogc="http://www.opengis.net/ogc">
  <NamedLayer>
    <Name>forest_monitoring_plots</Name>
    <UserStyle>
      <Title>Forest Plots by Type</Title>
      <FeatureTypeStyle>
        <!-- Primary Forest - Dark Green -->
        <Rule>
          <Name>Primary Forest</Name>
          <ogc:Filter>
            <ogc:PropertyIsEqualTo>
              <ogc:PropertyName>plot_type</ogc:PropertyName>
              <ogc:Literal>Primary</ogc:Literal>
            </ogc:PropertyIsEqualTo>
          </ogc:Filter>
          <PointSymbolizer>
            <Graphic>
              <Mark>
                <WellKnownName>circle</WellKnownName>
                <Fill>
                  <CssParameter name="fill">#006400</CssParameter>
                </Fill>
                <Stroke>
                  <CssParameter name="stroke">#000000</CssParameter>
                  <CssParameter name="stroke-width">1</CssParameter>
                </Stroke>
              </Mark>
              <Size>12</Size>
            </Graphic>
          </PointSymbolizer>
        </Rule>
        
        <!-- Secondary Forest - Green -->
        <Rule>
          <Name>Secondary Forest</Name>
          <ogc:Filter>
            <ogc:PropertyIsEqualTo>
              <ogc:PropertyName>plot_type</ogc:PropertyName>
              <ogc:Literal>Secondary</ogc:Literal>
            </ogc:PropertyIsEqualTo>
          </ogc:Filter>
          <PointSymbolizer>
            <Graphic>
              <Mark>
                <WellKnownName>circle</WellKnownName>
                <Fill>
                  <CssParameter name="fill">#228B22</CssParameter>
                </Fill>
                <Stroke>
                  <CssParameter name="stroke">#000000</CssParameter>
                  <CssParameter name="stroke-width">1</CssParameter>
                </Stroke>
              </Mark>
              <Size>10</Size>
            </Graphic>
          </PointSymbolizer>
        </Rule>
        
        <!-- Planted/Reforestation - Light Green -->
        <Rule>
          <Name>Planted Forest</Name>
          <ogc:Filter>
            <ogc:PropertyIsEqualTo>
              <ogc:PropertyName>plot_type</ogc:PropertyName>
              <ogc:Literal>Planted</ogc:Literal>
            </ogc:PropertyIsEqualTo>
          </ogc:Filter>
          <PointSymbolizer>
            <Graphic>
              <Mark>
                <WellKnownName>circle</WellKnownName>
                <Fill>
                  <CssParameter name="fill">#90EE90</CssParameter>
                </Fill>
                <Stroke>
                  <CssParameter name="stroke">#000000</CssParameter>
                  <CssParameter name="stroke-width">1</CssParameter>
                </Stroke>
              </Mark>
              <Size>8</Size>
            </Graphic>
          </PointSymbolizer>
        </Rule>
        
        <!-- Mixed/Agroforestry - Yellow-Green -->
        <Rule>
          <Name>Mixed Forest</Name>
          <ogc:Filter>
            <ogc:PropertyIsEqualTo>
              <ogc:PropertyName>plot_type</ogc:PropertyName>
              <ogc:Literal>Mixed</ogc:Literal>
            </ogc:PropertyIsEqualTo>
          </ogc:Filter>
          <PointSymbolizer>
            <Graphic>
              <Mark>
                <WellKnownName>circle</WellKnownName>
                <Fill>
                  <CssParameter name="fill">#9ACD32</CssParameter>
                </Fill>
                <Stroke>
                  <CssParameter name="stroke">#000000</CssParameter>
                  <CssParameter name="stroke-width">1</CssParameter>
                </Stroke>
              </Mark>
              <Size>10</Size>
            </Graphic>
          </PointSymbolizer>
        </Rule>
      </FeatureTypeStyle>
    </UserStyle>
  </NamedLayer>
</StyledLayerDescriptor>
EOF

# Upload the style to GeoServer
curl -u admin:admin -X POST \
  -H "Content-Type: application/vnd.ogc.sld+xml" \
  -d @/tmp/forest_plots_style.xml \
  "http://localhost:8080/geoserver/rest/styles?name=forest_plots_style"

# Apply style to layer
curl -u admin:admin -X PUT \
  -H "Content-Type: text/xml" \
  -d "<layer><defaultStyle><name>forest_plots_style</name></defaultStyle></layer>" \
  "http://localhost:8080/geoserver/rest/layers/gis_carbon:forest_monitoring_plots"

echo "✅ Style applied!"
```

### Step 8: Query via Django/FastAPI

Example Python code to query the layer:

```python
import requests
from requests.auth import HTTPBasicAuth

# WFS GetFeature request
url = "http://localhost:8080/geoserver/gis_carbon/wfs"
params = {
    "service": "WFS",
    "version": "2.0.0",
    "request": "GetFeature",
    "typeName": "gis_carbon:forest_monitoring_plots",
    "outputFormat": "application/json",
    "CQL_FILTER": "carbon_stock_tons > 300"  # Filter high carbon plots
}

response = requests.get(
    url, 
    params=params,
    auth=HTTPBasicAuth('admin', 'admin')
)

data = response.json()
print(f"Found {len(data['features'])} plots with >300 tons carbon")

for feature in data['features']:
    props = feature['properties']
    print(f"  {props['plot_name']}: {props['carbon_stock_tons']} tons")
```

## More Examples

### Create a Polygon Layer (Forest Boundaries)

```sql
-- In psql:
CREATE TABLE forest_boundaries (
    id SERIAL PRIMARY KEY,
    forest_name VARCHAR(255),
    forest_type VARCHAR(50),
    area_hectares DECIMAL(12,2),
    total_carbon_tons DECIMAL(15,2),
    protection_status VARCHAR(100),
    geom GEOMETRY(POLYGON, 4326)
);

-- Insert a sample polygon
INSERT INTO forest_boundaries 
(forest_name, forest_type, area_hectares, total_carbon_tons, protection_status, geom)
VALUES
    ('Central Conservation Area', 'Protected', 500.0, 22500.0, 'National Park',
     ST_GeomFromText('POLYGON((106.82 -6.18, 106.85 -6.18, 106.85 -6.16, 106.82 -6.16, 106.82 -6.18))', 4326));
```

```bash
# Publish polygon layer
./geoserver/create-datastore.sh create-layer \
    gis_carbon gis_carbon_postgis forest_boundaries "Forest Boundary Polygons"
```

### Create a LineString Layer (Patrol Routes)

```sql
-- In psql:
CREATE TABLE patrol_routes (
    id SERIAL PRIMARY KEY,
    route_name VARCHAR(255),
    route_length_km DECIMAL(8,2),
    patrol_frequency VARCHAR(50),
    last_patrol_date DATE,
    geom GEOMETRY(LINESTRING, 4326)
);

INSERT INTO patrol_routes 
(route_name, route_length_km, patrol_frequency, last_patrol_date, geom)
VALUES
    ('North Boundary Route', 5.2, 'Weekly', '2024-01-15',
     ST_GeomFromText('LINESTRING(106.82 -6.17, 106.83 -6.175, 106.84 -6.17, 106.85 -6.175)', 4326));
```

```bash
# Publish line layer
./geoserver/create-datastore.sh create-layer \
    gis_carbon gis_carbon_postgis patrol_routes "Patrol Routes"
```

## Tips and Best Practices

1. **Always use SRID 4326** for coordinates (WGS84 lat/long)
2. **Create indexes** on geometry columns for better performance:
   ```sql
   CREATE INDEX idx_plots_geom ON forest_monitoring_plots USING GIST(geom);
   ```
3. **Add constraints** to ensure data quality:
   ```sql
   ALTER TABLE forest_monitoring_plots 
   ADD CONSTRAINT enforce_srid_geom CHECK (ST_SRID(geom) = 4326);
   ```
4. **Use descriptive layer titles** when publishing
5. **Test with small datasets** first before loading large data

## Troubleshooting

### Layer not appearing in GeoServer?
```bash
# Recalculate bounding box
curl -u admin:admin -X PUT \
  "http://localhost:8080/geoserver/rest/layers/gis_carbon:forest_monitoring_plots/featuretypes.xml" \
  -H "Content-Type: text/xml" \
  -d "<featureType><nativeBoundingBox><compute>true</compute></nativeBoundingBox></featureType>"
```

### Empty map / no features?
```bash
# Check feature count
curl -s -u admin:admin \
  "http://localhost:8080/geoserver/gis_carbon/wfs?service=WFS&version=2.0.0&request=GetFeature&typeName=gis_carbon:forest_monitoring_plots&resultType=hits"
```

### Check layer configuration
```bash
curl -s -u admin:admin \
  "http://localhost:8080/geoserver/rest/layers/gis_carbon:forest_monitoring_plots.json" \
  | python3 -m json.tool
```

---

**You now have a complete working example!** 🎉

Next steps:
- Import your own spatial data
- Create custom styles
- Set up role-based layer access
- Integrate with your Django/FastAPI applications

