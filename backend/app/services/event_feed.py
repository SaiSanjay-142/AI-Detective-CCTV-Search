"""Evidence-first post-processing event timeline for a single CCTV video."""
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import Action, Detection, Frame, ObjectObservation, ObjectRelationship, PersonAttribute, Track, Video

def _window(video: Video, timestamp: float, start: float | None = None, end: float | None = None):
    return max(0.0, (start if start is not None else timestamp) - 3), min(video.duration, (end if end is not None else timestamp) + 4)

def timeline(db: Session, video: Video) -> list[dict]:
    """Return independently clickable events; every entry has a real stored frame."""
    items=[]
    for track in db.execute(select(Track).where(Track.video_id==video.id)).scalars():
        pair=db.execute(select(Detection,Frame).join(Frame,Detection.frame_id==Frame.id).where(Detection.video_id==video.id,Detection.track_id==track.track_id).order_by(Frame.timestamp)).first()
        if not pair: continue
        det,frame=pair; start,end=_window(video,frame.timestamp,track.first_timestamp,track.last_timestamp)
        items.append({"kind":"track","event":"person detected","video_id":video.id,"track_id":track.track_id,"matched_object_id":None,"evidence_frame_id":frame.id,"evidence_timestamp":frame.timestamp,"start_time":track.first_timestamp,"end_time":track.last_timestamp,"evidence_start":start,"evidence_end":end,"confidence":det.confidence,"match_reasons":[f"ByteTrack person track {track.track_id}",f"Observed in {track.detection_count} sampled frames"]})
    # One representative per class/frame is an evidence event; limit is applied after ranking.
    objects=db.execute(select(ObjectObservation,Frame).join(Frame,ObjectObservation.frame_id==Frame.id).where(ObjectObservation.video_id==video.id).order_by(ObjectObservation.confidence.desc())).all()
    seen=set()
    for obj,frame in objects:
        key=(obj.label,round(frame.timestamp))
        if key in seen: continue
        seen.add(key); start,end=_window(video,frame.timestamp)
        items.append({"kind":"object","event":f"{obj.label} detected","video_id":video.id,"track_id":None,"matched_object_id":obj.id,"evidence_frame_id":frame.id,"evidence_timestamp":frame.timestamp,"start_time":frame.timestamp,"end_time":frame.timestamp,"evidence_start":start,"evidence_end":end,"confidence":obj.confidence,"match_reasons":[f"YOLO detected {obj.label} in this exact frame"]})
    relations=db.execute(select(ObjectRelationship,ObjectObservation,Detection,Frame).join(ObjectObservation,ObjectRelationship.object_id==ObjectObservation.id).join(Detection,ObjectRelationship.person_detection_id==Detection.id).join(Frame,ObjectRelationship.frame_id==Frame.id).where(ObjectRelationship.video_id==video.id).order_by(ObjectRelationship.score.desc())).all()
    seen=set()
    for rel,obj,det,frame in relations:
        key=(det.track_id,obj.label,round(frame.timestamp))
        if key in seen: continue
        seen.add(key); start,end=_window(video,frame.timestamp)
        items.append({"kind":"relationship","event":f"person associated with {obj.label}","video_id":video.id,"track_id":det.track_id,"matched_object_id":obj.id,"evidence_frame_id":frame.id,"evidence_timestamp":frame.timestamp,"start_time":frame.timestamp,"end_time":frame.timestamp,"evidence_start":start,"evidence_end":end,"confidence":rel.score,"relationship":"associated_with","relationship_score":rel.score,"match_reasons":[f"Track {det.track_id} and {obj.label} measured in the same frame",f"Spatial association score: {rel.score:.2f}"]})
    for action in db.execute(select(Action).where(Action.video_id==video.id)).scalars():
        pair=db.execute(select(Detection,Frame).join(Frame,Detection.frame_id==Frame.id).where(Detection.video_id==video.id,Detection.track_id==action.track_id,Frame.timestamp>=action.start_timestamp,Frame.timestamp<=action.end_timestamp).order_by(Frame.timestamp)).first()
        if not pair: continue
        det,frame=pair; start,end=_window(video,frame.timestamp,action.start_timestamp,action.end_timestamp)
        items.append({"kind":"action","event":action.action,"video_id":video.id,"track_id":action.track_id,"matched_object_id":None,"evidence_frame_id":frame.id,"evidence_timestamp":frame.timestamp,"start_time":action.start_timestamp,"end_time":action.end_timestamp,"evidence_start":start,"evidence_end":end,"confidence":action.confidence,"match_reasons":[f"VideoMAE action: {action.action}",f"Track {action.track_id}"]})
    return sorted(items,key=lambda e:(e["evidence_timestamp"],-e["confidence"]))[:100]

def suggestions(db: Session, video: Video, limit: int = 6) -> list[dict]:
    """Small, deduplicated investigator prompts derived from verified metadata.

    This is intentionally not a feed of detections. A relationship must already
    have passed same-frame spatial validation; an action must come from VideoMAE.
    """
    candidates: dict[str, dict] = {}
    # Attribute questions are offered only when the indexed evidence actually
    # contains the relevant non-unknown value.  These prompts are deliberately
    # answerable from the local evidence that Gemini receives after retrieval.
    track_count=db.query(Track).filter_by(video_id=video.id).count()
    if track_count:
        candidates["How many people are in the video?"]={"title":"Count people","query":"How many people are in the video?","kind":"count","confidence":1.0}
    attributes=db.execute(select(PersonAttribute).where(PersonAttribute.video_id==video.id).order_by(PersonAttribute.confidence.desc())).scalars().all()
    for attribute in attributes:
        if attribute.gender in {"male","female"}:
            label="men" if attribute.gender == "male" else "women"
            query=f"How many {label} are in the video?"
            candidates.setdefault(query,{"title":f"Count {label}","query":query,"kind":"attribute_count","confidence":attribute.confidence})
        if attribute.upper_color not in {"unknown",""}:
            query=f"Find people wearing a {attribute.upper_color} top"
            candidates.setdefault(query,{"title":f"People in {attribute.upper_color}","query":query,"kind":"attribute","confidence":attribute.confidence})
        if attribute.lower_color not in {"unknown",""}:
            query=f"Find people wearing {attribute.lower_color} lower clothing"
            candidates.setdefault(query,{"title":f"{attribute.lower_color.title()} lower clothing","query":query,"kind":"attribute","confidence":attribute.confidence})
    relations=db.execute(select(ObjectRelationship,ObjectObservation).join(ObjectObservation,ObjectRelationship.object_id==ObjectObservation.id).where(ObjectRelationship.video_id==video.id).order_by(ObjectRelationship.score.desc())).all()
    labels={"dog":("Person near a dog","Find a person near a dog"),"backpack":("Person with a backpack","Find a person with a backpack"),"handbag":("Person with a handbag","Find a person with a handbag"),"phone":("Person near a phone","Find a person near a phone"),"bicycle":("Person near a bicycle","Find a person near a bicycle"),"car":("Person near a car","Find a person near a car")}
    for rel,obj in relations:
        if obj.label not in labels: continue
        title,query=labels[obj.label]
        candidates.setdefault(query,{"title":title,"query":query,"kind":"relationship","confidence":rel.score})
    actions=db.execute(select(Action).where(Action.video_id==video.id).order_by(Action.confidence.desc())).scalars().all()
    for action in actions:
        label=action.action.lower()
        for token,title,query in [("walk","Person walking","Find people walking"),("runn","Person running","Find people running")]:
            if token in label: candidates.setdefault(query,{"title":title,"query":query,"kind":"action","confidence":action.confidence})
    # Riding is suggested only when the model reports riding AND this same person
    # has a validated bicycle relationship during an overlapping interval.
    for action in actions:
        if "rid" not in action.action.lower(): continue
        bicycle=db.execute(select(ObjectRelationship,Detection,Frame).join(Detection,ObjectRelationship.person_detection_id==Detection.id).join(ObjectObservation,ObjectRelationship.object_id==ObjectObservation.id).join(Frame,ObjectRelationship.frame_id==Frame.id).where(ObjectRelationship.video_id==video.id,Detection.track_id==action.track_id,ObjectObservation.label=="bicycle",Frame.timestamp>=action.start_timestamp,Frame.timestamp<=action.end_timestamp)).first()
        if bicycle: candidates.setdefault("Find a person riding a bicycle",{"title":"Person riding a bicycle","query":"Find a person riding a bicycle","kind":"action_relationship","confidence":min(action.confidence,bicycle[0].score)})
    return sorted(candidates.values(),key=lambda item:(-item["confidence"],item["title"]))[:limit]
