# Test: Jupyter Survives SSH Disconnect

## Purpose
Verify that Jupyter kernels and running processes continue when SSH disconnects and can be resumed via web interface.

## Pre-Test: Verify Container is Running

```bash
# On VM, check container status
docker ps | grep jupyter

# Check uptime (should show current time)
docker inspect gis_jupyter_dev --format='Started: {{.State.StartedAt}}'

# Note this time - we'll verify it doesn't change after SSH disconnect
```

---

## Test 1: Simple Variable Persistence (2 minutes)

### Step 1: Connect and Create Variables
```bash
# From your laptop (with Cursor)
ssh -L 8888:localhost:8888 user@your-vm-ip
```

Open browser: `http://localhost:8888`

**In a new Jupyter notebook:**
```python
# Cell 1: Create variables
test_number = 12345
test_string = "This should persist!"
test_list = list(range(100))

print(f"Created test_number: {test_number}")
print(f"Created test_string: {test_string}")
print(f"Created test_list with {len(test_list)} items")
```

Run the cell ✅

### Step 2: Disconnect SSH
- Close Cursor completely (or just the SSH connection)
- Wait 30 seconds

### Step 3: Reconnect and Verify
```bash
# Reconnect SSH tunnel
ssh -L 8888:localhost:8888 user@your-vm-ip
```

Open browser: `http://localhost:8888`

**In the SAME notebook (should still be open):**
```python
# Cell 2: Check if variables exist
print(f"test_number still exists: {test_number}")
print(f"test_string still exists: {test_string}")
print(f"test_list still has {len(test_list)} items")
print("\n✅ All variables persisted!")
```

**Expected Result:** All variables print correctly! ✅

**If variables are gone:** The kernel restarted (container issue, not SSH issue)

---

## Test 2: Long-Running Process (10 minutes)

### Step 1: Start Long Process
```bash
# Connect
ssh -L 8888:localhost:8888 user@your-vm-ip
```

Open `http://localhost:8888`

**In a new notebook:**
```python
import time
from datetime import datetime

print(f"🚀 Started: {datetime.now().strftime('%H:%M:%S')}")
print("This will run for 10 minutes...")
print("You can disconnect SSH now!\n")

for i in range(60):  # 60 iterations x 10 seconds = 10 minutes
    current_time = datetime.now().strftime('%H:%M:%S')
    print(f"[{current_time}] Iteration {i+1}/60 - Still running...")
    time.sleep(10)

print(f"\n✅ Finished: {datetime.now().strftime('%H:%M:%S')}")
```

### Step 2: Start Cell and Disconnect
1. Click "Run" on the cell
2. Wait until you see first 3-4 iterations printing
3. **Close Cursor completely** (or disconnect SSH)
4. Wait 5 minutes

### Step 3: Reconnect and Check Progress
```bash
# Reconnect
ssh -L 8888:localhost:8888 user@your-vm-ip
```

Open `http://localhost:8888`

**Expected Result:**
- Cell shows **[*]** (still running) OR **[number]** (finished)
- You see iterations 30-40+ (proving it continued while disconnected)
- Process didn't restart from iteration 1

### Step 4: Verify from VM (Optional)
While SSH is disconnected, from another SSH session to the VM:

```bash
# Check container is still running (should NOT have restarted)
docker inspect gis_jupyter_dev --format='Started: {{.State.StartedAt}}'
# Compare with time from Pre-Test - should be the SAME

# Check Python processes (should see high CPU if running)
docker exec gis_jupyter_dev ps aux | grep python
# Should show kernel with some CPU usage

# Check container logs (should see iteration messages)
docker logs --tail 10 gis_jupyter_dev
```

---

## Test 3: Data Persistence to Disk (5 minutes)

### Step 1: Save Data While Connected
```bash
ssh -L 8888:localhost:8888 user@your-vm-ip
```

Open `http://localhost:8888`

```python
import pandas as pd
from datetime import datetime

# Create and save data
df = pd.DataFrame({
    'id': range(10000),
    'value': range(10000)
})

filename = f'/mnt/data/test_{datetime.now():%Y%m%d_%H%M%S}.csv'
df.to_csv(filename, index=False)

print(f"✅ Saved {len(df)} rows to: {filename}")
print(f"File size: {os.path.getsize(filename) / 1024:.2f} KB")
```

### Step 2: Disconnect SSH
Close Cursor/SSH

### Step 3: Reconnect and Verify File Exists
```bash
ssh -L 8888:localhost:8888 user@your-vm-ip
```

Open `http://localhost:8888`

```python
import glob
import os

# List all test files
test_files = glob.glob('/mnt/data/test_*.csv')
print(f"Found {len(test_files)} test files:")
for f in test_files:
    size = os.path.getsize(f)
    print(f"  - {os.path.basename(f)} ({size:,} bytes)")

# Read back the data
latest_file = max(test_files, key=os.path.getctime)
df_loaded = pd.read_csv(latest_file)
print(f"\n✅ Loaded {len(df_loaded)} rows from {os.path.basename(latest_file)}")
```

**Expected Result:** File still exists and can be loaded! ✅

---

## Test 4: Simulated GDAL Process (3 minutes)

### Step 1: Start Simulated Process with Logging
```python
import time
import logging
import os
from datetime import datetime

# Setup logging
log_dir = '/mnt/data/logs'
os.makedirs(log_dir, exist_ok=True)
log_file = f"{log_dir}/ssh_test_{datetime.now():%Y%m%d_%H%M%S}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

logger.info("="*60)
logger.info("SSH Disconnect Test - Simulated GDAL Process")
logger.info(f"Log file: {log_file}")
logger.info("="*60)

start = time.time()

for i in range(20):  # 20 iterations x 10 seconds = ~3 minutes
    logger.info(f"Processing item {i+1}/20 ({(i+1)/20*100:.0f}%)")
    time.sleep(10)

elapsed = time.time() - start
logger.info("="*60)
logger.info(f"✅ Process Complete! Time: {elapsed:.1f}s")
logger.info("="*60)

print(f"\nLog saved to: {log_file}")
```

### Step 2: Disconnect After 5 Iterations
1. Run the cell
2. Wait for 5 iterations (~50 seconds)
3. **Close Cursor/disconnect SSH**
4. Wait 2 minutes

### Step 3: Reconnect and Check
```bash
ssh -L 8888:localhost:8888 user@your-vm-ip
```

**Expected Results:**
- Cell shows completed OR still running
- You see iterations 10+ (proving it continued)
- Log file contains all iterations

**Check log file:**
```python
import glob

# Find latest log
log_files = glob.glob('/mnt/data/logs/ssh_test_*.log')
latest_log = max(log_files, key=os.path.getctime)

print(f"Reading: {os.path.basename(latest_log)}\n")
with open(latest_log, 'r') as f:
    print(f.read())
```

---

## Troubleshooting: If Kernel Dies

### Check if Container Restarted
```bash
# From VM
docker inspect gis_jupyter_dev --format='Started: {{.State.StartedAt}} | RestartCount: {{.RestartCount}}'

# If StartedAt changed or RestartCount > 0, container was restarted!
```

### Common Causes of Container Restart:
1. ❌ Manual restart: `docker restart gis_jupyter_dev`
2. ❌ Docker compose restart: `docker-compose restart`
3. ❌ Out of memory (OOM kill)
4. ❌ Container crash
5. ❌ VM reboot

### Check Container Logs for Restart Reason:
```bash
docker logs gis_jupyter_dev --since '2 hours ago' | grep -i "killed\|oom\|error\|exit"
```

---

## Success Criteria

### ✅ PASS Conditions:
1. Variables persist after SSH disconnect/reconnect
2. Long-running cells continue executing while disconnected
3. Cell shows progress that occurred during disconnect
4. Files saved to /mnt/data persist
5. Logs show continuous operation
6. Container StartedAt time doesn't change

### ❌ FAIL Conditions:
1. Variables are lost (kernel died)
2. Cell restarts from beginning
3. Container StartedAt time changes (container restarted)
4. RestartCount increases

---

## What We're Testing vs What We're NOT Testing

### ✅ What This Tests:
- **SSH tunnel disconnect** doesn't affect Jupyter
- Kernels survive SSH reconnection
- Processes continue independently
- Web interface can be resumed

### ❌ What This Doesn't Test:
- Container restart (this WILL kill kernels - by design)
- VM reboot (container will restart - kernels lost)
- OOM situation (container may be killed)

---

## Quick Reference: Expected Behavior

| Action | Container Status | Kernel Status | Variables | Running Processes |
|--------|------------------|---------------|-----------|-------------------|
| **SSH Disconnect** | ✅ Running | ✅ Alive | ✅ Persist | ✅ Continue |
| **Close Browser** | ✅ Running | ✅ Alive | ✅ Persist | ✅ Continue |
| **SSH Reconnect** | ✅ Running | ✅ Alive | ✅ Accessible | ✅ Resume View |
| Container Restart | 🔄 Restarted | ❌ Died | ❌ Lost | ❌ Stopped |
| VM Reboot | 🔄 Restarted | ❌ Died | ❌ Lost | ❌ Stopped |

---

## After Testing

### If All Tests Pass ✅
Your setup is working perfectly! SSH disconnect has no effect on Jupyter.

### If Tests Fail ❌
Check:
1. Did container restart? (check StartedAt time)
2. Docker logs for errors
3. Memory usage (might be OOM)
4. Confirm `restart: unless-stopped` in docker-compose.dev.yml

---

## Pro Tip: Monitor During Test

In a separate SSH session to the VM (without port forwarding):

```bash
# Terminal 1: Watch container status
watch -n 2 'docker stats gis_jupyter_dev --no-stream'

# Terminal 2: Follow logs
docker logs -f gis_jupyter_dev | grep -v "GET /api"

# Terminal 3: Watch processes
watch -n 5 'docker exec gis_jupyter_dev ps aux | grep python'
```

This lets you see that everything keeps running even when your Cursor SSH is disconnected!

---

## Ready to Test?

1. Make sure container is running and hasn't been restarted recently
2. Note the container StartedAt time
3. Run Test 1 (simplest - 2 minutes)
4. Then try Test 2 (most thorough - 10 minutes)

Good luck! 🚀




