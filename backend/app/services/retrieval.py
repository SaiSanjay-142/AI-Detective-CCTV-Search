import json, logging
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import Action, Detection, Frame, ObjectObservation, ObjectRelationship, PersonAttribute, Track
from .query_parser import ParsedQuery
log=logging.getLogger(__name__)

def _attributes(attr):
    return None if not attr else {"gender":attr.gender,"upper_type":attr.upper_type,"upper_color":attr.upper_color,"lower_type":attr.lower_type,"lower_color":attr.lower_color,"accessories":json.loads(attr.accessories),"objects_held":json.loads(attr.objects_held)}

def _object_only(db, ids, parsed):
    rows=db.execute(select(ObjectObservation,Frame).join(Frame,ObjectObservation.frame_id==Frame.id).where(ObjectObservation.video_id.in_(ids),ObjectObservation.label==parsed.object_class).order_by(Frame.timestamp)).all()
    return [{"video_id":obj.video_id,"track_id":None,"matched_object_id":obj.id,"object":{"id":obj.id,"class":obj.label,"bbox":[obj.x1,obj.y1,obj.x2,obj.y2],"confidence":obj.confidence},"event":f"{obj.label} detected","relationship":None,"start_time":frame.timestamp,"end_time":frame.timestamp,"evidence_start":max(0,frame.timestamp-3),"evidence_end":frame.timestamp+4,"evidence_timestamp":frame.timestamp,"evidence_frame_id":frame.id,"evidence":{"frame_id":frame.id,"bbox":[obj.x1,obj.y1,obj.x2,obj.y2],"confidence":obj.confidence},"match_reasons":[f"YOLO detected {obj.label} in this exact frame"],"confidence":obj.confidence,"score":obj.confidence} for obj,frame in rows]

def search(db: Session, owner_video_ids: list[int], parsed: ParsedQuery, video_id: int | None = None) -> list[dict]:
    ids=[video_id] if video_id else owner_video_ids
    if not ids:return []
    if parsed.subject_class=="object": return _object_only(db,ids,parsed)
    results=[]
    for track in db.execute(select(Track).where(Track.video_id.in_(ids))).scalars():
        attr=db.execute(select(PersonAttribute).where(PersonAttribute.video_id==track.video_id,PersonAttribute.track_id==track.track_id)).scalars().first()
        actions=db.execute(select(Action).where(Action.video_id==track.video_id,Action.track_id==track.track_id)).scalars().all()
        reasons=[]; score=0
        mismatched=False
        for expected,actual,label in [(parsed.gender,attr.gender if attr else None,"Gender"),(parsed.upper_type,attr.upper_type if attr else None,"Upper clothing"),(parsed.upper_color,attr.upper_color if attr else None,"Upper clothing colour"),(parsed.lower_type,attr.lower_type if attr else None,"Lower clothing"),(parsed.lower_color,attr.lower_color if attr else None,"Lower clothing colour")]:
            if expected and actual!=expected: mismatched=True; break
            if expected: reasons.append(f"{label}: {actual}");score+=1
        if mismatched: continue
        if parsed.start_seconds is not None and track.last_timestamp<parsed.start_seconds: continue
        if parsed.end_seconds is not None and track.first_timestamp>parsed.end_seconds: continue
        # Kinetics labels are more specific (for example "walking the dog");
        # query actions are canonical prefixes, never a fabricated classifier label.
        action_segments=[a for a in actions if parsed.action in a.action] if parsed.action else []
        if parsed.action and not action_segments: continue
        if parsed.action: reasons.append(f"Action: {parsed.action}");score+=1
        relation_rows=[]
        if parsed.object_class:
            relation_rows=db.execute(select(ObjectRelationship,ObjectObservation,Detection,Frame).join(ObjectObservation,ObjectRelationship.object_id==ObjectObservation.id).join(Detection,ObjectRelationship.person_detection_id==Detection.id).join(Frame,ObjectRelationship.frame_id==Frame.id).where(ObjectRelationship.video_id==track.video_id,Detection.track_id==track.track_id,ObjectObservation.label==parsed.object_class).order_by(Frame.timestamp)).all()
            if not relation_rows: continue
            reasons.append(f"{parsed.object_class} measured near this person in the same frame(s)");score+=1
        if relation_rows:
            rel,obj,det,frame=max(relation_rows,key=lambda r:r[0].score)
            start=min(r[3].timestamp for r in relation_rows); end=max(r[3].timestamp for r in relation_rows)
            if parsed.action:
                compatible=[a for a in action_segments if a.end_timestamp>=start and a.start_timestamp<=end]
                if not compatible: continue
                start=max(start,compatible[0].start_timestamp);end=min(end,compatible[0].end_timestamp)
            segments=[(start,end,rel.score,frame,det,obj,rel)]
        elif action_segments:
            segments=[(a.start_timestamp,a.end_timestamp,a.confidence,None,None,None,None) for a in action_segments]
        else:
            pair=db.execute(select(Detection,Frame).join(Frame,Detection.frame_id==Frame.id).where(Detection.video_id==track.video_id,Detection.track_id==track.track_id).order_by(Frame.timestamp)).first()
            if not pair: continue
            segments=[(track.first_timestamp,track.last_timestamp,attr.confidence if attr else 0,pair[1],pair[0],None,None)]
        for start,end,confidence,frame,det,obj,rel in segments:
            if frame is None:
                pair=db.execute(select(Detection,Frame).join(Frame,Detection.frame_id==Frame.id).where(Detection.video_id==track.video_id,Detection.track_id==track.track_id,Frame.timestamp>=start,Frame.timestamp<=end).order_by(Frame.timestamp)).first(); det,frame=pair if pair else (None,None)
            timestamp=frame.timestamp if frame else (start+end)/2
            results.append({"video_id":track.video_id,"track_id":track.track_id,"matched_object_id":obj.id if obj else None,"event":f"person associated with {obj.label}" if obj else (parsed.action or "matching person"),"requested_relationship":parsed.relationship,"relationship":"associated_with" if obj else None,"relationship_score":rel.score if rel else None,"start_time":start,"end_time":end,"evidence_start":max(0,start-3),"evidence_end":end+4,"duration":max(0,end-start),"evidence_timestamp":timestamp,"evidence_frame_id":frame.id if frame else None,"evidence":None if not det else {"frame_id":det.frame_id,"bbox":[det.x1,det.y1,det.x2,det.y2],"confidence":det.confidence},"object":None if not obj else {"id":obj.id,"class":obj.label,"bbox":[obj.x1,obj.y1,obj.x2,obj.y2],"confidence":obj.confidence},"attributes":_attributes(attr),"actions":[{"action":a.action,"confidence":a.confidence,"start":a.start_timestamp,"end":a.end_timestamp} for a in actions],"match_reasons":reasons,"confidence":confidence,"score":score+confidence+min(track.detection_count/100,1)})
    log.info("[SEARCH] parsed=%s results=%s",parsed.dict(),len(results))
    return sorted(results,key=lambda r:r["score"],reverse=True)
