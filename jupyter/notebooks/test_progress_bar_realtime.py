#!/usr/bin/env python3
"""
Test script to verify progress bar updates in real-time during processing,
not just at the end.
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
    _docker_log_file = open("/proc/1/fd/2", "w", buffering=1)  # Line buffered
    sys.stdout = _docker_log_file
    sys.stderr = _docker_log_file
except Exception:
    pass

print("=" * 80)
print("PROGRESS BAR REAL-TIME UPDATE TEST")
print("=" * 80)
print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()
print("This test will verify that the progress bar updates DURING processing,")
print("not just at the end. Watch for incremental updates (0% -> 10% -> 20% -> ...)")
print()
sys.stdout.flush()
sys.stderr.flush()

# Create a larger dataset to make processing take longer
print("Creating test dataset (500 samples, 20 timesteps, 6 bands)...")
n_samples = 500
n_times = 20
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
print(f"✅ Created dataset: {n_samples} samples × {n_times} timesteps")
print()
sys.stdout.flush()

# Prepare data
print("Preparing data for tsfresh...")
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

print(f"✅ Prepared: {n_valid} samples, {len(df_long_all):,} long-format rows")
print()
sys.stdout.flush()

# Feature configuration (more features to make it take longer)
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
os.environ["TQDM_MININTERVAL"] = "0.1"  # Update every 0.1 seconds (very frequent)
os.environ["TQDM_MINITERS"] = "1"

# Redirect stderr with unbuffered mode
try:
    _original_stderr = sys.stderr
    _proc_stderr = open("/proc/1/fd/2", "w", buffering=0)  # UNBUFFERED for real-time updates
    sys.stderr = _proc_stderr
    # Force line buffering if available
    if hasattr(sys.stderr, 'reconfigure'):
        try:
            sys.stderr.reconfigure(line_buffering=True)
        except:
            pass
except Exception:
    _proc_stderr = sys.stderr

# Patch tqdm to force immediate flushing on every update
try:
    from tqdm import tqdm as _tqdm_module
    _original_tqdm_init = _tqdm_module.tqdm.__init__
    _original_tqdm_refresh = _tqdm_module.tqdm.refresh
    _original_tqdm_update = _tqdm_module.tqdm.update
    
    # File wrapper that forces immediate flush
    class FlushingFileWrapper:
        def __init__(self, file_obj):
            self._file = file_obj
            if hasattr(file_obj, 'reconfigure'):
                try:
                    file_obj.reconfigure(line_buffering=True)
                except:
                    pass
        
        def write(self, s):
            self._file.write(s)
            self._file.flush()  # CRITICAL: flush immediately
        
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
        # Force flush after refresh
        try:
            if hasattr(self, 'fp') and self.fp:
                self.fp.flush()
        except:
            pass
        return result
    
    def _patched_tqdm_update(self, n=1):
        result = _original_tqdm_update(self, n)
        # Force flush after update
        try:
            if hasattr(self, 'fp') and self.fp:
                self.fp.flush()
        except:
            pass
        return result
    
    _tqdm_module.tqdm.__init__ = _patched_tqdm_init
    _tqdm_module.tqdm.refresh = _patched_tqdm_refresh
    _tqdm_module.tqdm.update = _patched_tqdm_update
except Exception as e:
    print(f"Warning: Could not patch tqdm: {e}")
    pass

print("=" * 80)
print("STARTING FEATURE EXTRACTION")
print("=" * 80)
print("Watch the progress bar below - it should update incrementally:")
print("  0% -> 10% -> 20% -> 30% -> ... -> 100%")
print("If you only see 0% and then 100% at the end, the progress bar is NOT working!")
print()
print("Starting extraction at:", datetime.now().strftime('%H:%M:%S.%f')[:-3])
print()
sys.stdout.flush()
sys.stderr.flush()

# Extract features with progress bar
from tsfresh import extract_features
from tsfresh.utilities.dataframe_functions import impute

start_time = time.time()
progress_check_time = start_time + 10  # Check after 10 seconds

fc_params_per_kind = {band: selected_features['value'] for band in band_list}

# Use smaller chunksize to create more progress updates
chunksize = 50  # Small chunksize = more progress updates
n_jobs = 2

print(f"Configuration:")
print(f"  Samples: {n_valid}")
print(f"  Chunksize: {chunksize} (will create ~{n_valid // chunksize} progress updates)")
print(f"  Workers: {n_jobs}")
print()
print("⏱️  PROGRESS CHECK: Will check if progress bar updates appear within 10 seconds...")
print("   If no updates appear in 10s, the progress bar is NOT working in real-time!")
print()
sys.stdout.flush()
sys.stderr.flush()

# Start extraction in a way we can monitor
import threading

progress_seen = {'value': False}
progress_times = []

def monitor_progress():
    """Monitor if progress updates appear"""
    while time.time() < progress_check_time:
        time.sleep(0.5)
        # Check docker logs for progress updates (we can't easily do this from here)
        # Instead, we'll check after extraction
    if not progress_seen['value']:
        print()
        print("⚠️  WARNING: No progress updates detected in first 10 seconds!")
        print("   This suggests the progress bar is NOT updating in real-time.")
        sys.stdout.flush()

# Start monitoring thread
monitor_thread = threading.Thread(target=monitor_progress, daemon=True)
monitor_thread.start()

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

# Flush immediately after extraction
try:
    sys.stderr.flush()
    sys.stdout.flush()
except:
    pass

print()
print("=" * 80)
print("EXTRACTION COMPLETE")
print("=" * 80)
print(f"Completed at: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
print(f"Elapsed time: {elapsed_time:.2f} seconds")
print(f"Feature matrix shape: {features_df.shape}")
print()

# Check if progress bar was visible
print("=" * 80)
print("PROGRESS BAR TEST RESULTS")
print("=" * 80)
print()
print("📊 ANALYSIS:")
print(f"  Total processing time: {elapsed_time:.2f} seconds")
if elapsed_time < 10:
    print(f"  ⚠️  Processing completed in <10 seconds - progress bar might appear to jump")
    print(f"     This is normal for fast processing, but updates should still be visible")
else:
    print(f"  ✅ Processing took >10 seconds - progress bar should show incremental updates")
print()
print("🔍 CHECK DOCKER LOGS:")
print("  Run: docker compose logs --tail=200 jupyter | grep 'Feature Extraction'")
print()
print("Expected behavior in logs:")
print("  ✅ GOOD: Multiple progress lines with incremental percentages:")
print("     Feature Extraction:   0%|...")
print("     Feature Extraction:  10%|...")
print("     Feature Extraction:  20%|...")
print("     ... (multiple updates)")
print("     Feature Extraction: 100%|...")
print()
print("  ❌ BAD: Only one or two progress lines:")
print("     Feature Extraction:   0%|...")
print("     Feature Extraction: 100%|... (appears only at end)")
print()
print("=" * 80)
print("💡 TIP: Check docker logs in real-time to see if updates appear incrementally:")
print("   docker compose logs -f jupyter | grep 'Feature Extraction'")
print("=" * 80)

sys.stdout.flush()
sys.stderr.flush()

