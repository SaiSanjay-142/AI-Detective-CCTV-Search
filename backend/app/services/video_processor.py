from datetime import datetime
import json, logging, time
from pathlib import Path
import cv2
from sqlalchemy.orm import Session
from ..config import get_settings
from ..models import Action, AttributeAudit, Detection, Frame, ObjectObservation, ObjectRelationship, PersonAttribute, ProcessingJob, Track, Video
from .detector import Detector
from .attribute_extractor import AttributeExtractor
from .color_estimator import estimate_clothing_colours
from .pphuman_attribute import PPHumanAttributeExtractor
from .relationships import measure
from .action_recognizer import ActionRecognizer
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger(__name__)
def _update(db: Session, job: ProcessingJob, stage: str, progress: float, detail: str): job.stage, job.progress, job.detail = stage, progress, detail; db.commit()
def process_job(job_id: int, db_factory):
    db: Session = db_factory(); job = db.get(ProcessingJob, job_id)
    try:
        processing_started=time.perf_counter()
        job.status = "processing"; _update(db, job, "opening_video", 2, "Validating video")
        video = db.get(Video, job.video_id)
        # Keep a small per-video/per-track cache before derived rows are replaced.
        # It is used only during a reprocess of the same footage; searches never invoke Qwen.
        cached_attributes={a.track_id:{"gender":a.gender,"upper_type":a.upper_type,"upper_color":a.upper_color,"lower_type":a.lower_type,"lower_color":a.lower_color,"accessories":a.accessories,"objects_held":a.objects_held,"confidence":a.confidence} for a in db.query(PersonAttribute).filter_by(video_id=video.id).all()}
        # A deliberate re-run replaces only this video's derived metadata.
        # Original uploaded footage is preserved.
        db.query(Action).filter_by(video_id=video.id).delete()
        db.query(ObjectRelationship).filter_by(video_id=video.id).delete()
        db.query(ObjectObservation).filter_by(video_id=video.id).delete()
        db.query(AttributeAudit).filter_by(video_id=video.id).delete()
        db.query(PersonAttribute).filter_by(video_id=video.id).delete()
        db.query(Detection).filter_by(video_id=video.id).delete()
        db.query(Track).filter_by(video_id=video.id).delete()
        db.query(Frame).filter_by(video_id=video.id).delete()
        db.commit()
        cap = cv2.VideoCapture(video.stored_path)
        if not cap.isOpened(): raise ValueError("OpenCV could not open this video")
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0; total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0); video.fps = fps; video.duration = total / fps; video.width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); video.height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)); db.commit()
        log.info("[VIDEO] id=%s duration=%.2fs fps=%.3f frames=%s size=%sx%s", video.id, video.duration, fps, total, video.width, video.height)
        settings=get_settings(); every = max(1, round(fps / settings.frame_sample_fps)); detector = Detector(); seen: dict[int, list[tuple[float, float]]] = {}; candidates: dict[int, list[dict]] = {}
        frame_dir = get_settings().directory(get_settings().frame_dir) / str(video.id); crop_dir = get_settings().directory(get_settings().crop_dir) / str(video.id); frame_dir.mkdir(parents=True, exist_ok=True); crop_dir.mkdir(parents=True, exist_ok=True)
        n = 0
        while True:
            ok, image = cap.read()
            if not ok: break
            if n % every: n += 1; continue
            timestamp = n / fps; image_path = frame_dir / f"{n:08d}.jpg"; cv2.imwrite(str(image_path), image)
            frame = Frame(video_id=video.id, frame_number=n, timestamp=timestamp, image_path=str(image_path)); db.add(frame); db.flush()
            _update(db, job, "detection_and_tracking", 5 + 70 * n / max(total, 1), f"YOLOv8 + ByteTrack frame {n}/{total}")
            person_detections=[]
            for item in detector.track(image_path):
                x1,y1,x2,y2 = [max(0, int(v)) for v in item["bbox"]]; det = Detection(frame_id=frame.id, video_id=video.id, track_id=item["track_id"], label="person", confidence=item["confidence"], x1=x1,y1=y1,x2=x2,y2=y2); db.add(det)
                person_detections.append((det, [x1,y1,x2,y2]))
                seen.setdefault(item["track_id"], []).append((timestamp, item["confidence"]))
                width,height=x2-x1,y2-y1
                if item["confidence"] >= settings.qwen_min_confidence and min(width,height) >= settings.qwen_min_crop_pixels:
                    # Confidence and visible crop area are cheap, deterministic quality signals.
                    candidates.setdefault(item["track_id"],[]).append({"confidence":item["confidence"],"area":width*height,"frame":n,"image_path":image_path,"bbox":(x1,y1,x2,y2)})
            db.flush()
            objects=[]
            for item in detector.objects(image_path):
                x1,y1,x2,y2=[max(0, int(v)) for v in item["bbox"]]
                obj=ObjectObservation(frame_id=frame.id, video_id=video.id, label=item["label"], confidence=item["confidence"], x1=x1,y1=y1,x2=x2,y2=y2); db.add(obj); objects.append((obj,[x1,y1,x2,y2]))
            db.flush()
            for person, person_box in person_detections:
                for obj, object_box in objects:
                    relation=measure(person_box, object_box)
                    if relation: db.add(ObjectRelationship(video_id=video.id, frame_id=frame.id, person_detection_id=person.id, object_id=obj.id, **relation))
            log.info("[YOLO] frame=%s persons=%s objects=%s", n, len(person_detections), len(objects))
            db.commit(); n += 1
        cap.release(); _update(db, job, "indexing_tracks", 78, "Writing track metadata")
        for track_id, observations in seen.items(): db.add(Track(video_id=video.id, track_id=track_id, first_timestamp=observations[0][0], last_timestamp=observations[-1][0], detection_count=len(observations)))
        db.commit()
        log.info("[BYTETRACK] tracks=%s ids=%s", len(seen), sorted(seen))
        _update(db, job, "attributes", 82, "Selecting representative person crops for attribute analysis")
        warnings=[]
        candidate_count=sum(len(items) for items in candidates.values()); qwen_calls=cache_hits=cache_misses=0; qwen_seconds=0.0
        # Colour is measured locally once from each track's clearest crop.  This
        # takes milliseconds, works on CPU/GPU installations alike, and allows
        # colour search to remain available if an optional attribute model fails.
        colour_by_track: dict[int, dict] = {}
        if settings.attribute_color_enabled:
            for track_id, track_candidates in candidates.items():
                candidate=max(track_candidates,key=lambda item:item["confidence"] * item["area"])
                image=cv2.imread(str(candidate["image_path"])); x1,y1,x2,y2=candidate["bbox"]
                person=image[y1:y2,x1:x2] if image is not None else None
                colour_by_track[track_id]=estimate_clothing_colours(person)
        pphuman=None
        if settings.pphuman_enabled:
            pphuman=PPHumanAttributeExtractor()
            if not pphuman.available():
                warnings.append(f"PP-Human attributes unavailable: {pphuman.reason}")
                log.warning("[PP-HUMAN] %s", pphuman.reason)
                pphuman=None
        if candidates and settings.qwen_enabled:
            try:
                extractor=None
                track_items=sorted(candidates.items(),key=lambda item:max(c["confidence"]*c["area"] for c in item[1]),reverse=True)
                if settings.qwen_max_tracks: track_items=track_items[:settings.qwen_max_tracks]
                for index, (track_id, track_candidates) in enumerate(track_items, start=1):
                    _update(db, job, "attributes", 83 + 9 * (index - 1) / len(track_items), f"Qwen3-VL attributes for track {index}/{len(track_items)}")
                    cached=cached_attributes.get(track_id)
                    if cached:
                        cache_hits+=1
                        cached={**cached}
                        colours=colour_by_track.get(track_id,{})
                        for field in ("upper_color","lower_color"):
                            if colours.get(field) not in (None,"unknown"):
                                cached[field]=colours[field]
                        db.add(PersonAttribute(video_id=video.id,track_id=track_id,source="qwen-cache+crop-colour",**cached)); db.commit(); continue
                    cache_misses+=1
                    if extractor is None:
                        _update(db, job, "attributes", 83, "Loading Qwen3-VL model; this can take several minutes on CPU")
                        extractor=AttributeExtractor(); extractor.ready()
                    # Large, confident crops first; keep frame spacing so selections are not duplicates.
                    selected=[]
                    for candidate in sorted(track_candidates,key=lambda c:c["confidence"]*c["area"],reverse=True):
                        if all(abs(candidate["frame"]-old["frame"]) >= every*10 for old in selected): selected.append(candidate)
                        if len(selected)>=settings.qwen_max_frames_per_track: break
                    parsed=[]
                    try:
                        pphuman_attrs=None
                        for rank,candidate in enumerate(selected):
                            image=cv2.imread(str(candidate["image_path"])); x1,y1,x2,y2=candidate["bbox"]; person=image[y1:y2,x1:x2]
                            if person.size==0: continue
                            pc=crop_dir/f"track_{track_id}_representative_{rank}.jpg"; cv2.imwrite(str(pc),person)
                            if rank == 0 and pphuman is not None:
                                try:
                                    pphuman_attrs, pphuman_scores = pphuman.extract(person)
                                    db.add(AttributeAudit(video_id=video.id,track_id=track_id,raw_response=json.dumps({"provider":"pphuman","attributes":pphuman_attrs,"scores":pphuman_scores})))
                                except Exception as exc:
                                    log.warning("[PP-HUMAN] track=%s failed: %s",track_id,exc)
                            started=time.perf_counter(); attrs,raw=extractor.extract(pc); elapsed=time.perf_counter()-started; qwen_calls+=1; qwen_seconds+=elapsed
                            db.add(AttributeAudit(video_id=video.id,track_id=track_id,raw_response=raw)); parsed.append(attrs)
                        if not parsed: raise ValueError("No usable representative crop")
                        # Highest-quality representative is primary; additional representative calls
                        # are retained in the audit trail and protect against a single bad crop.
                        attrs=parsed[0]
                        colours=colour_by_track.get(track_id,{})
                        # Qwen remains the richer fallback.  PP-Human fills only
                        # fields Qwen explicitly left unknown; crop colour wins
                        # where the local measurement has sufficient evidence.
                        if pphuman_attrs:
                            if attrs.gender == "unknown": attrs.gender=pphuman_attrs["gender"]
                            if attrs.upper_clothing.type == "unknown": attrs.upper_clothing.type=pphuman_attrs["upper_type"]
                            if attrs.lower_clothing.type == "unknown": attrs.lower_clothing.type=pphuman_attrs["lower_type"]
                            attrs.accessories=sorted(set(attrs.accessories + pphuman_attrs["accessories"]))
                            attrs.objects_held=sorted(set(attrs.objects_held + pphuman_attrs["objects_held"]))
                        upper_color=colours.get("upper_color") if colours.get("upper_color") != "unknown" else attrs.upper_clothing.color
                        lower_color=colours.get("lower_color") if colours.get("lower_color") != "unknown" else attrs.lower_clothing.color
                        log.info("[QWEN] track=%s selected=%s parsed=%s",track_id,len(selected),attrs.model_dump())
                        source="qwen3-vl+crop-colour" + ("+pphuman" if pphuman_attrs else "")
                        db.add(PersonAttribute(video_id=video.id, track_id=track_id, gender=attrs.gender, upper_type=attrs.upper_clothing.type, upper_color=upper_color, lower_type=attrs.lower_clothing.type, lower_color=lower_color, accessories=json.dumps(attrs.accessories), objects_held=json.dumps(attrs.objects_held), confidence=max(float(colours.get("confidence",0)), 0.65), source=source)); db.commit()
                    except Exception as exc:
                        raw=getattr(extractor,"last_raw","")
                        db.add(AttributeAudit(video_id=video.id,track_id=track_id,raw_response=raw,parse_error=str(exc))); db.commit()
                        colours=colour_by_track.get(track_id,{})
                        if colours:
                            db.add(PersonAttribute(video_id=video.id,track_id=track_id,gender="unknown",upper_type="unknown",upper_color=colours.get("upper_color","unknown"),lower_type="unknown",lower_color=colours.get("lower_color","unknown"),accessories="[]",objects_held="[]",confidence=float(colours.get("confidence",0)),source="crop-colour")); db.commit()
                        warnings.append(f"Qwen3-VL attributes unavailable for track {track_id}: {exc}"); log.warning("[QWEN] track=%s parsing failed: %s", track_id, exc)
                log.info("[QWEN PERFORMANCE] tracks=%s candidates=%s representative_frames=%s calls=%s cache_hits=%s cache_misses=%s average_seconds=%.2f total_seconds=%.2f",len(track_items),candidate_count,qwen_calls,qwen_calls,cache_hits,cache_misses,qwen_seconds/max(qwen_calls,1),qwen_seconds)
                _update(db, job, "attributes", 92, "Qwen3-VL attribute extraction complete")
            except Exception as exc: warnings.append(f"Qwen3-VL unavailable: {exc}"); log.warning("Attribute stage skipped: %s", exc)
        elif not settings.qwen_enabled:
            # Retain fast, local colour evidence even if the slower VLM is
            # deliberately disabled for throughput.
            for track_id, colours in colour_by_track.items():
                values={"gender":"unknown","upper_type":"unknown","lower_type":"unknown","accessories":[],"objects_held":[]}
                if pphuman is not None:
                    candidate=max(candidates[track_id],key=lambda item:item["confidence"] * item["area"])
                    image=cv2.imread(str(candidate["image_path"])); x1,y1,x2,y2=candidate["bbox"]
                    person=image[y1:y2,x1:x2] if image is not None else None
                    try:
                        values, scores=pphuman.extract(person)
                        db.add(AttributeAudit(video_id=video.id,track_id=track_id,raw_response=json.dumps({"provider":"pphuman","attributes":values,"scores":scores})))
                    except Exception as exc:
                        log.warning("[PP-HUMAN] track=%s failed: %s",track_id,exc)
                db.add(PersonAttribute(video_id=video.id,track_id=track_id,gender=values["gender"],upper_type=values["upper_type"],upper_color=colours.get("upper_color","unknown"),lower_type=values["lower_type"],lower_color=colours.get("lower_color","unknown"),accessories=json.dumps(values["accessories"]),objects_held=json.dumps(values["objects_held"]),confidence=float(colours.get("confidence",0)),source="pphuman+crop-colour" if pphuman is not None else "crop-colour"))
            db.commit()
            warnings.append("Qwen3-VL attributes disabled by QWEN_ENABLED; colour evidence was still indexed.")
        else:
            warnings.append("Qwen3-VL attributes skipped because no track had a sufficiently clear representative crop.")
        _update(db, job, "action_recognition", 94, "Checking VideoMAE-Large action checkpoint")
        recognizer=ActionRecognizer()
        if not recognizer.available():
            warnings.append("Action recognition model unavailable.")
            log.warning("[VIDEOMAE] checkpoint unavailable: %s", get_settings().action_model_path or "ACTION_MODEL_PATH not set")
        else:
            # Per-track sampled crops are temporal windows. A bad/incompatible checkpoint
            # is surfaced as a warning; no synthetic action is inserted into SQLite.
            try:
                window=get_settings().action_window_frames
                for track_id in seen:
                    track_frames=[f for f in db.query(Frame).join(Detection,Detection.frame_id==Frame.id).filter(Detection.video_id==video.id,Detection.track_id==track_id).order_by(Frame.timestamp).all()]
                    for start in range(0,max(0,len(track_frames)-window+1),max(1,get_settings().action_stride)):
                        selected=track_frames[start:start+window]
                        if len(selected)!=window: continue
                        prediction=recognizer.recognize([Path(f.image_path) for f in selected])
                        db.add(Action(video_id=video.id,track_id=track_id,action=prediction["action"],confidence=prediction["confidence"],start_timestamp=selected[0].timestamp,end_timestamp=selected[-1].timestamp))
                        log.info("[VIDEOMAE] track=%s action=%s %.3f %.2f-%.2f",track_id,prediction["action"],prediction["confidence"],selected[0].timestamp,selected[-1].timestamp)
                db.commit()
            except Exception as exc:
                warnings.append(f"Action recognition model unavailable: {exc}")
                log.warning("[VIDEOMAE] action stage failed safely: %s",exc)
        log.info("[PROCESSING PERFORMANCE] video_id=%s total_seconds=%.2f",video.id,time.perf_counter()-processing_started)
        job.status = "completed_with_warnings" if warnings else "completed"; job.error = " ".join(warnings) if warnings else None; job.completed_at=datetime.utcnow(); _update(db, job, "complete", 100, "Processing finished")
    except Exception as exc:
        log.exception("Processing failed"); job.status="failed"; job.error=str(exc); job.stage="failed"; db.commit()
    finally: db.close()
