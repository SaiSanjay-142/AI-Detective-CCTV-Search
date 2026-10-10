import json, re
from pathlib import Path
from PIL import Image
from ..config import get_settings
from ..schemas import AttributePayload
PROMPT = """Return ONLY JSON: {"gender":"unknown","upper_clothing":{"type":"unknown","color":"unknown"},"lower_clothing":{"type":"unknown","color":"unknown"},"accessories":[],"objects_held":[],"headwear":"unknown","eyewear":"unknown"}. Analyse only visible CCTV evidence; use unknown if unsure."""
class AttributeExtractor:
    def __init__(self): self.model = self.processor = None; self.last_raw = ""
    def _load(self):
        if self.model is not None: return
        try:
            from transformers import AutoProcessor, Qwen3VLForConditionalGeneration
            settings = get_settings()
            device = settings.resolved_device
            import torch
            self.processor = AutoProcessor.from_pretrained(settings.qwen_model)
            # Do not use device_map="auto" here. On some Windows/Accelerate builds it
            # leaves Qwen parameters on the meta device, causing the Tensor.item error.
            options = {"low_cpu_mem_usage": device == "cuda"}
            if device == "cuda":
                # FP16 + PyTorch scaled-dot-product attention substantially reduces
                # laptop-GPU memory pressure and generation latency where supported.
                options.update({"torch_dtype":torch.float16,"attn_implementation":"sdpa"})
            try:
                self.model = Qwen3VLForConditionalGeneration.from_pretrained(settings.qwen_model, **options)
            except (TypeError, ValueError) as exc:
                if "attn_implementation" not in str(exc): raise
                options.pop("attn_implementation",None)
                self.model = Qwen3VLForConditionalGeneration.from_pretrained(settings.qwen_model, **options)
            self.model.to(device)
            self.model.eval()
        except Exception as exc: raise RuntimeError(f"Qwen3-VL unavailable: {exc}") from exc
    def ready(self) -> None: self._load()
    def extract(self, person_crop: Path, context_crop: Path | None = None) -> tuple[AttributePayload, str]:
        self._load()
        # apply_chat_template returns prompt text by default. Tokenize that text and
        # the two real crop images together before calling the multimodal model.
        include_context = bool(context_crop and get_settings().qwen_include_context)
        messages = [{"role":"user","content":([{"type":"image"}] * (2 if include_context else 1)) + [{"type":"text","text":PROMPT}]}]
        prompt = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        images = [Image.open(person_crop).convert("RGB")]
        if include_context: images.append(Image.open(context_crop).convert("RGB"))
        device = next(self.model.parameters()).device
        inputs = self.processor(text=[prompt], images=images, padding=True, return_tensors="pt").to(device)
        import torch
        with torch.inference_mode():
            if device.type == "cuda":
                with torch.autocast(device_type="cuda",dtype=torch.float16): output = self.model.generate(**inputs, max_new_tokens=get_settings().qwen_max_new_tokens, do_sample=False, use_cache=True)
            else: output = self.model.generate(**inputs, max_new_tokens=get_settings().qwen_max_new_tokens, do_sample=False, use_cache=True)
        raw = self.processor.decode(output[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
        self.last_raw = raw
        return self.parse_response(raw), raw

    @staticmethod
    def parse_response(raw: str) -> AttributePayload:
        """Tolerate fences/prose while accepting only a validated object."""
        cleaned = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", raw.strip(), flags=re.I)
        candidates=[cleaned]
        decoder=json.JSONDecoder()
        for start, char in enumerate(cleaned):
            if char == "{":
                try:
                    value, _ = decoder.raw_decode(cleaned[start:])
                    candidates.append(value)
                except json.JSONDecodeError: pass
        last_error=None
        for candidate in candidates:
            try:
                value=json.loads(candidate) if isinstance(candidate, str) else candidate
                # Normalize common alternate keys without treating omissions as facts.
                if "top_color" in value: value.setdefault("upper_clothing", {"type": value.get("top_type", "unknown"), "color": value["top_color"]})
                if "bottom_color" in value: value.setdefault("lower_clothing", {"type": value.get("bottom_type", "unknown"), "color": value["bottom_color"]})
                AttributeExtractor._normalize_value(value)
                return AttributePayload.model_validate(value)
            except (json.JSONDecodeError, ValueError, TypeError) as exc: last_error=exc
        raise ValueError(f"Qwen response did not contain a valid attribute JSON object: {last_error}")

    @staticmethod
    def _normalize_value(value: dict) -> None:
        """Convert common Qwen shorthand into the strictly indexed schema.

        The model often returns `"black shirt"` instead of the required
        `{type, color}` object or a scalar instead of an array. These are
        formatting differences, not grounds to discard valid CCTV evidence.
        """
        colors=("dark_green","dark_blue","black","white","red","blue","green","yellow","orange","pink","purple","brown","gray","dark")
        for key in ("upper_clothing","lower_clothing"):
            clothing=value.get(key, {"type":"unknown","color":"unknown"})
            if clothing is None: clothing={"type":"unknown","color":"unknown"}
            if isinstance(clothing,str):
                text=clothing.lower().replace("-", "_").strip()
                color=next((c for c in colors if c.replace("_"," ") in text.replace("_"," ")),"unknown")
                if color == "dark": color="unknown"
                type_=text
                if color != "unknown": type_=re.sub(rf"\b{re.escape(color.replace('_',' '))}\b", "", text.replace("_"," ")).strip() or "unknown"
                clothing={"type":type_.replace(" ","_"),"color":color}
            elif isinstance(clothing,dict):
                clothing={"type":clothing.get("type") or "unknown","color":clothing.get("color") or "unknown"}
            else: clothing={"type":"unknown","color":"unknown"}
            clothing["type"]={"t_shirt":"tshirt","tee_shirt":"tshirt","tee":"tshirt"}.get(clothing["type"],clothing["type"])
            value[key]=clothing
        for key in ("accessories","objects_held"):
            item=value.get(key, [])
            if item is None: item=[]
            if isinstance(item,str): item=[item]
            value[key]=[str(x).lower().strip() for x in item if x]
        for key in ("gender","headwear","eyewear"):
            if value.get(key) is None: value[key]="unknown"
