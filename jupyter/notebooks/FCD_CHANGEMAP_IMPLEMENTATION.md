# FCD Change Detection Implementation

## Overview

This implementation creates a change detection map from FCD (Forest Canopy Density) time series, matching the LT-GEE `getChangeMap` functionality but using native Earth Engine LandTrendr.

## Key Difference from LT-GEE

**LT-GEE Approach:**
- Uses `ltgee.runLT()` which processes LandTrendr and outputs vertices
- `ltgee.getChangeMap()` extracts change info from vertices array

**Our Approach (Native Earth Engine):**
- Uses native `ee.Algorithms.TemporalSegmentation.LandTrendr()` 
- Native LandTrendr only outputs `['LandTrendr', 'rmse']` (no vertices)
- **Solution**: Process the **original time series collection** (`fcd_collection_lt`) to detect changes
- This matches what LT-GEE does internally - it processes the time series to find changes

## Implementation Flow

### 1. Input Data
- `fcd_collection_lt`: FCD time series ImageCollection (sorted by time)
- Each image has: `system:time_start` (year) and `FCD` band (0-100)

### 2. Change Detection Function
`get_change_map_from_timeseries()`:
- Compares consecutive years in the time series
- Finds greatest loss (FCD decrease) segment
- Extracts: YOD, magnitude, duration, pre-value, post-value

### 3. Change Parameters (matching LT-GEE example)
```python
change_params = {
    'delta': 'loss',        # Detect loss (FCD decrease)
    'mag_threshold': 5,      # Minimum 5 FCD points loss
    'dur_max': 10,           # Maximum 10 years duration
    'preval_min': 20         # Minimum 20 FCD points before change
}
```

### 4. Output Bands
- `yod`: Year of Detection (when loss started)
- `mag`: Magnitude of change (FCD loss amount)
- `dur`: Duration of change (years)
- `preval`: Pre-value (FCD before change)
- `postval`: Post-value (FCD after change)

### 5. Visualization
- Year of Detection: Color-coded by year (purple to red palette)
- Magnitude: Yellow to red gradient (shows loss severity)
- Duration: Blue to red gradient (shows change speed)
- Pre/Post values: FCD values before and after change

## How It Works

1. **Time Series Processing**: Iterates through consecutive image pairs
2. **Loss Calculation**: `loss = prev_fcd - curr_fcd` (positive = loss)
3. **Greatest Loss Selection**: Keeps the segment with maximum loss magnitude
4. **Threshold Filtering**: Masks pixels that don't meet criteria
5. **Visualization**: Creates interactive geemap with all layers

## Comparison with LT-GEE Example

| LT-GEE Example | Our Implementation |
|----------------|-------------------|
| `ltgee.runLT()` | `ee.Algorithms.TemporalSegmentation.LandTrendr()` |
| `ltgee.getChangeMap(lt, changeParams)` | `get_change_map_from_timeseries(fcd_collection_lt, ...)` |
| Processes vertices array | Processes original time series |
| `changeParams` with mag, dur, preval thresholds | Same `change_params` structure |
| Output: yod, mag, dur, preval, postval | Same output bands |

## Why This Works

The native LandTrendr algorithm fits a segmented model to the time series, but doesn't output the segment vertices directly. However, **the original time series contains all the information needed** to detect changes. By comparing consecutive years, we can:

1. Find when FCD decreased (YOD)
2. Calculate how much it decreased (magnitude)
3. Determine how long the change took (duration)
4. Get values before and after (preval, postval)

This matches the LT-GEE approach, which internally processes the time series to extract change information.

## Usage

The implementation is in **Cell 31** of the notebook. It:
1. Checks LandTrendr output structure
2. Processes FCD time series to detect changes
3. Applies thresholds (matching LT-GEE changeParams)
4. Creates interactive visualization with geemap

## Expected Results

- **YOD**: Years when forest loss occurred (2015-2025 range)
- **Magnitude**: FCD loss values (0-100 range, typically 5-50 for significant loss)
- **Duration**: 1-10 years (how quickly loss occurred)
- **Pre-value**: FCD before loss (20-100 range)
- **Post-value**: FCD after loss (0-80 range)

The visualization will show:
- **Purple/Blue areas**: Early loss (2015-2017)
- **Green/Yellow areas**: Mid-period loss (2018-2021)
- **Orange/Red areas**: Recent loss (2022-2025)

