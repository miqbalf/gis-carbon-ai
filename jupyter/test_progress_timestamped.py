#!/usr/bin/env python3
"""
Test script with timestamps to verify progress bar updates in real-time.
Shows exactly when each progress update appears.
"""

import sys
import os
import numpy as np
import pandas as pd
import xarray as xr
from datetime import datetime
import time

# Redirect stdout and stderr to /proc/1/fd/2 for docker logs visibility
try:
    _docker_log_file = open("/proc/1/fd/2", "w", buffering=0)  # Unbuffered
    sys.stdout = _docker_log_file
    sys.stderr = _docker_log_file
except Exception:
    pass

def timestamp():
    return datetime.now().strftime('%H:%M:%S.%f')[:-3]

print("=" * 80)
print("PROGRESS BAR REAL-TIME TEST WITH TIMESTAMPS")
print("=" * 80)
print(f"Started at: {timestamp()}")
print()
print("This test will show timestamps for each progress update.")
print("If updates appear with different timestamps, progress bar is working!")
print("If all updates have the same timestamp, progress bar is buffered.")
print()
sys.stdout.flush()

# Create dataset - use more samples to make it take longer
print(f"[{timestamp()}] Creating test dataset...")
n_samples = 1000  # More samples = longer processing = more visible progress
n_times = 30  # More timesteps = longer processing
n_bands = 6
band_list = ['EVI', 'GNDVI', 'NDVI', 'SAVI', 'NBR', 'FCD']

np.random.seed(42)
time_coords = pd.date_range('2015-01-01', periods=n_times, freq='YS')

data_vars = {}
for band in band_list:
    if band == 'FCD':
        data = np.random.rand(n_times, n_samples) * 100
    else:
        data = np.random.rand(n_times, n_samples) * 2 - 1
    data_vars[band] = (['time', 'pixel'], data)

gt_data = np.full((n_times, n_samples), np.nan)
for i in range(n_samples):
    if np.random.rand() < 0.8:
        gt_data[:, i] = np.random.choice([0, 1], size=n_times)

data_vars['ground_truth'] = (['time', 'pixel'], gt_data)
gt_valid = ~np.isnan(gt_data)
data_vars['gt_valid'] = (['time', 'pixel'], gt_valid)

coords = {
    'time': time_coords,
    'pixel': np.arange(n_samples),
    'plot_id': ('pixel', [f'plot_{i % 5 + 1}' for i in range(n_samples)]),
    'x': ('pixel', np.random.rand(n_samples) * 1000 + 500000),
    'y': ('pixel', np.random.rand(n_samples) * 1000 + 9900000),
}

ds = xr.Dataset(data_vars, coords=coords)
valid_mask = ~np.isnan(gt_data).all(axis=0)
valid_pixel_indices = np.where(valid_mask)[0]
n_valid = len(valid_pixel_indices)

X_timeseries = np.full((n_valid, n_times, len(band_list)), np.nan, dtype=np.float32)
for band_idx, band_name in enumerate(band_list):
    band_values = ds[band_name].isel(pixel=valid_pixel_indices).values.T
    X_timeseries[:, :, band_idx] = band_values

dfs_long = []
for band_idx, band_name in enumerate(band_list):
    df_band = pd.DataFrame(X_timeseries[:, :, band_idx])
    df_band['id'] = df_band.index
    df_long = df_band.melt(id_vars='id', var_name='time', value_name='value')
    df_long['kind'] = band_name
    df_long['time'] = df_long['time'].astype(int)
    dfs_long.append(df_long)

df_long_all = pd.concat(dfs_long, ignore_index=True)
df_long_all = df_long_all.dropna(subset=['value'])

print(f"[{timestamp()}] ✅ Prepared: {n_valid} samples")
sys.stdout.flush()

# Feature configuration
selected_features = {'value': {
    'minimum': None,
    'mean': None,
    'maximum': None,
    'standard_deviation': None,
    'variance': None,
    'median': None,
    'quantile': [{'q': 0.25}, {'q': 0.75}],
    'skewness': None,
    'kurtosis': None,
}}

# Configure tqdm
os.environ["TQDM_DISABLE"] = "0"
os.environ["TQDM_NCOLS"] = "120"
os.environ["TQDM_MININTERVAL"] = "0.1"
os.environ["TQDM_MINITERS"] = "1"
os.environ['PYTHONUNBUFFERED'] = '1'

# Redirect stderr
try:
    _original_stderr = sys.stderr
    _proc_stderr = open("/proc/1/fd/2", "w", buffering=0)
    sys.stderr = _proc_stderr
    if hasattr(sys.stderr, 'reconfigure'):
        try:
            sys.stderr.reconfigure(line_buffering=True)
        except:
            pass
except Exception:
    _proc_stderr = sys.stderr

# Patch tqdm
try:
    from tqdm import tqdm
    _original_tqdm_init = tqdm.__init__
    _original_tqdm_refresh = tqdm.refresh
    _original_tqdm_update = tqdm.update
    
    class FlushingFileWrapper:
        def __init__(self, file_obj):
            self._file = file_obj
            if hasattr(file_obj, 'reconfigure'):
                try:
                    file_obj.reconfigure(line_buffering=True)
                except:
                    pass
        
        def write(self, s):
            # Convert carriage returns to newlines for better log visibility
            # tqdm uses \r to overwrite the same line, but in logs we want separate lines
            s_str = str(s)
            # Replace \r with \n to show each update as a new line in logs
            if '\r' in s_str:
                # Split by \r and write each part as a new line with timestamp
                parts = s_str.split('\r')
                for i, part in enumerate(parts):
                    if part.strip():  # Only write non-empty parts
                        timestamp_str = timestamp()
                        self._file.write(f"\n[{timestamp_str}] PROGRESS: {part}")
                        self._file.flush()
            else:
                # Regular write for non-progress lines
                if 'Feature Extraction' in s_str or '%|' in s_str:
                    timestamp_str = timestamp()
                    self._file.write(f"[{timestamp_str}] ")
                self._file.write(s)
                self._file.flush()
        
        def flush(self):
            self._file.flush()
        
        def isatty(self):
            return getattr(self._file, 'isatty', lambda: False)()
        
        def __getattr__(self, name):
            return getattr(self._file, name)
    
    def _patched_tqdm_init(self, *args, **kwargs):
        file_obj = kwargs.get('file', sys.stderr)
        if file_obj is None:
            file_obj = sys.stderr
        kwargs['file'] = FlushingFileWrapper(file_obj)
        kwargs.setdefault('mininterval', 0.1)
        kwargs.setdefault('miniters', 1)
        kwargs.setdefault('dynamic_ncols', True)
        return _original_tqdm_init(self, *args, **kwargs)
    
    def _patched_tqdm_refresh(self, *args, **kwargs):
        result = _original_tqdm_refresh(self, *args, **kwargs)
        try:
            if hasattr(self, 'fp') and self.fp:
                self.fp.flush()
        except:
            pass
        return result
    
    def _patched_tqdm_update(self, n=1):
        result = _original_tqdm_update(self, n)
        try:
            if hasattr(self, 'fp') and self.fp:
                self.fp.flush()
        except:
            pass
        return result
    
    tqdm.__init__ = _patched_tqdm_init
    tqdm.refresh = _patched_tqdm_refresh
    tqdm.update = _patched_tqdm_update
except Exception as e:
    print(f"Warning: Could not patch tqdm: {e}")
    pass

print()
print("=" * 80)
print(f"[{timestamp()}] STARTING FEATURE EXTRACTION")
print("=" * 80)
print(f"[{timestamp()}] Watch for timestamps - each progress update should have a different timestamp!")
print(f"[{timestamp()}] If all timestamps are the same, progress bar is NOT updating in real-time.")
print()
sys.stdout.flush()
sys.stderr.flush()

from tsfresh import extract_features
from tsfresh.utilities.dataframe_functions import impute

start_time = time.time()
fc_params_per_kind = {band: selected_features['value'] for band in band_list}

chunksize = 30  # Smaller chunksize = more progress updates
n_jobs = 2

print(f"[{timestamp()}] Configuration: {n_valid} samples, chunksize={chunksize}, n_jobs={n_jobs}")
print(f"[{timestamp()}] Expected progress updates: ~{n_valid // chunksize} internal chunks")
print(f"[{timestamp()}] Starting extraction...")
print(f"[{timestamp()}] ⏱️  Will check after 10 seconds if progress updates are visible...")
print()
sys.stdout.flush()

# Record start time for 10-second check
extraction_start = time.time()
ten_second_mark = extraction_start + 10

features_df = extract_features(
    df_long_all,
    column_id='id',
    column_sort='time',
    column_kind='kind',
    column_value='value',
    kind_to_fc_parameters=fc_params_per_kind,
    chunksize=chunksize,
    n_jobs=n_jobs,
    disable_progressbar=False
)

elapsed_time = time.time() - start_time

try:
    sys.stderr.flush()
    sys.stdout.flush()
except:
    pass

print()
print("=" * 80)
print(f"[{timestamp()}] EXTRACTION COMPLETE")
print("=" * 80)
print(f"[{timestamp()}] Elapsed time: {elapsed_time:.2f} seconds")
print()

# Check if we saw progress within 10 seconds
time_at_10s = time.time()
if time_at_10s >= ten_second_mark:
    print(f"[{timestamp()}] ✅ Test ran for >10 seconds - progress updates should be visible")
else:
    print(f"[{timestamp()}] ⚠️  Test completed in <10 seconds - might be too fast to see updates")

print()
print("=" * 80)
print("PROGRESS BAR ANALYSIS")
print("=" * 80)
print()
print("🔍 CHECK DOCKER LOGS FOR TIMESTAMPS:")
print("   docker compose logs --tail=300 jupyter | grep -E '(PROGRESS|Feature Extraction)'")
print()
print("✅ GOOD: Different timestamps for each progress update")
print("   [14:01:23.123] PROGRESS: Feature Extraction:   0%|...")
print("   [14:01:23.456] PROGRESS: Feature Extraction:  10%|...")
print("   [14:01:23.789] PROGRESS: Feature Extraction:  20%|...")
print("   (timestamps are different = real-time updates ✅)")
print()
print("❌ BAD: Same timestamp or no timestamps")
print("   Feature Extraction:   0%|...")
print("   Feature Extraction: 100%|...")
print("   (no timestamps or same timestamp = buffered ❌)")
print()
print("=" * 80)

sys.stdout.flush()
sys.stderr.flush()

