# Jupyter Resume Guide - SSH Disconnect Safety

## ✅ Your Setup is Already Configured Correctly!

Your `docker-compose.dev.yml` is configured so that:
- **Jupyter runs as a container service** (independent of SSH)
- **Processes continue running** when SSH disconnects
- **Web interface can be resumed** anytime

## Architecture Overview

```
┌──────────────────────────────────────────────────────┐
│  YOUR LAPTOP                                         │
│                                                      │
│  Browser (localhost:8888)                           │
│         ↑                                            │
│         │ SSH Tunnel (can disconnect/reconnect)     │
└─────────┼──────────────────────────────────────────┘
          │
          │ (Reconnectable anytime)
          ↓
┌──────────────────────────────────────────────────────┐
│  VM (Google Cloud)                                   │
│                                                      │
│  ┌────────────────────────────────────────────┐     │
│  │  Docker Container: gis_jupyter_dev         │     │
│  │  Status: Always Running                    │     │
│  │  Restart: unless-stopped                   │     │
│  │                                             │     │
│  │  ┌──────────────────────────────────────┐  │     │
│  │  │  Jupyter Lab (PID 1)                 │  │     │
│  │  │  - Runs 24/7 independent of SSH      │  │     │
│  │  │                                       │  │     │
│  │  │  Active Kernels:                     │  │     │
│  │  │  ├─ Notebook 1 (your_work.ipynb)     │  │     │
│  │  │  │  └─ Variables in memory           │  │     │
│  │  │  │  └─ Running processes             │  │     │
│  │  │  └─ Notebook 2 (analysis.ipynb)      │  │     │
│  │  └──────────────────────────────────────┘  │     │
│  │  Port 8888: ✅ Always Listening           │     │
│  └────────────────────────────────────────────┘     │
│                                                      │
│  Persistent Storage:                                 │
│  ├─ /home/miqbalf/gis-carbon-ai/jupyter/notebooks/  │
│  │  └─ Auto-saved every 2 minutes                   │
│  └─ /mnt/docker-data/jupyter/                       │
│     └─ Your large datasets and outputs              │
└──────────────────────────────────────────────────────┘
```

## Why It Works

### 1. Jupyter is NOT an SSH Process
```yaml
# In docker-compose.dev.yml
command: jupyter lab --ip=0.0.0.0 --port=8888 ...
```
- Jupyter is the **main container process** (PID 1)
- Managed by Docker, not your SSH session
- Lives completely independent of SSH connections

### 2. SSH is ONLY for Port Forwarding
```bash
ssh -L 8888:localhost:8888 user@vm
#     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#     Creates a tunnel, doesn't run Jupyter
```
- SSH just creates a **tunnel** to access the web interface
- When SSH disconnects, only the tunnel closes
- Jupyter keeps running on the VM

### 3. Notebook State is Preserved
- **Jupyter auto-saves** notebooks every 120 seconds
- **Kernel variables** stay in memory (until kernel restarts)
- **Running cells** continue executing
- **Output** is saved in the notebook

## Step-by-Step: Resume After SSH Disconnect

### Step 1: Reconnect SSH Tunnel
```bash
# On your local machine
ssh -L 8888:localhost:8888 user@YOUR_VM_IP

# Keep this terminal open
```

### Step 2: Open Browser
```
http://localhost:8888
```

### Step 3: Check Your Notebook
You'll see **exactly** where you left off:
- All notebooks still open in tabs
- Cell outputs preserved
- Running cells show [*] or completed with [number]

## Testing: Verify It Works

### Test 1: Long-Running Process Test

**In Jupyter notebook, run this:**
```python
import time
from datetime import datetime

print(f"Started: {datetime.now()}")

for i in range(100):
    print(f"Iteration {i} at {datetime.now().strftime('%H:%M:%S')}")
    time.sleep(10)  # 10 seconds each = 16+ minutes total

print(f"Finished: {datetime.now()}")
```

**Then:**
1. Start the cell
2. See first few iterations
3. **Close your browser** (or disconnect SSH)
4. Wait 5 minutes
5. **Reconnect tunnel** and open browser
6. **Result:** Cell is still running, showing later iterations!

### Test 2: Variable Persistence Test

**In a Jupyter cell:**
```python
# Cell 1 - Create data
import pandas as pd
large_df = pd.DataFrame({'value': range(1000000)})
print(f"Created dataframe with {len(large_df)} rows")
```

**Then:**
1. Run the cell
2. **Close browser** completely
3. **Reconnect** after a few minutes

**In a new cell:**
```python
# Cell 2 - Access data (kernel wasn't restarted)
print(f"DataFrame still has {len(large_df)} rows")
print(large_df.head())
```

**Result:** Variables are still there! 🎉

## Monitoring Running Processes

### From Host Machine (VM)

```bash
# Check if container is running
docker ps | grep jupyter

# Check Jupyter processes inside container
docker exec gis_jupyter_dev ps aux | grep python

# Check resource usage (if CPU high = process running)
docker stats gis_jupyter_dev --no-stream

# View container logs
docker logs --tail 50 gis_jupyter_dev

# Follow logs in real-time
docker logs -f gis_jupyter_dev
```

### From Web Interface

After reconnecting:
1. Look at cell execution indicator:
   - **[*]** = Still running
   - **[23]** = Completed (number shows execution order)
2. Check kernel status (top right):
   - **● Python 3** = Kernel active
   - **○ No Kernel** = Kernel died (restart needed)
3. Scroll through cell outputs to see progress

## What Gets Preserved vs Lost

### ✅ Preserved (Survives SSH Disconnect)

| Item | Details |
|------|---------|
| Container | Keeps running (restart: unless-stopped) |
| Jupyter Server | Main process, always running |
| Notebook Kernels | All active kernels continue |
| Running Cells | Processes keep executing |
| Kernel Variables | All variables stay in memory |
| Cell Outputs | Auto-saved in notebook |
| Notebook Files | Auto-saved every 2 minutes |
| Data on Disk | /mnt/data persists |

### ⚠️ Lost (If Container/Kernel Restarts)

| Item | When Lost |
|------|-----------|
| Kernel Variables | Only if kernel dies/restarts |
| Unsaved Changes | Only if not auto-saved yet |
| Running Cell State | Only if kernel crashes |

### ❌ Never Preserved

| Item | Why |
|------|-----|
| Browser Scroll Position | Client-side only |
| Browser Tab State | Local browser data |
| SSH Tunnel | By design - must reconnect |

## Common Scenarios

### Scenario 1: SSH Accidentally Disconnects
**What happens:**
- Jupyter: ✅ Still running
- Your process: ✅ Still running
- Notebook: ✅ Still executing

**What to do:**
```bash
ssh -L 8888:localhost:8888 user@vm  # Reconnect
# Open localhost:8888 in browser
# Continue where you left off
```

### Scenario 2: Close Laptop Lid (SSH Dies)
**What happens:**
- Jupyter: ✅ Still running on VM
- Your GDAL process: ✅ Still processing
- Results: ✅ Being saved to /mnt/data

**What to do:**
```bash
# Later, when you open laptop
ssh -L 8888:localhost:8888 user@vm
# Check results in browser
```

### Scenario 3: VM Maintenance/Restart
**What happens:**
- Container: ✅ Auto-restarts (restart: unless-stopped)
- Jupyter: ✅ Auto-starts
- Kernels: ❌ Lost (will restart fresh)
- Saved notebooks: ✅ Preserved
- Files on disk: ✅ Preserved

**What to do:**
```bash
ssh -L 8888:localhost:8888 user@vm
# Open notebooks
# Re-run cells to restore kernel state
```

## Troubleshooting

### Problem: "Connection Refused" in Browser

**Cause:** SSH tunnel not connected

**Fix:**
```bash
# Check if tunnel is running locally
ps aux | grep "ssh.*8888"

# If nothing, reconnect
ssh -L 8888:localhost:8888 user@vm
```

### Problem: Notebook Shows "Kernel Dead"

**Cause:** Kernel crashed (likely out of memory)

**Fix:**
```bash
# Check container logs
docker logs --tail 100 gis_jupyter_dev | grep -i "error\|killed\|memory"

# Restart kernel from web interface
# Kernel → Restart Kernel
```

### Problem: Can't Remember Which Notebooks Were Running

**Fix:**
```bash
# Check active kernels
docker exec gis_jupyter_dev jupyter notebook list

# See kernel processes
docker exec gis_jupyter_dev ps aux | grep ipykernel
```

## Best Practices

### 1. Save Important Intermediate Results
```python
# In long-running processes
import pickle

for i in range(1000):
    result = process_data(i)
    
    # Save checkpoint every 100 iterations
    if i % 100 == 0:
        with open(f'/mnt/data/checkpoint_{i}.pkl', 'wb') as f:
            pickle.dump(result, f)
        print(f"Checkpoint saved: {i}/1000")
```

### 2. Use Progress Logging
```python
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(message)s',
    handlers=[
        logging.FileHandler(f'/mnt/data/logs/process_{datetime.now():%Y%m%d_%H%M%S}.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

for i in range(1000):
    if i % 10 == 0:
        logger.info(f"Progress: {i}/1000")
    process_data(i)
```

### 3. Use Persistent SSH Tunnels
```bash
# Option A: Use autossh (auto-reconnects)
autossh -M 0 -N -L 8888:localhost:8888 user@vm

# Option B: Use tmux to keep tunnel alive
tmux new -s jupyter-tunnel
ssh -L 8888:localhost:8888 user@vm
# Detach: Ctrl+B, then D
# Tunnel keeps running even if you close terminal
```

### 4. Monitor Resource Usage
```bash
# Watch CPU/Memory in real-time
watch -n 2 'docker stats gis_jupyter_dev --no-stream'

# Alert when process completes
docker logs -f gis_jupyter_dev | grep --line-buffered "SUCCESS\|COMPLETE" && notify-send "Process Done!"
```

## Summary

### Current Configuration (No Changes Needed) ✅
```yaml
jupyter:
  restart: unless-stopped    # ← Auto-restarts
  ports: ["8888:8888"]       # ← Always accessible
  volumes:
    - ./jupyter/notebooks:/usr/src/app/notebooks  # ← Auto-save
    - /mnt/docker-data/jupyter:/mnt/data          # ← Persist data
  command: jupyter lab ...   # ← Runs as PID 1
```

### To Resume After SSH Disconnect
```bash
# 1. Reconnect tunnel (2 seconds)
ssh -L 8888:localhost:8888 user@vm

# 2. Open browser
http://localhost:8888

# 3. Everything is exactly as you left it! ✅
```

### Key Points
- ✅ Jupyter runs independently of SSH
- ✅ Processes survive disconnects
- ✅ Web interface always resumable
- ✅ Data persists on disk
- ✅ No configuration changes needed

**Your setup is production-ready!** Just reconnect the tunnel anytime to resume. 🚀




