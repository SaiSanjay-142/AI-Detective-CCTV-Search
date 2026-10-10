import shutil, uuid
from pathlib import Path
import cv2
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from html import escape
from sqlalchemy.orm import Session
from ..config import get_settings
from ..database import SessionLocal, get_db
from ..models import Detection, Frame, ObjectObservation, ProcessingJob, Video
from ..security import current_user
from ..services.video_processor import process_job
from ..services.event_feed import suggestions
from ..services.analysis_report import build as build_report
router=APIRouter(prefix="/api", tags=["videos"]); ALLOWED={".mp4",".avi",".mov",".mkv"}
def owned(db,user,video_id):
    v=db.get(Video,video_id)
    if not v or v.owner_id!=user.id: raise HTTPException(404,"Video not found")
    return v
@router.post("/videos/upload")
def upload(file: UploadFile=File(...), db:Session=Depends(get_db), user=Depends(current_user)):
    suffix=Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED: raise HTTPException(415,"Supported video formats: MP4, AVI, MOV, MKV")
    name=f"{uuid.uuid4().hex}{suffix}"; target=get_settings().directory(get_settings().upload_dir)/name
    with target.open("wb") as out: shutil.copyfileobj(file.file,out)
    if target.stat().st_size>get_settings().max_upload_mb*1024*1024: target.unlink(); raise HTTPException(413,"Upload exceeds configured size limit")
    cap=cv2.VideoCapture(str(target))
    if not cap.isOpened(): target.unlink(); raise HTTPException(422,"File is not a readable video")
    fps=cap.get(cv2.CAP_PROP_FPS) or 0; frames=cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0; width=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); height=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)); cap.release()
    v=Video(owner_id=user.id,filename=Path(file.filename or name).name,stored_path=str(target),fps=fps,duration=frames/fps if fps else 0,width=width,height=height); db.add(v); db.commit(); db.refresh(v)
    return {"id":v.id,"filename":v.filename,"duration":v.duration,"fps":v.fps,"width":v.width,"height":v.height}
@router.get("/videos")
def videos(db:Session=Depends(get_db),user=Depends(current_user)):
    return [{"id":v.id,"filename":v.filename,"duration":v.duration,"fps":v.fps,"created_at":v.created_at} for v in db.query(Video).filter_by(owner_id=user.id).order_by(Video.id.desc())]
@router.get("/videos/{video_id}")
def video(video_id:int,db:Session=Depends(get_db),user=Depends(current_user)):
    v=owned(db,user,video_id); return {"id":v.id,"filename":v.filename,"duration":v.duration,"fps":v.fps,"width":v.width,"height":v.height}
@router.get("/videos/{video_id}/events")
def events(video_id:int,db:Session=Depends(get_db),user=Depends(current_user)):
    v=owned(db,user,video_id)
    return {"video_id":v.id,"video":{"filename":v.filename,"duration":v.duration},"suggestions":suggestions(db,v)}
@router.get("/videos/{video_id}/report")
def report(video_id:int,db:Session=Depends(get_db),user=Depends(current_user)):
    return build_report(db,owned(db,user,video_id))
@router.get("/videos/{video_id}/report/print",response_class=HTMLResponse)
def printable_report(video_id:int,db:Session=Depends(get_db),user=Depends(current_user)):
    data=build_report(db,owned(db,user,video_id)); video=data["video"]
    objects="".join(f"<tr><td>{escape(row['class'])}</td><td>{row['frame_observations']}</td><td>{row['average_confidence']:.3f}</td></tr>" for row in data["objects_detected"]) or "<tr><td colspan='3'>No non-person object observations.</td></tr>"
    people="".join(f"<tr><td>{p['track_id']}</td><td>{p['first_seen']:.2f}–{p['last_seen']:.2f}s</td><td>{p['sampled_observations']}</td><td>{escape(json.dumps(p['attributes'] or {'status':'attributes unavailable'}))}</td><td>{escape(json.dumps(p['actions']))}</td><td>{escape(json.dumps(p['spatial_relationships']))}</td></tr>" for p in data["person_tracks"]) or "<tr><td colspan='6'>No person tracks.</td></tr>"
    return HTMLResponse(f"""<!doctype html><html><head><title>Video analysis report</title><style>body{{font:14px Arial;margin:28px;color:#17212b}}table{{width:100%;border-collapse:collapse;margin:14px 0}}th,td{{border:1px solid #aaa;padding:7px;text-align:left;vertical-align:top}}th{{background:#e9eef2}}.notice{{background:#fff4d6;padding:12px}}@media print{{button{{display:none}}}}</style></head><body><button onclick='print()'>Print</button><h1>CCTV Video Analysis Report</h1><p><b>Video:</b> {escape(video['filename'])}<br><b>Duration:</b> {video['duration_seconds']:.2f}s · <b>FPS:</b> {video['fps']:.2f}<br><b>Person tracks:</b> {data['summary']['person_tracks']} · <b>Object observations:</b> {data['summary']['object_observations']}</p><p class='notice'>{escape(data['notice'])}</p><h2>Detected object classes</h2><table><tr><th>Object class</th><th>Frame observations</th><th>Average confidence</th></tr>{objects}</table><h2>Person-track attributes and evidence</h2><table><tr><th>Track</th><th>Observed interval</th><th>Samples</th><th>Qwen attributes</th><th>VideoMAE actions</th><th>Spatial relationships</th></tr>{people}</table></body></html>""")
@router.get("/videos/{video_id}/file")
def stream(video_id:int,db:Session=Depends(get_db),user=Depends(current_user)):
    v=owned(db,user,video_id); return FileResponse(v.stored_path,media_type="video/mp4",filename=v.filename)
@router.get("/frames/{frame_id}/evidence")
def evidence_frame(frame_id:int,track_id:int|None=None,object_id:int|None=None,db:Session=Depends(get_db),user=Depends(current_user)):
    frame=db.get(Frame,frame_id); video=db.get(Video,frame.video_id) if frame else None
    if not frame or not video or video.owner_id!=user.id: raise HTTPException(404,"Evidence frame not found")
    detection=db.query(Detection).filter_by(frame_id=frame_id,track_id=track_id).first() if track_id is not None else None
    obj=db.query(ObjectObservation).filter_by(frame_id=frame_id,id=object_id).first() if object_id is not None else None
    image=cv2.imread(frame.image_path)
    if image is None: raise HTTPException(404,"Stored evidence image not found")
    if detection:
        cv2.rectangle(image,(int(detection.x1),int(detection.y1)),(int(detection.x2),int(detection.y2)),(26,205,157),2)
        cv2.putText(image,f"Track {track_id} | {frame.timestamp:.2f}s",(16,30),cv2.FONT_HERSHEY_SIMPLEX,.7,(26,205,157),2)
    if obj:
        cv2.rectangle(image,(int(obj.x1),int(obj.y1)),(int(obj.x2),int(obj.y2)),(255,178,50),2)
        cv2.putText(image,f"{obj.label} | {frame.timestamp:.2f}s",(16,60),cv2.FONT_HERSHEY_SIMPLEX,.7,(255,178,50),2)
    output=get_settings().directory(get_settings().result_dir)/f"evidence_{frame_id}_{track_id or 'object'}_{object_id or ''}.jpg"
    cv2.imwrite(str(output),image)
    return FileResponse(output,media_type="image/jpeg")
@router.post("/videos/{video_id}/process")
def start(video_id:int,background:BackgroundTasks,db:Session=Depends(get_db),user=Depends(current_user)):
    owned(db,user,video_id); active=db.query(ProcessingJob).filter(ProcessingJob.video_id==video_id,ProcessingJob.status.in_(["queued","processing"])).first()
    if active: return {"job_id":active.id,"status":active.status}
    job=ProcessingJob(video_id=video_id); db.add(job); db.commit(); db.refresh(job); background.add_task(process_job,job.id,SessionLocal); return {"job_id":job.id,"status":"queued"}
