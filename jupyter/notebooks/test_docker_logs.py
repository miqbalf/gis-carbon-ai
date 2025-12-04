#!/usr/bin/env python3
"""
Test script to determine which output methods work with docker compose logs -f jupyter

Run this script and check: docker compose logs -f jupyter
See which TEST methods actually appear in Docker logs.
"""

import sys
import time
from datetime import datetime

print("\n" + "="*60)
print("TESTING DOCKER LOGS OUTPUT METHODS")
print("="*60)
print("Check: docker compose logs -f jupyter")
print("="*60 + "\n")

# Test 1: Direct sys.stderr.write
print("\n[TEST 1] Direct sys.stderr.write:")
sys.stderr.write("TEST 1: Direct stderr write - should appear in docker logs\n")
sys.stderr.flush()
time.sleep(0.5)

# Test 2: Python logging to stderr
print("\n[TEST 2] Python logging to stderr:")
import logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)
logger.info("TEST 2: Python logger to stderr - should appear in docker logs")
time.sleep(0.5)

# Test 3: Print with file=sys.stderr
print("\n[TEST 3] Print to stderr:")
print("TEST 3: Print to stderr", file=sys.stderr, flush=True)
time.sleep(0.5)

# Test 4: Redirect stdout to stderr
print("\n[TEST 4] Redirected stdout:")
original_stdout = sys.stdout
sys.stdout = sys.stderr
print("TEST 4: Print after stdout redirect - should appear in docker logs")
sys.stdout.flush()
sys.stdout = original_stdout  # Restore
time.sleep(0.5)

# Test 5: Builtin print patching
print("\n[TEST 5] Patched builtin print:")
import builtins
_orig_print = builtins.print
def stderr_print(*args, **kwargs):
    kwargs.setdefault('file', sys.stderr)
    kwargs.setdefault('flush', True)
    _orig_print(*args, **kwargs)
builtins.print = stderr_print
print("TEST 5: Patched print - should appear in docker logs")
builtins.print = _orig_print  # Restore
time.sleep(0.5)

# Test 6: Write to /proc/1/fd/2 (container's stderr)
print("\n[TEST 6] Direct container stderr:")
try:
    with open('/proc/1/fd/2', 'w') as f:
        f.write("TEST 6: Direct container stderr write - should appear in docker logs\n")
        f.flush()
except Exception as e:
    print(f"TEST 6 failed: {e}")
time.sleep(0.5)

# Test 7: Multiple writes
print("\n[TEST 7] Multiple stderr writes:")
for i in range(3):
    msg = f"TEST 7.{i+1}: Multiple stderr write {i+1}/3 - should appear in docker logs\n"
    sys.stderr.write(msg)
    sys.stderr.flush()
    time.sleep(0.2)

# Test 8: Using os.write to stderr file descriptor
print("\n[TEST 8] os.write to stderr FD:")
import os
try:
    os.write(2, b"TEST 8: os.write to stderr FD (2) - should appear in docker logs\n")
except Exception as e:
    print(f"TEST 8 failed: {e}")
time.sleep(0.5)

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)
print("Now check: docker compose logs -f jupyter")
print("Look for lines starting with 'TEST 1:', 'TEST 2:', etc.")
print("="*60 + "\n")

