# Planet Downloader Test Scripts

This folder contains test scripts for the PlanetScope downloader functionality.

## Files

1. **test_planet_downloader.py** - Basic unit tests for Planet SDK setup
   - Tests imports, API key, filter creation, session/client creation
   - Run: `python3 test_planet_downloader.py`

2. **test_planet_full_workflow.py** - End-to-end workflow test
   - Tests complete workflow: Load AOI from GCS → Search → Get Results → Prepare Order
   - Uses actual GCS shapefile: `f'gs://{os.getenv(\"GCS_BUCKET_PATH\")}/01-korindo/aoi_buffer/korindo_buffer.shp`'
   - Run: `python3 test_planet_full_workflow.py`
   - Requires: `PLANET_API_KEY` and `GOOGLE_CLOUD_PROJECT` environment variables

3. **check_search_method.py** - Quick check of search method signature
   - Inspects the actual `client.search()` method signature
   - Run: `python3 check_search_method.py`

## Usage

### In Docker Container:
```bash
docker exec gis_jupyter_dev bash -c "cd /usr/src/app/notebooks/test/planet_download && python3 test_planet_full_workflow.py"
```

### In Jupyter Notebook:
The main implementation is in `planet_downloader.ipynb` notebook.

## Test Results

✅ **All tests passed!**
- Successfully searches for PlanetScope images
- Loads AOI from GCS correctly
- Gets list of images with metadata
- Prepares items for ordering

## Key Findings from Testing

1. **Search method**: `client.search(item_types=[...], search_filter=...)` 
   - Parameter is `search_filter`, not `filter`
   - Returns async generator (iterate with `async for`)

2. **Assets**: Use `client.list_item_assets(item_id)` which returns async iterator
   - Not `get_assets()` which doesn't exist

3. **Date parsing**: `date_range_filter` expects `datetime` objects, not strings
   - Use `parse_date()` helper function

4. **Event loop**: Jupyter notebooks need `nest_asyncio` or thread-based solution
   - Use `run_async()` helper function

