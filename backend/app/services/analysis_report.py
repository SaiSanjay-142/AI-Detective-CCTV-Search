"""Printable, evidence-oriented post-processing report for an analysed video."""
import json
from collections import defaultdict
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from ..models import Action, ObjectObservation, ObjectRelationship, PersonAttribute, Track, Video

def build(db: Session, video: Video) -> dict:
    objects=db.execute(select(ObjectObservation.label,func.count(ObjectObservation.id),func.avg(ObjectObservation.confidence)).where(ObjectObservation.video_id==video.id).group_by(ObjectObservation.label).order_by(func.count(ObjectObservation.id).desc())).all()
    attributes={item.track_id:item for item in db.execute(select(PersonAttribute).where(PersonAttribute.video_id==video.id)).scalars()}
    actions=defaultdict(list)
    for item in db.execute(select(Action).where(Action.video_id==video.id).order_by(Action.start_timestamp)).scalars():
        actions[item.track_id].append({"action":item.action,"confidence":round(item.confidence,3),"start":item.start_timestamp,"end":item.end_timestamp})
    relations=defaultdict(list)
    from ..models import Detection
    rows=db.execute(select(ObjectRelationship, ObjectObservation, Detection).join(ObjectObservation,ObjectRelationship.object_id==ObjectObservation.id).join(Detection,ObjectRelationship.person_detection_id==Detection.id).where(ObjectRelationship.video_id==video.id).order_by(ObjectRelationship.score.desc())).all()
    seen=set()
    for rel,obj,det in rows:
        # Report the strongest evidence for each track/object class rather than a
        # misleading dump of thousands of sampled-frame observations.
        key=(det.track_id,obj.label)
        if key in seen: continue
        seen.add(key)
        relations[det.track_id].append({"object":obj.label,"score":round(rel.score,3),"relationship":rel.relationship})
    people=[]
    for track in db.execute(select(Track).where(Track.video_id==video.id).order_by(Track.track_id)).scalars():
        attr=attributes.get(track.track_id)
        people.append({"track_id":track.track_id,"first_seen":track.first_timestamp,"last_seen":track.last_timestamp,"sampled_observations":track.detection_count,"attributes":None if not attr else {"gender":attr.gender,"upper_clothing":{"type":attr.upper_type,"color":attr.upper_color},"lower_clothing":{"type":attr.lower_type,"color":attr.lower_color},"accessories":json.loads(attr.accessories),"objects_held":json.loads(attr.objects_held),"source":attr.source,"confidence":attr.confidence},"actions":actions[track.track_id],"spatial_relationships":relations[track.track_id]})
    return {"video":{"id":video.id,"filename":video.filename,"duration_seconds":video.duration,"fps":video.fps,"width":video.width,"height":video.height},"summary":{"person_tracks":len(people),"object_observations":sum(row[1] for row in objects),"object_classes":len(objects)},"objects_detected":[{"class":label,"frame_observations":count,"average_confidence":round(float(confidence or 0),3)} for label,count,confidence in objects],"person_tracks":people,"notice":"Model-derived evidence only. Confidence is not a guarantee of identity, gender, clothing colour, or object count. Review the linked evidence/video before using it as a forensic conclusion."}
