import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import EvidenceVideo, SearchQuery, Video
from ..schemas import SearchIn
from ..security import current_user
from ..services.query_parser import parse_query
from ..services.gemini_query import answer, interpret
from ..services.retrieval import search
from ..services.result_video import generate
router=APIRouter(prefix="/api",tags=["search"])
@router.post("/search")
def find(data:SearchIn,db:Session=Depends(get_db),user=Depends(current_user)):
    if data.video_id:
        video=db.get(Video,data.video_id)
        if not video or video.owner_id!=user.id: raise HTTPException(404,"Video not found")
    ids=[v.id for v in db.query(Video).filter_by(owner_id=user.id)] ; parsed,llm=interpret(data.query)
    entry=SearchQuery(owner_id=user.id,text=data.query,parsed_json=json.dumps(parsed.dict())); db.add(entry);db.commit();db.refresh(entry)
    results=search(db,ids,parsed,data.video_id)
    videos={v.id:v for v in db.query(Video).filter(Video.id.in_({r['video_id'] for r in results})).all()} if results else {}
    for result in results:
        video=videos[result["video_id"]]
        result["video"]={"id":video.id,"filename":video.filename,"duration":video.duration,"url":f"/api/videos/{video.id}/file"}
        result["evidence_end"]=min(video.duration,result["evidence_end"])
        params=[]
        if result.get("track_id") is not None: params.append(f"track_id={result['track_id']}")
        if result.get("matched_object_id") is not None: params.append(f"object_id={result['matched_object_id']}")
        # API clients already use the /api base URL; keep this relative to it so
        # the frontend cannot accidentally request /api/api/frames/….
        result["frame_url"]=f"/frames/{result['evidence_frame_id']}/evidence?{'&'.join(params)}" if result.get("evidence_frame_id") else None
    primary=results[0] if results else None
    return {"search_id":entry.id,"parsed_query":parsed.dict(),"query_interpreter":llm,"answer":answer(data.query,primary,results,llm.get("intent","find")),"result_count":len(results),"primary_evidence":primary}
@router.get("/search/{search_id}")
def saved(search_id:int,db:Session=Depends(get_db),user=Depends(current_user)):
    s=db.get(SearchQuery,search_id)
    if not s or s.owner_id!=user.id: raise HTTPException(404,"Search not found")
    parsed=parse_query(s.text); ids=[v.id for v in db.query(Video).filter_by(owner_id=user.id)]
    return {"search_id":s.id,"query":s.text,"parsed_query":parsed.dict(),"results":search(db,ids,parsed)}
@router.post("/results/{video_id}/{track_id}/generate-video")
def evidence(video_id:int,track_id:int,db:Session=Depends(get_db),user=Depends(current_user)):
    video=db.get(Video,video_id)
    if not video or video.owner_id!=user.id: raise HTTPException(404,"Video not found")
    path=generate(db,video,track_id); record=EvidenceVideo(video_id=video_id,track_id=track_id,path=str(path));db.add(record);db.commit();db.refresh(record)
    return {"evidence_id":record.id,"url":f"/api/results/{record.id}/video"}
@router.get("/results/{evidence_id}/video")
def evidence_file(evidence_id:int,db:Session=Depends(get_db),user=Depends(current_user)):
    item=db.get(EvidenceVideo,evidence_id); video=db.get(Video,item.video_id) if item else None
    if not item or not video or video.owner_id!=user.id: raise HTTPException(404,"Evidence video not found")
    return FileResponse(item.path,media_type="video/mp4",filename=Path(item.path).name)
