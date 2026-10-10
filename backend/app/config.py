from functools import lru_cache
from pathlib import Path
import torch
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")
    app_name: str = "AI Detective"
    database_url: str = "sqlite:///./ai_detective.db"
    jwt_secret: str = "development-only-change-me"
    jwt_expire_minutes: int = 480
    yolo_model: str = "yolov8m.pt"
    frame_sample_fps: float = 3.0
    qwen_model: str = "Qwen/Qwen3-VL-2B-Instruct"
    qwen_enabled: bool = True
    qwen_max_frames_per_track: int = 1
    qwen_min_confidence: float = 0.70
    qwen_min_crop_pixels: int = 96
    qwen_max_tracks: int = 0
    qwen_include_context: bool = False
    qwen_max_new_tokens: int = 96
    # PP-Human uses the open-source PaddleDetection person-attribute model.  It is
    # optional because the exported Paddle model must be installed locally first.
    pphuman_enabled: bool = False
    pphuman_model_dir: str = "storage/models/pphuman-person-attribute"
    pphuman_threshold: float = 0.55
    attribute_color_enabled: bool = True
    action_model: str = "VideoMAE-Large"
    action_model_path: str = ""
    action_window_frames: int = 16
    action_stride: int = 8
    device: str = "auto"
    gemini_enabled: bool = False
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"
    upload_dir: str = "storage/uploads"
    frame_dir: str = "storage/frames"
    crop_dir: str = "storage/crops"
    result_dir: str = "storage/results"
    max_upload_mb: int = 1024
    @property
    def root(self) -> Path: return ROOT
    def directory(self, value: str) -> Path:
        path = self.root / value
        path.mkdir(parents=True, exist_ok=True)
        return path
    @property
    def resolved_device(self) -> str:
        return "cuda" if self.device == "auto" and torch.cuda.is_available() else ("cpu" if self.device == "auto" else self.device)

@lru_cache
def get_settings() -> Settings: return Settings()
