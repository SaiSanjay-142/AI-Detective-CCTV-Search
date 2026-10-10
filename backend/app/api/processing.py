from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import ProcessingJob, Video
from ..security import current_user
router=APIRouter(prefix="/api/jobs",tags=["processing"])
@router.get("/{job_id}")
@router.get("/{job_id}/progress")
def progress(job_id:int,db:Session=Depends(get_db),user=Depends(current_user)):
    job=db.get(ProcessingJob,job_id); video=db.get(Video,job.video_id) if job else None
    if not job or not video or video.owner_id!=user.id: raise HTTPException(404,"Job not found")
    return {"job_id":job.id,"video_id":job.video_id,"status":job.status,"stage":job.stage,"progress":job.progress,"detail":job.detail,"error":job.error}

