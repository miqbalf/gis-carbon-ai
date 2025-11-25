# LandTrendr Sensitivity Analysis & Parameter Tuning Guide

## Understanding LandTrendr Sensitivity

### Why Only Small Areas Detected?

LandTrendr may detect changes in only small areas due to several reasons:

1. **Parameters are too conservative** - Filters out real changes as noise
2. **Data actually shows minimal changes** - Forest is relatively stable
3. **Thresholds are too high** - Requires very large changes to be detected
4. **Time series quality** - Missing data or cloud contamination

### Key Parameters Affecting Sensitivity

#### 1. `spikeThreshold` (Current: 0.85)
- **Purpose**: Filters out noise/spikes in time series
- **Higher values (0.9-0.95)**: Less sensitive, filters more noise
- **Lower values (0.7-0.8)**: More sensitive, detects smaller changes
- **Impact**: Primary control for false positive filtering

#### 2. `recoveryThreshold` (Current: 15 FCD points)
- **Purpose**: Minimum change required to detect recovery
- **Higher values (20-30)**: Requires larger recovery
- **Lower values (5-10)**: Detects smaller recoveries
- **Impact**: Controls minimum detectable change magnitude

#### 3. `maxSegments` (Current: 6)
- **Purpose**: Maximum number of segments in time series model
- **More segments (8-10)**: Can detect more change events
- **Fewer segments (4-5)**: Simpler model, may miss some changes
- **Impact**: Controls complexity of change detection

#### 4. `preventOneYearRecovery` (Current: True)
- **Purpose**: Prevents false recovery detection from single-year spikes
- **True**: More conservative, filters one-year anomalies
- **False**: More sensitive, may include false recoveries

## Diagnostic Tools

### Cell 32: Sensitivity Analysis
- Analyzes current change detection statistics
- Compares with original time series
- Provides recommendations based on detection coverage

### Cell 33: Parameter Comparison
- Tests 4 parameter sets: conservative, moderate, sensitive, very_sensitive
- Compares change detection results
- Recommends optimal parameters

### Cell 34: ML Role Explanation
- Explains how ML can validate LandTrendr results
- Describes parameter optimization workflow
- Outlines hybrid approach

### Cell 35: ML Validation Example
- Practical code for validating changes with ML
- Parameter adjustment strategy
- Hybrid workflow implementation

## How to Determine if Changes are Real

### Step 1: Run Sensitivity Analysis (Cell 32)
```python
# This will show:
# - Change detection coverage (% of area)
# - Change magnitude statistics
# - Comparison with original time series
```

### Step 2: Compare Parameter Sets (Cell 33)
```python
# This will test different sensitivity levels
# Compare results to see if more sensitive parameters detect more changes
```

### Step 3: Verify with Time Series
```python
# Check if original FCD time series shows actual changes
# If time series shows minimal change, LandTrendr is correct
# If time series shows large changes but LandTrendr misses them, parameters need adjustment
```

### Step 4: Validate with ML (Cell 35)
```python
# Use training data to validate detected changes
# ML can distinguish:
# - Real forest loss (1) vs False positive (0)
# - Missed changes (training says change, LandTrendr missed)
```

## ML Role in Parameter Tuning

### 1. Validation Loop
```
LandTrendr (candidate changes) 
  → ML Classification (real vs false) 
  → Parameter Adjustment 
  → Re-run LandTrendr
```

### 2. Parameter Optimization
- Train ML on LandTrendr features from different parameter sets
- Compare ML accuracy across parameter sets
- Select parameters with best ML performance

### 3. Hybrid Approach
- **LandTrendr**: Detects temporal patterns (when changes occur)
- **ML**: Classifies spatial patterns (what changed, severity)
- **Together**: Comprehensive change analysis

### 4. Adaptive Parameters
- Different forest types may need different sensitivity
- ML can learn optimal parameters for different conditions
- Enables region-specific parameter tuning

## Recommended Workflow

### Initial Setup
1. Run LandTrendr with moderate parameters (current setting)
2. Run sensitivity analysis (Cell 32)
3. Check change detection coverage

### If Too Few Changes Detected
1. Run parameter comparison (Cell 33)
2. Try "sensitive" parameters
3. Verify with time series comparison
4. If still few changes, data may show minimal forest loss

### If Too Many Changes Detected
1. Check for false positives using ML validation (Cell 35)
2. Increase `spikeThreshold` (0.85 → 0.90)
3. Increase `recoveryThreshold` (15 → 20)
4. Re-run and validate

### ML Validation
1. Extract change areas from LandTrendr
2. Sample these areas and label with training data
3. Train ML classifier
4. Evaluate accuracy:
   - High accuracy (>80%): Parameters are good
   - Many false positives: Increase thresholds
   - Many missed changes: Decrease thresholds

## Parameter Adjustment Guide

### Scenario 1: Very Few Changes Detected (<1% of area)
**Possible causes:**
- Parameters too conservative
- Data shows minimal changes
- Thresholds too high

**Actions:**
1. Decrease `spikeThreshold`: 0.85 → 0.75
2. Decrease `recoveryThreshold`: 15 → 10
3. Increase `maxSegments`: 6 → 8
4. Verify with time series comparison

### Scenario 2: Too Many Changes Detected (>30% of area)
**Possible causes:**
- Parameters too sensitive
- Many false positives
- Noise in time series

**Actions:**
1. Increase `spikeThreshold`: 0.85 → 0.90
2. Increase `recoveryThreshold`: 15 → 20
3. Use ML to filter false positives
4. Validate with training data

### Scenario 3: Changes Only in Small Areas
**Possible causes:**
- Real localized disturbances
- Parameters appropriate for data
- Need to verify if changes are real

**Actions:**
1. Run sensitivity analysis to check statistics
2. Compare with time series
3. Use ML to validate if changes are real
4. If validated, parameters are correct

## Key Takeaways

1. **LandTrendr sensitivity is controlled by parameters** - Adjust based on your needs
2. **Small change areas may be correct** - Verify with time series and ML
3. **ML validates LandTrendr results** - Creates feedback loop for parameter tuning
4. **Hybrid approach is powerful** - LandTrendr + ML provides comprehensive analysis
5. **Parameters should match your data** - Different forests need different sensitivity

## Next Steps

1. Run Cell 32 (Sensitivity Analysis) to diagnose current situation
2. Run Cell 33 (Parameter Comparison) to test different settings
3. Run Cell 35 (ML Validation) to validate changes with training data
4. Adjust parameters based on results
5. Iterate until optimal balance

