from pathlib import Path
import cv2
from sqlalchemy.orm import Session
from ..config import get_settings
from ..models import Detection, Video
def generate(db: Session, video: Video, track_id: int) -> Path:
    source=cv2.VideoCapture(video.stored_path)
    if not source.isOpened(): raise ValueError("Unable to open original video")
    fps=source.get(cv2.CAP_PROP_FPS) or 25; w=int(source.get(cv2.CAP_PROP_FRAME_WIDTH)); h=int(source.get(cv2.CAP_PROP_FRAME_HEIGHT))
    output=get_settings().directory(get_settings().result_dir)/f"video_{video.id}_track_{track_id}.mp4"
    writer=cv2.VideoWriter(str(output),cv2.VideoWriter_fourcc(*"mp4v"),fps,(w,h))
    detections={}
    for d in db.query(Detection).filter_by(video_id=video.id,track_id=track_id): detections.setdefault(d.frame_id,d)
    # Link samples by timestamp because source frame count and extracted frames differ.
    from ..models import Frame
    frame_map={round(f.timestamp,2):d for f,d in ((db.get(Frame,d.frame_id),d) for d in detections.values()) if f}
    index=0
    while True:
        ok, image=source.read()
        if not ok: break
        stamp=round(index/fps,2); d=frame_map.get(stamp)
        if d:
            cv2.rectangle(image,(int(d.x1),int(d.y1)),(int(d.x2),int(d.y2)),(26,205,157),2)
            cv2.putText(image,f"AI DETECTIVE | Track {track_id} | {stamp:.2f}s",(16,30),cv2.FONT_HERSHEY_SIMPLEX,.7,(26,205,157),2)
        writer.write(image); index+=1
    source.release();writer.release();return output

