"""Local VideoMAE adapter; it never manufactures an action when no compatible model exists."""
from pathlib import Path
from PIL import Image
from ..config import get_settings

class ActionRecognizer:
    def __init__(self): self.model=self.processor=None
    def available(self) -> bool:
        path=Path(get_settings().action_model_path)
        return bool(get_settings().action_model_path and path.exists() and (path / "config.json").is_file())
    def _load(self):
        if self.model is not None:return
        if not self.available(): raise RuntimeError("Action recognition model unavailable.")
        from transformers import AutoImageProcessor, VideoMAEForVideoClassification
        import torch
        path=get_settings().action_model_path
        self.processor=AutoImageProcessor.from_pretrained(path, local_files_only=True)
        options={"local_files_only":True}
        if get_settings().resolved_device=="cuda": options["torch_dtype"]=torch.float16
        self.model=VideoMAEForVideoClassification.from_pretrained(path, **options)
        self.model.to(get_settings().resolved_device).eval()
        if not getattr(self.model.config,"id2label",None): raise RuntimeError("VideoMAE checkpoint has no action label mapping.")
    def recognize(self, frames: list[Path]) -> dict:
        """Classify one temporal window and return only the checkpoint's own label."""
        self._load()
        import torch
        images=[Image.open(frame).convert("RGB") for frame in frames]
        inputs=self.processor(images, return_tensors="pt").to(get_settings().resolved_device)
        if get_settings().resolved_device=="cuda": inputs["pixel_values"]=inputs["pixel_values"].half()
        with torch.inference_mode(): logits=self.model(**inputs).logits[0]
        confidence,index=torch.softmax(logits,dim=-1).max(dim=-1)
        return {"action":str(self.model.config.id2label[int(index)]).lower(),"confidence":float(confidence)}
