"""Generate an end-to-end workflow and measured-quality report for the CCTV project."""
from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "evaluation" / "forensic_project_workflow_evaluation.docx"


def shade(cell, color: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr(); shd = OxmlElement("w:shd"); shd.set(qn("w:fill"), color); tc_pr.append(shd)


def borders(cell) -> None:
    tc_pr = cell._tc.get_or_add_tcPr(); node = tc_pr.first_child_found_in("w:tcBorders")
    if node is None:
        node = OxmlElement("w:tcBorders"); tc_pr.append(node)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        item = OxmlElement(f"w:{edge}"); item.set(qn("w:val"), "single"); item.set(qn("w:sz"), "4"); item.set(qn("w:color"), "D9D9D9"); node.append(item)


def table(doc, headers, rows, widths=None, font_size=8.3):
    t = doc.add_table(rows=1, cols=len(headers)); t.style = "Table Grid"; t.autofit = False
    for idx, label in enumerate(headers):
        cell = t.rows[0].cells[idx]; cell.text = label; shade(cell, "17365D"); borders(cell); cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in cell.paragraphs[0].runs:
            run.font.bold = True; run.font.color.rgb = RGBColor(255, 255, 255); run.font.size = Pt(font_size)
        if widths: cell.width = Inches(widths[idx])
    for number, row in enumerate(rows):
        cells = t.add_row().cells
        for idx, value in enumerate(row):
            cell = cells[idx]; cell.text = str(value); borders(cell); cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            if number % 2: shade(cell, "EFF4F8")
            for para in cell.paragraphs:
                para.paragraph_format.space_before = Pt(2); para.paragraph_format.space_after = Pt(2)
                para.alignment = WD_ALIGN_PARAGRAPH.LEFT if idx == 0 else WD_ALIGN_PARAGRAPH.CENTER
                for run in para.runs: run.font.size = Pt(font_size)
            if widths: cell.width = Inches(widths[idx])
    doc.add_paragraph().paragraph_format.space_after = Pt(4)
    return t


def heading(doc, text, level=1):
    p = doc.add_heading(text, level=level); p.paragraph_format.space_before = Pt(8); p.paragraph_format.space_after = Pt(4)
    for run in p.runs: run.font.color.rgb = RGBColor(0, 0, 0)


def para(doc, text, bold_prefix=None):
    p = doc.add_paragraph()
    if bold_prefix and text.startswith(bold_prefix):
        p.add_run(bold_prefix).bold = True; p.add_run(text[len(bold_prefix):])
    else: p.add_run(text)
    p.paragraph_format.space_after = Pt(4)
    return p


def rate(n, d):
    return "N/A" if not d else f"{n / d * 100:.1f}%"


def metrics():
    c = sqlite3.connect(ROOT / "ai_detective.db").cursor()
    one = lambda sql: c.execute(sql).fetchone()
    values = {}
    values["videos"] = one("select count(*) from videos")[0]
    values["frames"] = one("select count(*) from frames")[0]
    values["detections"], values["det_avg"], values["det_min"], values["det_max"] = one("select count(*),avg(confidence),min(confidence),max(confidence) from detections")
    values["objects"], values["obj_avg"], values["obj_min"], values["obj_max"] = one("select count(*),avg(confidence),min(confidence),max(confidence) from object_observations")
    values["tracks"], values["track_avg"], values["track_min"], values["track_max"] = one("select count(*),avg(detection_count),min(detection_count),max(detection_count) from tracks")
    values["attrs"], values["gender"], values["utype"], values["ucolor"], values["ltype"], values["lcolor"] = one("select count(*),sum(gender != 'unknown'),sum(upper_type != 'unknown'),sum(upper_color != 'unknown'),sum(lower_type != 'unknown'),sum(lower_color != 'unknown') from person_attributes")
    values["audits"], values["parse_errors"] = one("select count(*),sum(parse_error is not null) from attribute_audits")
    values["actions"], values["action_avg"], values["action_min"], values["action_max"] = one("select count(*),avg(confidence),min(confidence),max(confidence) from actions")
    values["searches"] = one("select count(*) from search_queries")[0]
    values["jobs"] = dict(c.execute("select status,count(*) from processing_jobs group by status"))
    values["classes"] = c.execute("select label,count(*),avg(confidence) from object_observations group by label order by count(*) desc limit 8").fetchall()
    values["actions_by_label"] = c.execute("select action,count(*),avg(confidence) from actions group by action order by count(*) desc limit 6").fetchall()
    return values


def main():
    m = metrics()
    doc = Document(); s = doc.sections[0]; s.top_margin = Inches(.6); s.bottom_margin = Inches(.6); s.left_margin = Inches(.65); s.right_margin = Inches(.65)
    doc.styles["Normal"].font.name = "Aptos"; doc.styles["Normal"].font.size = Pt(9.5)
    title = doc.add_paragraph(style="Title"); title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = title.add_run("CCTV Forensic Search Workflow and Evaluation Report"); run.font.color.rgb = RGBColor(0, 0, 0)
    sub = doc.add_paragraph(); sub.alignment = WD_ALIGN_PARAGRAPH.CENTER; sub.add_run("End to end data flow, measured operating results, evaluation framework and accuracy improvements").italic = True
    doc.add_paragraph(f"Generated {datetime.now().strftime('%d %B %Y %H:%M')}. Snapshot: {m['videos']} video records, {m['frames']:,} indexed frames, and {m['jobs'].get('completed',0) + m['jobs'].get('completed_with_warnings',0)} completed processing jobs.")

    heading(doc, "Executive assessment")
    para(doc, "The project has a complete evidence-first workflow from uploaded video to a Gemini-assisted answer with a single clickable frame. YOLOv8m and ByteTrack provide the strongest current foundation. Attribute retrieval is incomplete, especially for gender and clothing colour. The current VideoMAE action output is not reliable enough to present as forensic evidence because its mean confidence is only %.3f and its labels are often inconsistent with CCTV activity. Gemini can be grounded in local evidence, but its answer accuracy has not yet been measured against a labelled question set." % m["action_avg"])
    para(doc, "Important interpretation: model confidence is not accuracy. Accuracy, precision, recall, F1 score, mAP, IDF1 and LLM answer correctness require human-labelled ground truth. The report gives current observed values and marks unsupported accuracy metrics as not yet measurable.")

    heading(doc, "End to end workflow")
    para(doc, "The following flow represents the implemented path from a CCTV upload to an evidence-backed answer. Parallel branches preserve their own evidence and are merged only through the SQLite index.")
    flow = [
        ["1  Video upload", "User uploads MP4 AVI or MOV", "Secure stored original under storage uploads", "Validation state and video metadata"],
        ["v", "", "", ""],
        ["2  OpenCV validation and sampling", "VideoProcessor reads FPS duration resolution; samples at FRAME_SAMPLE_FPS", "Frame JPEG and timestamp", "Frame rows in SQLite"],
        ["v", "", "", ""],
        ["3  YOLOv8m inference", "YOLOv8m detects people and COCO objects on each sampled frame using CUDA when available", "Person boxes, non person object boxes, confidence", "detections and object_observations"],
        ["v", "", "", ""],
        ["4  ByteTrack and spatial evidence", "YOLO track mode links people across frames; same frame box geometry measures person object association", "Track ID, temporal span, association score", "tracks and object_relationships"],
        ["v", "", "", ""],
        ["5  Person crop quality gate", "Ranks person crops by detector confidence and crop area", "Representative crop per eligible track", "Crop file and selected track"],
        ["v", "", "", ""],
        ["6A  Colour branch", "Local HSV dominant-colour estimator measures upper and lower clothing zones", "Colour plus local purity confidence", "PersonAttribute colour fields"],
        ["6B  Attribute branch", "Qwen3 VL produces constrained JSON for visible clothing type, gender presentation, accessories and held objects; optional PP Human can fill supported local attributes", "Validated attribute payload and raw audit", "person_attributes and attribute_audits"],
        ["6C  Action branch", "VideoMAE classifies a 16 frame temporal window associated with a track", "Checkpoint action label and softmax confidence", "actions"],
        ["v", "", "", ""],
        ["7  Evidence index", "Frames, tracks, attributes, actions and spatial relationships are written to SQLite", "Searchable local metadata", "Evidence authority for all queries"],
        ["v", "", "", ""],
        ["8  Query interpretation", "Gemini converts a natural-language question to constrained filters; local rules are fallback", "Structured person object colour action constraints", "ParsedQuery"],
        ["v", "", "", ""],
        ["9  Deterministic retrieval", "SQLite applies filters and selects strongest real frame and interval", "Ranked verified result rows", "One primary evidence item"],
        ["v", "", "", ""],
        ["10  Grounded Gemini answer", "Gemini receives only selected local evidence facts and returns one concise answer", "Answer plus provider label", "UI answer and clickable evidence frame"],
    ]
    table(doc, ["Flow stage", "Processing", "Output", "Stored evidence"], flow, [1.35, 2.85, 1.7, 1.45], 7.4)

    heading(doc, "Current measured results by workflow stage")
    table(doc, ["Stage", "Current measured value", "Quality interpretation", "True evaluation status"], [
        ["Upload and processing", f"{sum(m['jobs'].values())} jobs: {m['jobs'].get('completed',0)} completed, {m['jobs'].get('completed_with_warnings',0)} completed with warnings, {m['jobs'].get('processing',0)} processing", "The pipeline runs end to end, but five unfinished jobs should be resolved before a final benchmark.", "Reliability rate can be calculated after retrying incomplete jobs."],
        ["Sampling", f"{m['frames']:,} indexed frames across {m['videos']} video records", "Sufficient stored evidence for operational inspection; sample rate affects missed short events.", "Frame-level recall needs labelled events/boxes."],
        ["YOLO people", f"{m['detections']:,} detections; confidence mean {m['det_avg']:.3f}, range {m['det_min']:.3f}-{m['det_max']:.3f}", "Moderate-to-strong model confidence; low-confidence rows need threshold calibration.", "Precision, recall, F1, AP and mAP: not measurable without boxes."],
        ["YOLO objects", f"{m['objects']:,} observations; confidence mean {m['obj_avg']:.3f}, range {m['obj_min']:.3f}-{m['obj_max']:.3f}", "Object labels require manual validation. COCO labels may be unsuitable for site-specific CCTV classes.", "Per-class AP and false-positive rate: not measurable."],
        ["ByteTrack", f"{m['tracks']} tracks; {m['track_avg']:.2f} mean observations per track; range {m['track_min']}-{m['track_max']}", "Tracks provide evidence continuity, but fragmentation and identity switches are unknown.", "HOTA, MOTA, IDF1 and ID switches: not measurable."],
        ["Qwen and colour", f"{m['attrs']} attributes for {m['tracks']} tracks ({rate(m['attrs'],m['tracks'])}); {m['parse_errors'] or 0}/{m['audits']} audit parse failures", "Useful for reviewed leads; coverage, not correctness, is measured.", "Attribute accuracy, macro F1 and calibration: not measurable."],
        ["VideoMAE", f"{m['actions']} segments; confidence mean {m['action_avg']:.3f}, range {m['action_min']:.3f}-{m['action_max']:.3f}", "Current action predictions are low confidence and unsuitable for automatic forensic claims.", "Top-1 action accuracy and macro F1: not measurable."],
        ["Gemini query and answer", f"{m['searches']} saved searches; response text is not retained as an evaluation artifact", "The retrieval design limits Gemini to local facts, but output correctness remains untested.", "Answer accuracy, support rate and evidence recall: not measurable."],
    ], [1.2, 1.75, 2.35, 1.65], 7.2)

    heading(doc, "Attribute coverage and retrieval readiness")
    table(doc, ["Attribute", "Known values", "Coverage among stored attributes", "Assessment"], [
        ["Gender presentation", str(m['gender'] or 0), rate(m['gender'] or 0, m['attrs']), "Too incomplete for unreviewed counts; keep unknown rather than guessing."],
        ["Upper garment type", str(m['utype'] or 0), rate(m['utype'] or 0, m['attrs']), "Moderate lead-generation coverage; verify on the evidence frame."],
        ["Upper garment colour", str(m['ucolor'] or 0), rate(m['ucolor'] or 0, m['attrs']), "Lighting and crop quality make this a review cue, not a confirmed fact."],
        ["Lower garment type", str(m['ltype'] or 0), rate(m['ltype'] or 0, m['attrs']), "Moderate lead-generation coverage."],
        ["Lower garment colour", str(m['lcolor'] or 0), rate(m['lcolor'] or 0, m['attrs']), "Weak coverage; do not use as an exclusive filter without manual review."],
    ], [1.65, 1.15, 1.65, 2.5], 8.2)

    heading(doc, "Observed object and action outputs")
    table(doc, ["Most frequent object class", "Frame observations", "Mean detector confidence"], [[x[0], str(x[1]), f"{x[2]:.3f}"] for x in m["classes"]], [2.45, 1.7, 2.5], 8.4)
    table(doc, ["Frequent action label", "Segments", "Mean action confidence"], [[x[0], str(x[1]), f"{x[2]:.3f}"] for x in m["actions_by_label"]], [2.95, 1.25, 2.45], 8.4)
    para(doc, "The action labels above are checkpoint outputs, not independently verified events. Their very low confidence values and labels such as recording music or robot dancing indicate a domain mismatch between the current VideoMAE checkpoint and this CCTV footage.")

    doc.add_section(WD_SECTION.NEW_PAGE)
    heading(doc, "Metric definitions and current availability")
    table(doc, ["Metric", "Formula or meaning", "Used at stage", "Current value"], [
        ["Accuracy", "Correct predictions divided by all predictions", "Attributes, actions, answers", "Not measurable - labels/expected answers absent"],
        ["Precision", "True positives divided by true positives plus false positives", "YOLO, attributes, retrieval", "Not measurable - false positives are not labelled"],
        ["Recall", "True positives divided by true positives plus false negatives", "YOLO, attributes, retrieval", "Not measurable - missed ground truth is not labelled"],
        ["F1 score", "Harmonic mean of precision and recall", "YOLO, attributes, actions", "Not measurable"],
        ["AP and mAP", "Area under precision-recall curve; mean over classes and IoU thresholds", "YOLO detection", "Not measurable"],
        ["IDF1 and HOTA", "Identity and association quality for multi-object tracking", "ByteTrack", "Not measurable"],
        ["Coverage", "Non-unknown / eligible evidence records", "Attributes", f"Track attribute coverage {rate(m['attrs'],m['tracks'])}"],
        ["Mean confidence", "Average model confidence; not correctness", "YOLO and VideoMAE", f"People {m['det_avg']:.3f}; objects {m['obj_avg']:.3f}; actions {m['action_avg']:.3f}"],
        ["Grounded answer support rate", "Answers fully supported by selected evidence / answers reviewed", "Gemini", "Not measurable - no reviewed answer set"],
    ], [1.25, 2.75, 1.55, 2.0], 7.7)

    heading(doc, "Required 20 epoch benchmark")
    para(doc, "A 20 epoch run should fine-tune YOLO on a new CCTV-specific labelled dataset, not train on the SQLite detections produced by the same model. Split videos, not adjacent frames, into training, validation and held-out test sets to avoid leakage. Keep site, camera angle, time of day and subject identities distributed across splits.")
    table(doc, ["Dataset requirement", "Minimum content", "Evaluation output after 20 epochs"], [
        ["Detection labels", "YOLO text labels for every person and required object box; frame lists split by video", "mAP50, mAP50-95, precision, recall, F1, per-class AP and confusion matrix"],
        ["Tracking labels", "Persistent ID per person across test-video frames", "HOTA, IDF1, MOTA, ID switches, mostly tracked rate"],
        ["Attribute labels", "Reviewed visible garment type/colour and allowed accessory attributes; unknown/occluded labels required", "Per-field accuracy, macro F1, precision, recall, coverage and confusion matrices"],
        ["Action labels", "Start/end action segments for actions the system is expected to detect", "Top-1 accuracy, macro F1, temporal segment IoU and per-class recall"],
        ["LLM QA set", "Held-out questions, expected answer, expected supporting evidence frame or track", "Answer accuracy or rubric score, support rate, evidence precision/recall, unsupported-claim rate"],
    ], [1.35, 2.7, 2.5], 7.6)

    heading(doc, "Recommended accuracy improvements")
    table(doc, ["Priority", "Component", "Modification", "Expected measurement improvement"], [
        ["P0", "Evaluation data", "Label representative CCTV videos and preserve a held-out test set. Run 20 epoch YOLO fine-tuning only after this split exists.", "Enables valid mAP, precision, recall and F1 instead of confidence-only reporting."],
        ["P0", "YOLO objects", "Fine-tune only the relevant local classes; remove or down-rank irrelevant COCO classes; calibrate confidence and NMS thresholds on validation data.", "Reduces false positives and improves per-class precision."],
        ["P0", "VideoMAE", "Replace the current checkpoint with a CCTV-domain action model trained for a small defined action taxonomy. Crop the tracked person before temporal classification; do not classify the full frame separately for each track.", "Improves action class relevance, top-1 accuracy and temporal F1."],
        ["P1", "ByteTrack", "Tune tracker thresholds using validation videos; evaluate track fragments and ID switches. Preserve detection confidence and camera-specific settings.", "Improves IDF1/HOTA and evidence continuity."],
        ["P1", "Qwen and PP Human", "Use two or three diverse high-quality crops per track, require cross-frame agreement, keep unknown when inconsistent, and enable PP Human only after its local model is installed and tested.", "Improves attribute coverage and macro F1 while avoiding overclaiming."],
        ["P1", "Colour", "Use person segmentation or pose-guided torso/leg masks, white-balance normalization and multi-frame colour consensus rather than one rectangular crop alone.", "Improves colour precision under shadows, skin exposure and background clutter."],
        ["P1", "Gemini", "Persist answer, selected evidence IDs and Gemini provider result; evaluate a held-out question set. Enforce a response template that states no evidence when retrieval is empty.", "Measures grounded answer accuracy and lowers unsupported-claim rate."],
        ["P2", "Monitoring", "Log inference time, GPU memory, confidence histograms, unknown rates and evaluator decisions per model version.", "Makes regressions measurable across model and configuration changes."],
    ], [0.55, 1.2, 3.35, 1.45], 7.25)

    heading(doc, "Suggested deployment gates")
    para(doc, "These are proposed pilot acceptance targets, not current results: person and object precision/recall each at least 0.80 on the held-out CCTV test set; mAP50 at least 0.85 for supported classes; tracking IDF1 at least 0.75; attribute macro F1 at least 0.80 for only the attributes with sufficient labelled samples; action macro F1 at least 0.75 for the defined CCTV action set; Gemini evidence support rate 100 percent; and no answer presented when retrieval returns no evidence. Set the final thresholds after reviewing actual false-positive and missed-event costs with investigators.")

    heading(doc, "Final recommendation")
    para(doc, "Use the current system for investigator-assisted discovery: person tracks, source frames, verified same-frame object associations and cautiously worded attribute leads. Do not use its current gender, clothing-colour, object-class or action outputs as unreviewed forensic conclusions. The first engineering priority is a labelled CCTV benchmark and a 20 epoch, held-out YOLO evaluation; the second is replacing or retraining the action model for the project action taxonomy.")

    OUT.parent.mkdir(parents=True, exist_ok=True); doc.save(OUT); print(OUT)


if __name__ == "__main__": main()
