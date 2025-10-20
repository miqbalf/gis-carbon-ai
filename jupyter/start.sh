#!/bin/bash

# Jupyter Lab startup script
set -e

echo "Starting Jupyter Lab with GIS Carbon AI environment..."

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
while ! nc -z postgres 5432; do
  sleep 1
done
echo "PostgreSQL is ready!"

# Wait for Redis to be ready
echo "Waiting for Redis..."
while ! nc -z redis 6379; do
  sleep 1
done
echo "Redis is ready!"

# Set up environment variables
export PYTHONPATH="/app:/app/gee_lib:/app/ex_ante:$PYTHONPATH"

# Create a default notebook if it doesn't exist
if [ ! -f "/app/notebooks/01_environment_test.ipynb" ]; then
    echo "Creating default test notebook..."
    python -c "
import json
import os

# Create the default test notebook
notebook_content = {
    'cells': [
        {
            'cell_type': 'markdown',
            'metadata': {},
            'source': [
                '# GIS Carbon AI - Environment Test\\n',
                '\\n',
                'This notebook tests the GIS Carbon AI environment including:\\n',
                '- Google Earth Engine\\n',
                '- ArcGIS Python API\\n',
                '- GEE_notebook_Forestry library\\n',
                '- ex_ante library\\n',
                '- Database connections\\n',
                '- GeoServer integration'
            ]
        },
        {
            'cell_type': 'code',
            'execution_count': None,
            'metadata': {},
            'outputs': [],
            'source': [
                '# Test imports\\n',
                'import sys\\n',
                'import os\\n',
                'print(f\"Python version: {sys.version}\")\\n',
                'print(f\"Python path: {sys.path}\")'
            ]
        },
        {
            'cell_type': 'code',
            'execution_count': None,
            'metadata': {},
            'outputs': [],
            'source': [
                '# Test Google Earth Engine\\n',
                'try:\\n',
                '    import ee\\n',
                '    print(\"✅ Google Earth Engine imported successfully\")\\n',
                '    # Initialize EE (will need authentication)\\n',
                '    # ee.Initialize()\\n',
                '    print(\"Google Earth Engine ready for authentication\")\\n',
                'except ImportError as e:\\n',
                '    print(f\"❌ Google Earth Engine import failed: {e}\")'
            ]
        },
        {
            'cell_type': 'code',
            'execution_count': None,
            'metadata': {},
            'outputs': [],
            'source': [
                '# Test ArcGIS Python API\\n',
                'try:\\n',
                '    from arcgis.gis import GIS\\n',
                '    print(\"✅ ArcGIS Python API imported successfully\")\\n',
                '    print(\"ArcGIS ready for authentication\")\\n',
                'except ImportError as e:\\n',
                '    print(f\"❌ ArcGIS Python API import failed: {e}\")'
            ]
        },
        {
            'cell_type': 'code',
            'execution_count': None,
            'metadata': {},
            'outputs': [],
            'source': [
                '# Test GEE_notebook_Forestry library\\n',
                'try:\\n',
                '    from gee_lib.osi.fcd.main_fcd import FCDCalc\\n',
                '    from gee_lib.osi.hansen.historical_loss import HansenHistorical\\n',
                '    print(\"✅ GEE_notebook_Forestry library imported successfully\")\\n',
                'except ImportError as e:\\n',
                '    print(f\"❌ GEE_notebook_Forestry library import failed: {e}\")\\n',
                '    print(\"Available paths:\", sys.path)"
            ]
        },
        {
            'cell_type': 'code',
            'execution_count': None,
            'metadata': {},
            'outputs': [],
            'source': [
                '# Test ex_ante library\\n',
                'try:\\n',
                '    # Add ex_ante to path if it exists\\n',
                '    ex_ante_path = \"/app/ex_ante\"\\n',
                '    if ex_ante_path not in sys.path:\\n',
                '        sys.path.append(ex_ante_path)\\n',
                '    \\n',
                '    # Try to import ex_ante modules\\n',
                '    import ex_ante\\n',
                '    print(\"✅ ex_ante library imported successfully\")\\n',
                'except ImportError as e:\\n',
                '    print(f\"❌ ex_ante library import failed: {e}\")\\n',
                '    print(\"Note: ex_ante library may not be mounted yet\")'
            ]
        },
        {
            'cell_type': 'code',
            'execution_count': None,
            'metadata': {},
            'outputs': [],
            'source': [
                '# Test database connection\\n',
                'try:\\n',
                '    import psycopg2\\n',
                '    conn = psycopg2.connect(\\n',
                '        host=\"postgres\",\\n',
                '        database=\"gis_carbon_data\",\\n',
                '        user=\"gis_user\",\\n',
                '        password=\"gis_password\"\\n',
                '    )\\n',
                '    print(\"✅ Database connection successful\")\\n',
                '    conn.close()\\n',
                'except Exception as e:\\n',
                '    print(f\"❌ Database connection failed: {e}\")'
            ]
        },
        {
            'cell_type': 'code',
            'execution_count': None,
            'metadata': {},
            'outputs': [],
            'source': [
                '# Test GeoServer connection\\n',
                'try:\\n',
                '    import requests\\n',
                '    response = requests.get(\"http://geoserver:8080/geoserver/rest/about/status.json\")\\n',
                '    if response.status_code == 200:\\n',
                '        print(\"✅ GeoServer connection successful\")\\n',
                '    else:\\n',
                '        print(f\"❌ GeoServer connection failed: {response.status_code}\")\\n',
                'except Exception as e:\\n',
                '    print(f\"❌ GeoServer connection failed: {e}\")'
            ]
        }
    ],
    'metadata': {
        'kernelspec': {
            'display_name': 'Python 3',
            'language': 'python',
            'name': 'python3'
        },
        'language_info': {
            'codemirror_mode': {'name': 'ipython', 'version': 3},
            'file_extension': '.py',
            'mimetype': 'text/x-python',
            'name': 'python',
            'nbconvert_exporter': 'python',
            'pygments_lexer': 'ipython3',
            'version': '3.10.12'
        }
    },
    'nbformat': 4,
    'nbformat_minor': 4
}

# Write the notebook
with open('/app/notebooks/01_environment_test.ipynb', 'w') as f:
    json.dump(notebook_content, f, indent=2)

print('Default test notebook created!')
"
fi

# Start Jupyter Lab
echo "Starting Jupyter Lab..."
exec jupyter lab \
    --ip=0.0.0.0 \
    --port=8888 \
    --no-browser \
    --allow-root \
    --NotebookApp.token='' \
    --NotebookApp.password='' \
    --NotebookApp.disable_check_xsrf=True \
    --NotebookApp.allow_origin='*' \
    --NotebookApp.allow_remote_access=True \
    --ServerApp.root_dir=/app/notebooks
