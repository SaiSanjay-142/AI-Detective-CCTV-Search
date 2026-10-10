from pathlib import Path
import logging
import torch
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .config import get_settings
from .database import Base, engine
from .api import auth, processing, search, videos
settings=get_settings(); app=FastAPI(title=settings.app_name,version="0.1.0")
log=logging.getLogger(__name__)
app.add_middleware(CORSMiddleware,allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
@app.on_event("startup")
def startup():
    Base.metadata.create_all(engine)
    for x in [settings.upload_dir,settings.frame_dir,settings.crop_dir,settings.result_dir]: settings.directory(x)
    if torch.cuda.is_available():
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
        torch.backends.cudnn.benchmark = True
    log.info("[GPU] configured_device=%s resolved_device=%s cuda_available=%s gpu=%s",settings.device,settings.resolved_device,torch.cuda.is_available(),torch.cuda.get_device_name(0) if torch.cuda.is_available() else "none")
app.include_router(auth.router);app.include_router(videos.router);app.include_router(processing.router);app.include_router(search.router)
@app.get("/api/health")
def health(): return {"name":settings.app_name,"configured_device":settings.device,"device":settings.resolved_device,"cuda_available":torch.cuda.is_available(),"gpu":torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,"fp16_support":torch.cuda.is_available(),"pphuman_enabled":settings.pphuman_enabled,"pphuman_model_dir":settings.pphuman_model_dir,"gemini_enabled":settings.gemini_enabled and bool(settings.gemini_api_key),"gemini_model":settings.gemini_model}
