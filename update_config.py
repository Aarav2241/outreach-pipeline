import os
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

config_path = "config.py"

if not os.path.exists(config_path):
    print("ERROR: config.py not found! Please run from the outreach-pipeline directory.")
else:
    with open(config_path, "r", encoding="utf-8") as f:
        content = f.read()

    if "APOLLO_API_KEY" not in content:
        with open(config_path, "a", encoding="utf-8") as f:
            f.write('\nAPOLLO_API_KEY = "puCmLGpV3b-3GTDcliuB3Q"\n')
        print("[SUCCESS] Successfully added APOLLO_API_KEY to config.py!")
    else:
        print("[SUCCESS] APOLLO_API_KEY is already present in config.py.")
