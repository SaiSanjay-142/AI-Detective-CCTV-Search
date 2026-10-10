"""Create report-ready evaluation figures from the SQLite evidence database.

Confidence and coverage are displayed explicitly as operational measurements;
they are not relabelled as accuracy because this project has no ground truth.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "evaluation" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

W, H = 1500, 900
NAVY = "#17365D"; BLUE = "#2F75B5"; TEAL = "#0B6B5D"; PURPLE = "#5A48B2"; GRAY = "#68727D"; LIGHT = "#EAF1F8"; GRID = "#CBD5E1"; WHITE = "#FFFFFF"; TEXT = "#152235"

def font(size: int, bold: bool = False):
    candidates = ["C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/calibrib.ttf" if bold else "C:/Windows/Fonts/calibri.ttf"]
    for candidate in candidates:
        if Path(candidate).exists(): return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()

def base(title: str, subtitle: str):
    image = Image.new("RGB", (W, H), WHITE); draw = ImageDraw.Draw(image)
    draw.text((75, 52), title, font=font(38, True), fill=TEXT)
    draw.text((75, 103), subtitle, font=font(22), fill=GRAY)
    return image, draw

def bar_chart(filename: str, title: str, subtitle: str, labels: list[str], values: list[float], colors: list[str], y_label: str):
    image, draw = base(title, subtitle)
    left, top, right, bottom = 145, 190, 1430, 730
    draw.line((left, bottom, right, bottom), fill=TEXT, width=3); draw.line((left, top, left, bottom), fill=TEXT, width=3)
    for tick in range(0, 101, 20):
        y = bottom - (bottom - top) * tick / 100
        draw.line((left, y, right, y), fill=GRID, width=1)
        draw.text((70, y - 12), f"{tick}%", font=font(18), fill=GRAY)
    count = len(labels); available = right - left; gap = 55; bar_w = min(190, int((available - gap * (count + 1)) / count))
    total = count * bar_w + (count - 1) * gap; start = left + (available - total) // 2
    for index, (label, value, color) in enumerate(zip(labels, values, colors)):
        x = start + index * (bar_w + gap); bar_h = (bottom - top) * value / 100
        draw.rounded_rectangle((x, bottom - bar_h, x + bar_w, bottom), radius=12, fill=color)
        value_text = f"{value:.1f}%"; tw = draw.textbbox((0,0), value_text, font=font(22, True))[2]
        draw.text((x + (bar_w - tw) / 2, bottom - bar_h - 38), value_text, font=font(22, True), fill=TEXT)
        words = label.split("\n")
        for line_index, word in enumerate(words):
            box = draw.textbbox((0,0), word, font=font(18)); draw.text((x + (bar_w - (box[2]-box[0])) / 2, bottom + 20 + line_index * 24), word, font=font(18), fill=TEXT)
    draw.text((75, 805), "Source: ai_detective.db. Values are measured from currently indexed evidence.", font=font(18), fill=GRAY)
    image.save(OUT / filename, quality=95)

def metric_status(filename: str):
    image, draw = base("Accuracy metric readiness", "A valid accuracy score requires manually labelled ground truth; the current project database does not contain it.")
    rows = [("Detection", "mAP, precision, recall", "Not measurable"), ("Tracking", "IDF1, HOTA, MOTA", "Not measurable"), ("Attributes", "Accuracy, macro F1", "Not measurable"), ("Actions", "Top-1 accuracy, macro F1", "Not measurable"), ("Gemini answers", "Answer accuracy, support rate", "Not measurable")]
    x1, x2, x3, y = 90, 445, 940, 190
    header_h, row_h = 70, 96
    for x, text in ((x1, "Component"), (x2, "Required evaluation metrics"), (x3, "Current status")):
        draw.rounded_rectangle((x, y, x + (315 if x == x1 else 435 if x == x2 else 455), y + header_h), radius=10, fill=NAVY)
        draw.text((x + 18, y + 20), text, font=font(22, True), fill=WHITE)
    y += header_h + 8
    for index, (component, metrics, status) in enumerate(rows):
        fill = LIGHT if index % 2 == 0 else WHITE
        for x, width in ((x1,315),(x2,435),(x3,455)):
            draw.rectangle((x, y, x+width, y+row_h), fill=fill, outline=GRID, width=2)
        draw.text((x1 + 18, y + 30), component, font=font(22, True), fill=TEXT)
        draw.text((x2 + 18, y + 30), metrics, font=font(20), fill=TEXT)
        draw.text((x3 + 18, y + 30), status, font=font(20, True), fill=GRAY)
        y += row_h
    draw.rounded_rectangle((90, 760, 1395, 830), radius=10, fill="#FFF3CD")
    draw.text((115, 782), "Next step: label separate test videos and compare predictions with the labels before reporting accuracy or F1 score.", font=font(19), fill=TEXT)
    image.save(OUT / filename, quality=95)

def main():
    cursor = sqlite3.connect(ROOT / "ai_detective.db").cursor()
    detections, detector_confidence = cursor.execute("select count(*), avg(confidence) from detections").fetchone()
    objects, object_confidence = cursor.execute("select count(*), avg(confidence) from object_observations").fetchone()
    actions, action_confidence = cursor.execute("select count(*), avg(confidence) from actions").fetchone()
    tracks = cursor.execute("select count(*) from tracks").fetchone()[0]
    attrs, gender, upper_type, upper_colour, lower_type, lower_colour = cursor.execute("select count(*), sum(gender != 'unknown'), sum(upper_type != 'unknown'), sum(upper_color != 'unknown'), sum(lower_type != 'unknown'), sum(lower_color != 'unknown') from person_attributes").fetchone()
    bar_chart("figure_6_1_model_confidence.png", "Model output confidence", "Confidence shows model certainty in stored predictions. It is not accuracy.", ["Person\ndetection", "Object\ndetection", "VideoMAE\naction"], [detector_confidence*100, object_confidence*100, action_confidence*100], [BLUE, TEAL, PURPLE], "Mean confidence")
    bar_chart("figure_6_2_attribute_coverage.png", "Attribute retrieval coverage", f"Known non-unknown values among {attrs} stored attribute records; track coverage is {attrs} of {tracks} tracks.", ["Track\nattributes", "Gender\npresentation", "Upper\ntype", "Upper\ncolour", "Lower\ntype", "Lower\ncolour"], [attrs/tracks*100 if tracks else 0, gender/attrs*100 if attrs else 0, upper_type/attrs*100 if attrs else 0, upper_colour/attrs*100 if attrs else 0, lower_type/attrs*100 if attrs else 0, lower_colour/attrs*100 if attrs else 0], [BLUE, PURPLE, TEAL, TEAL, TEAL, TEAL], "Coverage")
    metric_status("figure_6_3_accuracy_readiness.png")
    print(f"Created figures from {detections} person detections, {objects} object observations and {actions} action segments in {OUT}")

if __name__ == "__main__": main()
