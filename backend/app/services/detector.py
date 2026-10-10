from pathlib import Path
from ..config import get_settings
class Detector:
    """Real Ultralytics YOLO + bundled ByteTrack inference. Model loading is lazy."""
    def __init__(self): self.model = None
    def _model(self):
        if self.model is None:
            try:
                from ultralytics import YOLO
            except ImportError as exc:
                raise RuntimeError("Ultralytics is not installed. Install requirements.txt before processing video.") from exc
            self.model = YOLO(get_settings().yolo_model)
        return self.model
    def track(self, image_path: Path):
        settings=get_settings()
        result = self._model().track(source=str(image_path), persist=True, tracker="bytetrack.yaml", classes=[0], verbose=False, device=settings.resolved_device, half=settings.resolved_device=="cuda")[0]
        boxes = result.boxes
        if boxes is None or boxes.id is None: return []
        xyxy, conf, ids = boxes.xyxy.cpu().tolist(), boxes.conf.cpu().tolist(), boxes.id.int().cpu().tolist()
        return [{"track_id": tid, "label": "person", "confidence": score, "bbox": box} for box, score, tid in zip(xyxy, conf, ids)]
    def objects(self, image_path: Path):
        """Return COCO non-person detections for the sampled frame.

        Person identity remains owned by ByteTrack above; these are deliberately
        frame-level observations so an object ID can never be confused with a
        person track ID.
        """
        settings=get_settings()
        result = self._model().predict(source=str(image_path), classes=None, verbose=False, device=settings.resolved_device, half=settings.resolved_device=="cuda")[0]
        boxes = result.boxes
        if boxes is None: return []
        names = result.names
        output=[]
        for box, confidence, cls in zip(boxes.xyxy.cpu().tolist(), boxes.conf.cpu().tolist(), boxes.cls.int().cpu().tolist()):
            label = str(names[int(cls)]).lower()
            if label == "cell phone": label = "phone"
            if label != "person": output.append({"label": label, "confidence": confidence, "bbox": box})
        return output
