"""Report model readiness without downloading large weights."""
from pathlib import Path
import os
print(f"YOLO model: {os.getenv('YOLO_MODEL','yolov8m.pt')} (Ultralytics downloads on first real inference if not cached)")
action=os.getenv('ACTION_MODEL_PATH','')
print(f"VideoMAE action checkpoint: {'available' if action and Path(action).is_file() else 'MISSING - set ACTION_MODEL_PATH to your compatible VideoMAE-Large checkpoint'}")
print(f"Qwen model: {os.getenv('QWEN_MODEL','Qwen/Qwen3-VL-2B-Instruct')} (loaded only during attribute extraction)")
print("No large models were downloaded by this checker.")
