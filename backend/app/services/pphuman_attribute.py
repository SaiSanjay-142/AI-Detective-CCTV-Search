"""Optional local PP-Human attribute adapter.

It consumes an exported PaddleDetection PP-Human person-attribute model from
``PPHUMAN_MODEL_DIR``.  Nothing is downloaded at runtime and a missing Paddle
installation/model simply leaves Qwen as the fallback.  The compact standard
label list is the one used by the public PP-Human attribute export.
"""
from __future__ import annotations

from pathlib import Path
import numpy as np

from ..config import get_settings

LABELS = (
    "female", "age_less_18", "age_18_60", "age_over_60", "front", "side", "back",
    "hat", "glasses", "handbag", "shoulder_bag", "backpack", "holding_object",
    "short_sleeve", "long_sleeve", "upper_stripe", "upper_logo", "upper_plaid",
    "upper_splice", "lower_stripe", "lower_pattern", "long_coat", "trousers",
    "shorts", "skirt_or_dress", "boots",
)


class PPHumanAttributeExtractor:
    def __init__(self) -> None:
        self.predictor = self.input_name = self.output_name = None
        self.reason = "not initialised"

    def _load(self) -> None:
        if self.predictor is not None:
            return
        settings = get_settings()
        if not settings.pphuman_enabled:
            raise RuntimeError("PP-Human is disabled (set PPHUMAN_ENABLED=true after installing its model).")
        model_dir = settings.root / settings.pphuman_model_dir
        model = next((p for p in (model_dir / "inference.pdmodel", model_dir / "model.pdmodel") if p.exists()), None)
        params = next((p for p in (model_dir / "inference.pdiparams", model_dir / "model.pdiparams") if p.exists()), None)
        if not model or not params:
            raise RuntimeError(f"PP-Human exported model files were not found in {model_dir}")
        try:
            import paddle.inference as paddle_infer
        except Exception as exc:
            raise RuntimeError("PaddlePaddle is not installed for this Python environment") from exc
        config = paddle_infer.Config(str(model), str(params))
        if settings.resolved_device == "cuda":
            config.enable_use_gpu(1024, 0)
        else:
            config.disable_gpu()
        config.switch_ir_optim(True)
        config.enable_memory_optim()
        config.switch_use_feed_fetch_ops(False)
        self.predictor = paddle_infer.create_predictor(config)
        self.input_name = self.predictor.get_input_names()[0]
        self.output_name = self.predictor.get_output_names()[0]

    def available(self) -> bool:
        try:
            self._load()
            return True
        except Exception as exc:
            self.reason = str(exc)
            return False

    def extract(self, person_bgr: np.ndarray) -> tuple[dict[str, object], dict[str, float]]:
        self._load()
        import cv2
        image = cv2.cvtColor(person_bgr, cv2.COLOR_BGR2RGB)
        image = cv2.resize(image, (192, 256), interpolation=cv2.INTER_LINEAR).astype("float32") / 255.0
        image = (image - np.array([0.485, 0.456, 0.406], dtype="float32")) / np.array([0.229, 0.224, 0.225], dtype="float32")
        tensor = np.transpose(image, (2, 0, 1))[None, ...]
        input_handle = self.predictor.get_input_handle(self.input_name)
        input_handle.reshape(tensor.shape); input_handle.copy_from_cpu(tensor)
        self.predictor.run()
        scores = self.predictor.get_output_handle(self.output_name).copy_to_cpu().reshape(-1)
        probabilities = 1.0 / (1.0 + np.exp(-scores)) if np.any((scores < 0) | (scores > 1)) else scores
        values = {label: float(probabilities[index]) for index, label in enumerate(LABELS) if index < len(probabilities)}
        threshold = get_settings().pphuman_threshold
        accessories = [name for name in ("hat", "glasses", "handbag", "shoulder_bag", "backpack") if values.get(name, 0.0) >= threshold]
        garment = "unknown"
        for label, name in (("skirt_or_dress", "dress"), ("long_coat", "coat"), ("short_sleeve", "short_sleeve"), ("long_sleeve", "long_sleeve")):
            if values.get(label, 0.0) >= threshold:
                garment = name; break
        lower = next((name for label, name in (("trousers", "trousers"), ("shorts", "shorts"), ("skirt_or_dress", "skirt_or_dress")) if values.get(label, 0.0) >= threshold), "unknown")
        female_score = values.get("female", 0.0)
        # The PP-Human export uses a Female attribute; a clearly negative score
        # is evidence for the complementary male presentation.  Scores close to
        # the decision boundary stay unknown rather than being forced.
        gender = "female" if female_score >= threshold else ("male" if female_score <= 1 - threshold else "unknown")
        return {"gender": gender, "upper_type": garment, "lower_type": lower, "accessories": accessories, "objects_held": ["object"] if values.get("holding_object", 0.0) >= threshold else []}, values
