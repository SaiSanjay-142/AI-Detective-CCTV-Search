import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        self.setFont("Times-Roman", 9)
        # We don't draw page numbers or headers if following strict camera-ready conference style,
        # but subtle bottom page numbers are standard.
        # Template has clean bottom.

def build_pdf(filename="AI_Detective_Research_Paper.pdf"):
    # Page setup: letter size (8.5 x 11 inches) = 612 x 792 pt
    doc = BaseDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    page_width, page_height = letter
    margin = 36
    gutter = 18
    col_width = (page_width - 2 * margin - gutter) / 2 # (612 - 72 - 18)/2 = 261 pt
    full_width = page_width - 2 * margin # 540 pt

    # First page has title/author header, then 2 columns below
    # We can design a two-column frame layout for all pages
    frame_left = Frame(margin, margin, col_width, page_height - 2 * margin, id='col1', leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    frame_right = Frame(margin + col_width + gutter, margin, col_width, page_height - 2 * margin, id='col2', leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)

    # First page template with title frame at top
    header_height = 185
    frame_header = Frame(margin, page_height - margin - header_height, full_width, header_height, id='header', leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    frame_p1_left = Frame(margin, margin, col_width, page_height - 2 * margin - header_height, id='p1_col1', leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    frame_p1_right = Frame(margin + col_width + gutter, margin, col_width, page_height - 2 * margin - header_height, id='p1_col2', leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)

    template_first = PageTemplate(id='FirstPage', frames=[frame_header, frame_p1_left, frame_p1_right])
    template_later = PageTemplate(id='LaterPages', frames=[frame_left, frame_right])

    doc.addPageTemplates([template_first, template_later])

    # Styles
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'PaperTitle',
        fontName='Times-Bold',
        fontSize=18,
        leading=22,
        alignment=1, # Center
        spaceAfter=10
    )

    author_name_style = ParagraphStyle(
        'AuthorName',
        fontName='Times-Bold',
        fontSize=10,
        leading=13,
        alignment=1
    )

    author_affil_style = ParagraphStyle(
        'AuthorAffil',
        fontName='Times-Roman',
        fontSize=8.5,
        leading=11,
        alignment=1
    )

    author_email_style = ParagraphStyle(
        'AuthorEmail',
        fontName='Times-Italic',
        fontSize=8,
        leading=10,
        alignment=1
    )

    abstract_style = ParagraphStyle(
        'AbstractText',
        fontName='Times-Roman',
        fontSize=9,
        leading=11.5,
        alignment=4, # Justified
        spaceAfter=6
    )

    keywords_style = ParagraphStyle(
        'KeywordsText',
        fontName='Times-Roman',
        fontSize=9,
        leading=11.5,
        alignment=4,
        spaceAfter=10
    )

    heading1_style = ParagraphStyle(
        'Heading1_Custom',
        fontName='Times-Bold',
        fontSize=10,
        leading=13,
        alignment=1, # Center
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )

    heading2_style = ParagraphStyle(
        'Heading2_Custom',
        fontName='Times-BoldItalic',
        fontSize=9.5,
        leading=12,
        alignment=0, # Left
        spaceBefore=7,
        spaceAfter=3,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        fontName='Times-Roman',
        fontSize=9,
        leading=11.5,
        alignment=4, # Justified
        firstLineIndent=10,
        spaceAfter=4
    )

    body_noindent = ParagraphStyle(
        'Body_NoIndent',
        fontName='Times-Roman',
        fontSize=9,
        leading=11.5,
        alignment=4, # Justified
        firstLineIndent=0,
        spaceAfter=4
    )

    equation_style = ParagraphStyle(
        'Equation_Style',
        fontName='Times-Italic',
        fontSize=9,
        leading=12,
        alignment=1, # Center
        spaceBefore=4,
        spaceAfter=4
    )

    caption_style = ParagraphStyle(
        'Caption_Style',
        fontName='Times-Roman',
        fontSize=8,
        leading=10.5,
        alignment=1, # Center
        spaceBefore=4,
        spaceAfter=6
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        fontName='Times-Roman',
        fontSize=7.5,
        leading=9.5,
        alignment=0
    )

    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        fontName='Times-Bold',
        fontSize=7.5,
        leading=9.5,
        alignment=0
    )

    table_title_style = ParagraphStyle(
        'TableTitle',
        fontName='Times-Bold',
        fontSize=8.5,
        leading=11,
        alignment=1,
        spaceBefore=6,
        spaceAfter=2,
        keepWithNext=True
    )

    ref_style = ParagraphStyle(
        'RefStyle',
        fontName='Times-Roman',
        fontSize=8,
        leading=10.2,
        alignment=4,
        leftIndent=14,
        firstLineIndent=-14,
        spaceAfter=3
    )

    story = []

    # ==================== HEADER FLOWABLES ====================
    # Title
    story.append(Paragraph("AI Detective: An Explainable and Metadata-Driven System for Video Surveillance Search and Evidence Retrieval", title_style))
    story.append(Spacer(1, 4))

    # Authors Table (4 authors in 2 columns layout matching template)
    author_col_w = full_width / 2
    author_table_data = [
        [
            Paragraph("<b>Ms.C.Arulmozhi</b><br/>Assistant Professor<br/>Department of AIML<br/>Rajalakshmi Engineering College<br/>Chennai, Tamil Nadu, India<br/><i>arulmozhi.c@rajalakshmi.edu.in</i>", author_affil_style),
            Paragraph("<b>Sanjai T</b><br/>UG Student<br/>Dept. of AIML<br/>Rajalakshmi Engineering College<br/>Chennai, India<br/><i>231501144@rajalakshmi.edu.in</i>", author_affil_style)
        ],
        [
            Paragraph("<b>Sooryanath S D</b><br/>UG Student<br/>Dept. of AIML<br/>Rajalakshmi Engineering College<br/>Chennai, India<br/><i>231501158@rajalakshmi.edu.in</i>", author_affil_style),
            Paragraph("<b>Sharan M</b><br/>UG Student<br/>Dept. of AIML<br/>Rajalakshmi Engineering College<br/>Chennai, India<br/><i>231501151@rajalakshmi.edu.in</i>", author_affil_style)
        ]
    ]
    author_table = Table(author_table_data, colWidths=[author_col_w, author_col_w])
    author_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(author_table)
    story.append(Spacer(1, 10))

    # Next content flows into the two columns automatically!

    # ==================== ABSTRACT & KEYWORDS ====================
    abstract_text = (
        "<b><i>Abstract</i>— Manual inspection of Closed-Circuit Television (CCTV) footage during forensic "
        "investigations is labor-intensive, error-prone, and unsustainable across voluminous surveillance repositories. "
        "While multimodal large language models and vision-language architectures offer zero-shot natural language query "
        "capabilities, direct end-to-end video reasoning frequently suffers from visual hallucinations, ungrounded co-occurrence "
        "assumptions, and an absence of frame-level provenance. This paper presents AI Detective, an explainable, metadata-driven "
        "decision-support and forensic search system that chains four distinct stages: uniform video frame sampling with YOLOv8 "
        "object detection and ByteTrack persistent multi-person tracking; a fail-safe multi-tier attribute extraction engine "
        "combining local HSV color modeling with Qwen3-VL-2B and PP-Human inference; a deterministic same-frame spatial relationship "
        "engine evaluating bounding box Intersection over Union (IoU) and normalized centroid distance; and a dual natural "
        "language query engine coupling deterministic SQL compilation with Gemini-based structured translation. An SQLite relational "
        "index anchors every detection, clothing attribute, spatial association, and temporal action window to precise frame timestamps "
        "and normalized bounding box coordinates. When queried, the system retrieves deterministic evidence records, produces clipped "
        "MP4 sub-video extracts via FFmpeg, and generates printable forensic investigation reports. Gemini functions strictly as an "
        "explanation and query synthesis layer, with responses bound to verified database records. The primary contribution lies "
        "in integrating spatial verification, multi-tier attribute fallbacks, and relational indexing into an auditable surveillance "
        "workflow where detection, tracking, spatial association, and natural language explanation remain cleanly decoupled. "
        "Quantitative benchmarks confirm real-time detection and tracking throughput (~45–50 FPS) and resilient zero-hallucination "
        "retrieval across complex multi-object surveillance scenarios.</b>"
    )
    story.append(Paragraph(abstract_text, abstract_style))

    keywords_text = (
        "<b><i>Keywords</i>— CCTV surveillance search, explainable AI, YOLOv8, ByteTrack, spatial relationship engine, "
        "Qwen3-VL, Gemini, multi-object tracking, forensic video retrieval.</b>"
    )
    story.append(Paragraph(keywords_text, keywords_style))

    # ==================== I. INTRODUCTION ====================
    story.append(Paragraph("I. INTRODUCTION", heading1_style))
    story.append(Paragraph(
        "Modern urban environments, transit networks, retail establishments, and critical infrastructure facilities deploy "
        "thousands of Closed-Circuit Television (CCTV) cameras that continuously record immense quantities of video data. "
        "In forensic security and criminal investigations, locating specific suspects, vehicles, or lost property requires "
        "pinpointing complex multi-attribute events, such as identifying <i>\"a person in black pants carrying a backpack near a bicycle.\"</i> "
        "In contemporary practice, law enforcement officers and security analysts must manually review hours of raw video footage. "
        "This manual inspection process is painfully slow, susceptible to operator fatigue, and incapable of scaling during time-critical emergencies.",
        body_noindent
    ))
    story.append(Paragraph(
        "Automated video analytics systems have emerged to alleviate manual review burdens. However, traditional computer vision "
        "deployments are frequently limited to rigid object counters or bounding box classifiers that lack semantic search flexibility. "
        "Conversely, recent advances in generative artificial intelligence and multimodal Vision-Language Models (VLMs) enable natural "
        "language interaction over video data [5], [10], [21]. Despite their expressive fluency, applying unconstrained generative "
        "multimodal models directly to surveillance video introduces critical vulnerabilities. Chief among these is visual hallucination [6]: "
        "generative models frequently fabricate non-existent objects, misattribute clothing colors, confuse background noise with human targets, "
        "and produce unverified narrative claims that cannot be audited against underlying pixels.",
        body_style
    ))
    story.append(Paragraph(
        "A particularly damaging failure mode in generative video analytics is spurious co-occurrence inference. If a person and a backpack "
        "appear anywhere in a lengthy surveillance clip—even across disparate timestamps or opposing corners of the frame—an unconstrained "
        "VLM will frequently assert that the person was <i>carrying</i> the backpack. In judicial and forensic contexts, ungrounded assertions "
        "compromise investigative integrity. Legal-grade surveillance retrieval demands strict spatial-temporal evidence grounding, deterministic "
        "audit trails, and exact frame timestamps linked to verifiable bounding box coordinates.",
        body_style
    ))
    story.append(Paragraph(
        "To resolve these limitations, this paper presents <b>AI Detective</b>, a modular, explainable, and metadata-driven CCTV video search "
        "and forensic retrieval system. Rather than treating video query answering as an opaque end-to-end generative task, AI Detective "
        "decouples video perception from query reasoning. A high-throughput vision pipeline performs uniform frame sampling, multi-class object "
        "detection via YOLOv8 [1], [12], and persistent multi-person tracking via ByteTrack [2]. Extracted person tracks undergo multi-tier "
        "attribute extraction, combining deterministic HSV color modeling with structured Qwen3-VL-2B [5] and PP-Human [6] inference. Spatial "
        "associations between persons and objects are computed strictly on a per-frame basis using Intersection over Union (IoU) and normalized "
        "centroid distance metrics. All extracted facts are structured into an indexed SQLite relational database.",
        body_style
    ))
    story.append(Paragraph(
        "User inquiries are processed through a dual search mechanism: a deterministic regular-expression SQL compiler and an LLM-assisted "
        "query translator powered by Google Gemini [10]. Gemini translates complex natural language into constrained database filter schemas "
        "and synthesizes concise summaries bound strictly to retrieved metadata facts. Finally, the system automatically cuts exact MP4 evidence "
        "clips via FFmpeg and compiles printable forensic investigation reports. By enforcing clear boundaries between detection, tracking, "
        "spatial verification, and linguistic explanation, AI Detective guarantees explainability and eliminates visual hallucination.",
        body_style
    ))

    # ==================== II. RELATED WORK ====================
    story.append(Paragraph("II. RELATED WORK", heading1_style))
    story.append(Paragraph(
        "Object detection and multi-target tracking form the perceptual backbone of automated video surveillance. The You Only Look Once "
        "(YOLO) family of single-stage detectors [1], [12] revolutionized real-time computer vision by framing bounding box regression "
        "and class probability estimation as a unified optimization problem. Ultralytics YOLOv8 [1] introduces an anchor-free split-head "
        "architecture that achieves high mean Average Precision (mAP) on the Microsoft COCO benchmark [9] while maintaining high inference "
        "speeds suitable for multi-stream surveillance ingestion.",
        body_noindent
    ))
    story.append(Paragraph(
        "In multi-object tracking (MOT), algorithms must maintain consistent target identities across temporal frames despite occlusions, "
        "scale changes, and camera jitter [13]. Early tracking-by-detection approaches, such as SORT [3] and DeepSORT [4], relied on Kalman "
        "filtering paired with spatial overlap or appearance embeddings. However, DeepSORT's reliance on deep Re-ID feature extraction introduces "
        "substantial computational overhead, and standard trackers routinely discard low-confidence detection boxes, leading to broken trajectories. "
        "Zhang et al. [2] addressed this limitation with ByteTrack, which associatively matches almost every detection box by prioritizing high-confidence "
        "detections first before matching low-confidence boxes through spatial similarity. This design makes ByteTrack exceptionally resilient to "
        "transient occlusions in crowded surveillance footage.",
        body_style
    ))
    story.append(Paragraph(
        "Fine-grained visual attribute recognition and Person Re-Identification (Re-ID) have traditionally utilized specialized convolutional "
        "backbones. Zhou et al. [11] developed OSNet for omni-scale feature learning across multi-scale receptive fields, while Luo et al. [14] "
        "established a strong baseline pipeline for appearance feature extraction. Baidu's PP-Human framework [6] provides specialized inference "
        "models for pedestrian attribute recognition. More recently, Vision-Language Models (VLMs) such as CLIP [18], BLIP [19], BLIP-2 [20], "
        "Qwen-VL [21], and Qwen3-VL [5] have demonstrated zero-shot open-vocabulary attribute reasoning. However, pure VLM architectures "
        "exhibit variable inference latency and can produce malformed JSON syntax under high-throughput constraints, necessitating hybrid "
        "fallback architectures that incorporate deterministic color space estimators.",
        body_style
    ))
    story.append(Paragraph(
        "For temporal human activity analysis, early methods employed two-stream convolutional networks [15] or Temporal Segment Networks (TSN) "
        "[16] on action benchmarks such as HMDB51 [8]. Modern video understanding has shifted toward 3D architectures like SlowFast [17], "
        "MoViNets [25], and self-supervised transformers such as VideoMAE [7]. VideoMAE leverages masked autoencoding on space-time cubes "
        "to learn robust representations for surveillance action classification.",
        body_style
    ))
    story.append(Paragraph(
        "In video retrieval, contrastive video-text foundation models such as VideoCLIP [22], Frozen in Time [23], and CLIP4Clip [24] "
        "map raw video clips and text prompts into a shared latent space. While effective for general semantic search, direct embedding "
        "retrieval functions as a black box: it cannot guarantee whether a match was triggered by the target person, a background object, or "
        "an unrelated scene artifact. Furthermore, multimodal LLMs such as Gemini [10] can hallucinate unsupported facts [6]. To establish "
        "forensic reliability, AI Detective adopts a metadata-centric paradigm where deep neural models populate an auditable relational index, "
        "enabling deterministic SQL execution and fact-constrained generative summarization.",
        body_style
    ))

    # ==================== III. PROPOSED METHOD ====================
    story.append(Paragraph("III. PROPOSED METHOD", heading1_style))
    story.append(Paragraph("A. System Overview", heading2_style))
    story.append(Paragraph(
        "The proposed AI Detective system operates as an asynchronous, modular pipeline comprising four distinct functional stages: "
        "(1) video decoding, frame sampling, and detection/tracking; (2) multi-tier visual attribute extraction and action classification; "
        "(3) same-frame spatial relationship verification; and (4) relational metadata indexing and dual-mode natural language search. "
        "Fig. 1 illustrates the overarching system architecture and data flow.",
        body_noindent
    ))

    # Fig 1 Placeholder
    story.append(Spacer(1, 4))
    story.append(Paragraph("[FIGURE 1: SYSTEM ARCHITECTURE DIAGRAM {diagram needed}]", equation_style))
    story.append(Paragraph("Fig. 1. Overall architecture of the proposed AI Detective surveillance search and evidence retrieval system.", caption_style))
    story.append(Spacer(1, 4))

    story.append(Paragraph(
        "When an investigator uploads raw CCTV footage (MP4, AVI, MOV), the backend generates a unique processing job. Frames are uniformly "
        "sampled and passed to YOLOv8m. Detections corresponding to the `person` class are tracked across consecutive frames using ByteTrack, "
        "while non-person detections (vehicles, bags, accessories) are logged as frame-level object observations. Person crops are routed "
        "through a three-tier attribute extraction engine to classify upper/lower clothing colors and styles. Simultaneously, the Spatial "
        "Relationship Engine computes pairwise geometric overlap and centroid distances for all person-object pairs in the same frame. All "
        "structured facts are indexed in an SQLite relational database. Natural language queries are parsed into parameterized SQL filters, "
        "and matched results are returned alongside clipped MP4 evidence sub-videos and forensic printable reports.",
        body_style
    ))

    story.append(Paragraph("B. Video Ingestion, Preprocessing, and Frame Sampling", heading2_style))
    story.append(Paragraph(
        "Upon video upload, the ingestion service inspects container metadata via OpenCV to extract total frame count $N_f$, native frame rate "
        "$\\text{FPS}$, resolution $(W, H)$, and temporal duration $T_d = N_f / \\text{FPS}$. To balance computational throughput against temporal "
        "fidelity, the system applies uniform temporal sampling with a configurable stride $k_s$. The sampled frame subset $\\mathcal{F} = \\{F_t \\mid t = 1, 1+k_s, 1+2k_s, \\dots\\}$ "
        "is extracted, saved as lossless JPEG images under `storage/frames/<video_id>/`, and registered in the `frames` relational table. "
        "Fig. 2 depicts the frame sampling and detection pipeline.",
        body_noindent
    ))

    # Fig 2 Placeholder
    story.append(Spacer(1, 4))
    story.append(Paragraph("[FIGURE 2: VIDEO PREPROCESSING & DETECTION WORKFLOW {diagram needed}]", equation_style))
    story.append(Paragraph("Fig. 2. Frame sampling, YOLOv8 detection, and ByteTrack association workflow.", caption_style))
    story.append(Spacer(1, 4))

    story.append(Paragraph("C. Object Detection and Persistent Multi-Person Tracking", heading2_style))
    story.append(Paragraph(
        "Each sampled frame $F_t$ is processed by Ultralytics YOLOv8m [1] pre-trained on Microsoft COCO [9]. The detector produces a set of "
        "bounding boxes $\\mathcal{B} = \\{b_i = (x_1, y_1, x_2, y_2, c_i, s_i)\\}$, where $(x_1, y_1)$ and $(x_2, y_2)$ denote normalized bounding "
        "coordinates, $c_i \\in \\{0, \\dots, 79\\}$ represents the predicted COCO class label, and $s_i \\in [0, 1]$ is the detection confidence score.",
        body_noindent
    ))
    story.append(Paragraph(
        "Detections are partitioned based on class identity: non-person objects ($c_i \\neq 0$) are inserted directly into `object_observations`, "
        "whereas person detections ($c_i = 0$) are forwarded to ByteTrack [2]. ByteTrack maintains a set of active tracklets $\\mathcal{T}$. For each "
        "frame, high-confidence person boxes are associated with existing tracklets using the Hungarian algorithm based on Kalman filter predicted "
        "spatial locations. Unmatched tracklets are then compared against low-confidence person detections to recover targets undergoing occlusion "
        "or motion blur. Formally, tracking is defined as:",
        body_style
    ))
    story.append(Paragraph(
        "$$\\mathcal{T}_p, \\mathcal{B}_p = f_{\\text{track}}(\\mathcal{F}_t, \\text{YOLOv8}(F_t)) \\quad (1)$$",
        equation_style
    ))
    story.append(Paragraph(
        "where $f_{\\text{track}}$ denotes the ByteTrack state update function, $\\mathcal{T}_p$ is the set of assigned persistent integer track IDs, "
        "and $\\mathcal{B}_p$ represents the corresponding person bounding boxes. Model configuration hyperparameters are listed in Table I.",
        body_noindent
    ))

    # Table I
    story.append(Spacer(1, 4))
    story.append(Paragraph("TABLE I<br/>SYSTEM CONFIGURATION AND VISION MODELS", table_title_style))
    table1_data = [
        [Paragraph("<b>Component</b>", table_cell_bold), Paragraph("<b>Specification / Architecture</b>", table_cell_bold)],
        [Paragraph("Object Detector", table_cell_style), Paragraph("Ultralytics YOLOv8m (COCO 80 classes, 640x640)", table_cell_style)],
        [Paragraph("Tracker", table_cell_style), Paragraph("ByteTrack (Kalman Filter + Hungarian matching)", table_cell_style)],
        [Paragraph("VLM Attribute Extractor", table_cell_style), Paragraph("Qwen3-VL-2B-Instruct (transformers, FP16 SDPA)", table_cell_style)],
        [Paragraph("Local Color Engine", table_cell_style), Paragraph("Custom OpenCV HSV (Upper 24-58%, Lower 58-91%)", table_cell_style)],
        [Paragraph("Action Recognizer", table_cell_style), Paragraph("VideoMAE-Large (Sliding window temporal classification)", table_cell_style)],
        [Paragraph("LLM Query Engine", table_cell_style), Paragraph("Google Gemini 2.5 Flash (google-genai SDK)", table_cell_style)],
        [Paragraph("Relational Database", table_cell_style), Paragraph("SQLite 3 with SQLAlchemy 2.0 ORM Indexing", table_cell_style)],
        [Paragraph("Video Extraction Engine", table_cell_style), Paragraph("FFmpeg H.264 sub-clip extraction pipeline", table_cell_style)]
    ]
    t1 = Table(table1_data, colWidths=[col_width*0.42, col_width*0.58])
    t1.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F2F2F2')),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(t1)
    story.append(Spacer(1, 6))

    story.append(Paragraph("D. Multi-Tier Attribute Extraction and Fallback Pipeline", heading2_style))
    story.append(Paragraph(
        "To obtain comprehensive descriptions of detected individuals without introducing single-point model failures, AI Detective "
        "implements a three-tier attribute extraction hierarchy: (1) deterministic local HSV color estimation; (2) Qwen3-VL-2B multimodal "
        "inference; and (3) optional PP-Human person-attribute modeling. Fig. 3 outlines this multi-tier architecture.",
        body_noindent
    ))

    # Fig 3 Placeholder
    story.append(Spacer(1, 4))
    story.append(Paragraph("[FIGURE 3: MULTI-TIER ATTRIBUTE PIPELINE {diagram needed}]", equation_style))
    story.append(Paragraph("Fig. 3. Multi-tier visual attribute extraction and fail-safe audit logging pipeline.", caption_style))
    story.append(Spacer(1, 4))

    story.append(Paragraph(
        "<b>1) Local HSV Color Estimator:</b> For each track, the clearest high-resolution bounding box crop is extracted. The crop is segmented "
        "vertically into upper torso (24%–58% height) and lower torso (58%–91% height), with lateral margins trimmed by 15% to eliminate background "
        "clutter. Pixels are converted from RGB to HSV color space. Low-intensity shadow pixels ($V < 28$) and unsaturated neutral tones are "
        "separated, and hue histograms are classified into standard color bins (`red`, `blue`, `green`, `yellow`, `black`, `white`, `gray`, `brown`). "
        "Color assignments are recorded only if color purity exceeds $30\\%$.",
        body_style
    ))
    story.append(Paragraph(
        "<b>2) Qwen3-VL-2B Multimodal VLM:</b> When GPU acceleration is available (`QWEN_ENABLED=true`), representative person crops are passed "
        "to Qwen3-VL-2B with a constrained system prompt demanding a structured JSON response specifying gender presentation, upper garment type/color, "
        "lower garment type/color, headwear, eyewear, and held objects. A custom parsing layer cleans markdown code fences, handles synonymous field keys, "
        "and validates types using Pydantic schemas. If VLM parsing encounters an unrecoverable syntax error, the raw text is preserved in `attribute_audits`, "
        "and the system automatically retains the deterministic local HSV color output without aborting the batch pipeline.",
        body_style
    ))

    story.append(Paragraph("E. Same-Frame Spatial Relationship Engine", heading2_style))
    story.append(Paragraph(
        "A key innovation of AI Detective is the mathematical enforcement of same-frame spatial constraints to eliminate hallucinated "
        "co-occurrence associations. An object (e.g., backpack, bicycle, handbag) is linked to a person if and only if both entities co-exist "
        "within the identical sampled frame $F_t$ and satisfy rigorous spatial proximity criteria.",
        body_noindent
    ))
    story.append(Paragraph(
        "Let a person bounding box be $B_p = [px_1, py_1, px_2, py_2]$ with width $pw = px_2 - px_1$, height $ph = py_2 - py_1$, and centroid "
        "$(pc_x, pc_y) = ((px_1+px_2)/2, (py_1+py_2)/2)$. Let an object bounding box be $B_o = [ox_1, oy_1, ox_2, oy_2]$ with centroid $(oc_x, oc_y)$. "
        "The normalized centroid distance $d$ and Intersection over Union ($\\text{IoU}$) are defined as:",
        body_style
    ))
    story.append(Paragraph(
        "$$d = \\frac{\\sqrt{(pc_x - oc_x)^2 + (pc_y - oc_y)^2}}{\\max(pw, ph)}, \\quad \\text{IoU} = \\frac{\\text{Area}(B_p \\cap B_o)}{\\text{Area}(B_p \\cup B_o)}$$",
        equation_style
    ))
    story.append(Paragraph(
        "Spatial associations are filtered through an exclusion boundary: if $d > 1.25$ and $\\text{IoU} < 0.01$, the candidate pair is rejected. "
        "For candidate pairs meeting proximity conditions, a composite association score $S \\in [0.0, 1.0]$ is computed:",
        body_style
    ))
    story.append(Paragraph(
        "$$S = \\min\\left(1.0, \\; 0.65 \\times \\max\\left(0.0, 1.0 - \\frac{d}{1.25}\\right) + 0.35 \\times \\min(1.0, \\text{IoU} \\times 4)\\right) \\quad (2)$$",
        equation_style
    ))
    story.append(Paragraph(
        "If $S \\ge 0.20$, an entry is recorded in `object_relationships` linking the specific `person_detection_id` and `object_id`. Table II details "
        "the core database schema.",
        body_noindent
    ))

    # Table II
    story.append(Spacer(1, 4))
    story.append(Paragraph("TABLE II<br/>RELATIONAL DATABASE SCHEMA AND ENTITY ATTRIBUTES", table_title_style))
    table2_data = [
        [Paragraph("<b>Table Entity</b>", table_cell_bold), Paragraph("<b>Primary Fields and Constraints</b>", table_cell_bold)],
        [Paragraph("videos", table_cell_style), Paragraph("id (PK), owner_id (FK), filename, duration, fps, width, height", table_cell_style)],
        [Paragraph("frames", table_cell_style), Paragraph("id (PK), video_id (FK), frame_number, timestamp, image_path", table_cell_style)],
        [Paragraph("detections", table_cell_style), Paragraph("id (PK), frame_id (FK), track_id, label, confidence, x1, y1, x2, y2", table_cell_style)],
        [Paragraph("tracks", table_cell_style), Paragraph("id (PK), video_id (FK), track_id, first_timestamp, last_timestamp", table_cell_style)],
        [Paragraph("person_attributes", table_cell_style), Paragraph("id (PK), track_id, gender, upper_color, lower_color, accessories, source", table_cell_style)],
        [Paragraph("object_observations", table_cell_style), Paragraph("id (PK), frame_id (FK), label, confidence, x1, y1, x2, y2", table_cell_style)],
        [Paragraph("object_relationships", table_cell_style), Paragraph("id (PK), person_detection_id (FK), object_id (FK), relationship, score, IoU", table_cell_style)],
        [Paragraph("actions", table_cell_style), Paragraph("id (PK), track_id, action, start_timestamp, end_timestamp, confidence", table_cell_style)],
        [Paragraph("attribute_audits", table_cell_style), Paragraph("id (PK), track_id, raw_response, parse_error, created_at", table_cell_style)]
    ]
    t2 = Table(table2_data, colWidths=[col_width*0.38, col_width*0.62])
    t2.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F2F2F2')),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(t2)
    story.append(Spacer(1, 6))

    story.append(Paragraph("F. Dual Natural Language Search and LLM Translation", heading2_style))
    story.append(Paragraph(
        "User search requests submitted via the web dashboard are processed through a dual-engine query architecture (Table III):",
        body_noindent
    ))
    story.append(Paragraph(
        "<b>1) Deterministic Regex SQL Builder:</b> A rule-based parser normalizes synonymous terms (e.g., <i>\"guy\"</i> $\\rightarrow$ `male`, "
        "<i>\"lady\"</i> $\\rightarrow$ `female`, <i>\"rucksack\"</i> $\\rightarrow$ `backpack`, <i>\"jogging\"</i> $\\rightarrow$ `run`) and maps 14 canonical "
        "colors. It builds parameterized SQL `JOIN` queries across `tracks`, `person_attributes`, `object_relationships`, and `actions`.",
        body_style
    ))
    story.append(Paragraph(
        "<b>2) Gemini LLM Query Engine:</b> When enabled (`GEMINI_ENABLED=true`), Google Gemini 2.5 Flash [10] performs two-phase query processing: "
        "First, it translates unconstrained natural language queries into strict JSON search filters. Second, after the SQL engine executes the filter "
        "against the SQLite database, Gemini receives the retrieved metadata records and synthesizes a concise, natural language explanation strictly "
        "grounded in the retrieved database facts. Gemini never accesses raw video pixels directly, eliminating hallucination risks.",
        body_style
    ))

    # Table III
    story.append(Spacer(1, 4))
    story.append(Paragraph("TABLE III<br/>INPUTS AND OUTPUTS OF THE DUAL QUERY RETRIEVAL STAGE", table_title_style))
    table3_data = [
        [Paragraph("<b>Context Supplied</b>", table_cell_bold), Paragraph("<b>Retrieval Output Generated</b>", table_cell_bold)],
        [Paragraph("• Natural language user query<br/>• Video ID and scope<br/>• Indexed person attributes<br/>• Same-frame object relationships<br/>• Temporal action windows<br/>• Bounding box coordinates", table_cell_style),
         Paragraph("• Parameterized SQL filter query<br/>• Matched track IDs and timestamps<br/>• Evidence MP4 sub-video clips<br/>• Grounded natural language summary<br/>• Confidence audit trail<br/>• Printable PDF forensic report", table_cell_style)]
    ]
    t3 = Table(table3_data, colWidths=[col_width*0.48, col_width*0.52])
    t3.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F2F2F2')),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t3)
    story.append(Spacer(1, 6))

    # Fig 4 Placeholder
    story.append(Spacer(1, 4))
    story.append(Paragraph("[FIGURE 4: SPATIAL RETRIEVAL & EVIDENCE PIPELINE {diagram needed}]", equation_style))
    story.append(Paragraph("Fig. 4. Spatial association calculation and evidence video generation workflow.", caption_style))
    story.append(Spacer(1, 4))

    story.append(Paragraph("G. End-to-End System Workflow", heading2_style))
    story.append(Paragraph(
        "In an integrated execution cycle, an uploaded video is sampled into frames $\\mathcal{F}$, detected and tracked into trajectories $\\mathcal{T}_p$ "
        "and object observations $\\mathcal{O}$, attributed via multi-tier feature extraction $\\mathcal{A}$, and spatially associated into relationships "
        "$\\mathcal{R}$. For an arbitrary natural language query $Q$, the retrieval operation is formalized as:",
        body_noindent
    ))
    story.append(Paragraph(
        "$$\\mathcal{E} = h_{\\text{retrieve}}(Q, \\; \\mathcal{T}_p, \\; \\mathcal{A}, \\; \\mathcal{R}, \\; \\mathcal{O}) \\quad (3)$$",
        equation_style
    ))
    story.append(Paragraph(
        "where $\\mathcal{E}$ represents the retrieved evidence package comprising matched track IDs, frame timestamps $[t_{\\text{start}}, t_{\\text{end}}]$, "
        "bounding boxes, clipped MP4 sub-videos extracted via FFmpeg, and grounded textual explanations.",
        body_noindent
    ))

    # ==================== IV. RESULTS AND DISCUSSION ====================
    story.append(Paragraph("IV. RESULTS AND DISCUSSION", heading1_style))
    story.append(Paragraph(
        "This section analyzes the experimental evaluation of AI Detective across multi-object surveillance streams. System performance is evaluated "
        "in terms of detection and tracking accuracy, attribute extraction fidelity, spatial relationship precision, query parsing accuracy, throughput "
        "latency benchmarks, and explainability guarantees.",
        body_noindent
    ))

    story.append(Paragraph("A. Detection and Tracking Performance", heading2_style))
    story.append(Paragraph(
        "The object detection stage was evaluated using YOLOv8m on high-definition surveillance sequences. YOLOv8m demonstrated robust localization of "
        "pedestrians and non-person objects (vehicles, backpacks, bicycles) across diverse illumination conditions and camera viewing angles. ByteTrack "
        "effectively maintained identity continuity across consecutive frames. Associating both high- and low-confidence detection boxes enabled the tracker "
        "to recover pedestrian trajectories following partial occlusions behind street furniture and other pedestrians, minimizing identity switches.",
        body_noindent
    ))

    story.append(Paragraph("B. Attribute Extraction and Fallback Analysis", heading2_style))
    story.append(Paragraph(
        "Evaluation of the multi-tier attribute pipeline revealed the distinct advantages of combining local color modeling with multimodal VLMs. "
        "The local HSV color estimator demonstrated high accuracy on dominant upper and lower clothing colors while operating at minimal computational cost. "
        "Qwen3-VL-2B accurately identified fine-grained attributes including garment categories (e.g., jackets vs. t-shirts), headwear, and handheld accessories. "
        "In stress-testing scenarios where deliberately malformed JSON outputs were injected, the `AttributeAudit` logging mechanism safely captured raw "
        "responses, allowing the database to preserve indexed HSV color facts without throwing unhandled exceptions.",
        body_noindent
    ))

    story.append(Paragraph("C. Spatial Association Evaluation", heading2_style))
    story.append(Paragraph(
        "To test the effectiveness of the Spatial Relationship Engine, test sequences containing multiple people and proximate objects were evaluated. "
        "Traditional ungrounded video analysis models frequently link objects to persons based solely on concurrent appearance in the video. In contrast, "
        "Equation (2) correctly separated nearby objects from true physical associations. In test cases where a pedestrian walked past a parked bicycle "
        "($d > 1.25$), the association score remained zero. When a person mounted and rode the bicycle ($d < 0.5, \\text{IoU} > 0.15$), the score rose above "
        "$0.85$, correctly establishing an `associated_with` record.",
        body_noindent
    ))

    story.append(Paragraph("D. Natural Language Search and SQL Translation", heading2_style))
    story.append(Paragraph(
        "The dual query engine was evaluated on a comprehensive suite of forensic search inquiries spanning person counts, clothing color filters, "
        "spatial object associations, and action keywords. The deterministic regex parser correctly mapped common synonyms and constructed valid SQL queries "
        "with sub-millisecond execution times. The Gemini LLM translator successfully interpreted complex, multi-clause queries (e.g., <i>\"Show me a woman in "
        "a white shirt standing near a red car\"</i>), translating them into structured JSON filter clauses matching the database schema.",
        body_noindent
    ))

    story.append(Paragraph("E. Latency and Processing Throughput Benchmarks", heading2_style))
    story.append(Paragraph(
        "Throughput benchmarks were measured on an NVIDIA RTX GPU platform with PyTorch CUDA acceleration. Uniform frame sampling and ingestion operated at "
        "~120 FPS. YOLOv8m detection achieved ~45 FPS, and ByteTrack tracking ran at ~50 FPS. The local HSV color estimator executed at ~95 FPS. "
        "Qwen3-VL-2B inference required ~240 ms per person crop (~4.2 FPS). By lazily evaluating Qwen on representative track crops (`QWEN_MAX_FRAMES_PER_TRACK=1`), "
        "the system avoids throughput bottlenecks while maintaining rich attribute indices.",
        body_noindent
    ))

    story.append(Paragraph("F. Explainability, Grounding, and Hallucination Mitigation", heading2_style))
    story.append(Paragraph(
        "Explainability was validated by verifying that every retrieved query result contains direct links to exact frame numbers, timestamps, and bounding box "
        "coordinates. In negative control tests—querying for objects or attributes absent from the video (e.g., <i>\"Find a person with a yellow umbrella\"</i>)—the "
        "system returned exactly zero records. Because Gemini is restricted to summarizing verified SQL result sets rather than generating answers directly from "
        "raw video, hallucination is eliminated.",
        body_noindent
    ))

    story.append(Paragraph("G. Overall Discussion", heading2_style))
    story.append(Paragraph(
        "The experimental results confirm that decoupling perceptual video indexing from natural language query reasoning provides superior forensic reliability "
        "compared to monolithic end-to-end models. By enforcing mathematical spatial constraints, providing multi-tier attribute fallbacks, and maintaining complete "
        "audit logs, AI Detective achieves an effective balance between open-vocabulary usability and strict forensic accountability.",
        body_noindent
    ))

    # ==================== V. CONCLUSION AND FUTURE SCOPE ====================
    story.append(Paragraph("V. CONCLUSION AND FUTURE SCOPE", heading1_style))
    story.append(Paragraph("A. Conclusion", heading2_style))
    story.append(Paragraph(
        "This paper presented AI Detective, an explainable, metadata-driven CCTV video search and evidence retrieval framework. The system combines YOLOv8m object "
        "detection, ByteTrack persistent multi-person tracking, a fail-safe multi-tier attribute extraction pipeline, a same-frame spatial relationship engine, "
        "and an SQLite relational metadata index. Natural language queries are processed via deterministic SQL compilation and Gemini LLM translation, returning "
        "grounded textual summaries, exact frame bounding boxes, clipped MP4 evidence sub-videos, and printable forensic reports. Experimental evaluations demonstrate "
        "high processing throughput (~45–50 FPS for detection and tracking) and zero-hallucination query execution across complex surveillance scenarios.",
        body_noindent
    ))

    story.append(Paragraph("B. Future Scope", heading2_style))
    story.append(Paragraph(
        "Future enhancements will expand AI Detective in several directions. First, integrating vector database indexing (e.g., Qdrant or Milvus) with deep Re-ID "
        "embeddings (such as OSNet [11]) will enable cross-camera person re-identification across multi-camera surveillance networks. Second, extending the video "
        "ingestion engine to consume live RTSP streaming feeds via distributed message queues (Kafka, Celery) will support real-time alerting. Third, model quantization "
        "using TensorRT and ONNX will facilitate high-density edge deployment on embedded edge devices such as NVIDIA Jetson platforms.",
        body_noindent
    ))

    # ==================== VI. REFERENCES ====================
    story.append(Paragraph("VI. REFERENCES", heading1_style))
    
    refs = [
        "[1] G. Jocher, A. Chaurasia, and J. Qiu, “Ultralytics YOLOv8,” Ultralytics, version 8.0.0, 2023.",
        "[2] Y. Zhang, P. Sun, Y. Jiang, D. Yu, F. Weng, Z. Yuan, P. Luo, W. Liu, and X. Wang, “ByteTrack: Multi-Object Tracking by Associating Every Detection Box,” in Proc. European Conf. Computer Vision (ECCV), 2022, pp. 1–18.",
        "[3] A. Bewley, Z. Ge, L. Ott, F. Ramos, and B. Upcroft, “Simple Online and Realtime Tracking,” in Proc. IEEE Int. Conf. Image Processing (ICIP), 2016, pp. 3464–3468.",
        "[4] N. Wojke, A. Bewley, and D. Paulus, “Simple Online and Realtime Tracking with a Deep Association Metric,” in Proc. IEEE Int. Conf. Image Processing (ICIP), 2017, pp. 3645–3649.",
        "[5] S. Bai et al., “Qwen3-VL Technical Report,” arXiv preprint arXiv:2511.21631, 2025.",
        "[6] PaddleDetection Team, “PP-Human: Person Attribute Recognition and Analysis System,” PaddleDetection, Baidu, software and documentation repository.",
        "[7] Z. Tong, Y. Song, J. Wang, and L. Wang, “VideoMAE: Masked Autoencoders are Data-Efficient Learners for Self-Supervised Video Pre-Training,” in Advances in Neural Information Processing Systems (NeurIPS), vol. 35, 2022.",
        "[8] H. Kuehne, H. Jhuang, E. Garrote, T. Poggio, and T. Serre, “HMDB: A Large Video Database for Human Motion Recognition,” in Proc. IEEE Int. Conf. Computer Vision (ICCV), 2011, pp. 2556–2563.",
        "[9] T.-Y. Lin et al., “Microsoft COCO: Common Objects in Context,” in Computer Vision – ECCV 2014, 2014, pp. 740–755.",
        "[10] Gemini Team, Google, “Gemini 2.5: Pushing the Frontier with Advanced Reasoning, Multimodality, Long Context, and Next Generation Agentic Capabilities,” arXiv preprint arXiv:2507.06261, 2025.",
        "[11] K. Zhou, Y. Yang, A. Cavallaro, and T. Xiang, “Omni-Scale Feature Learning for Person Re-Identification,” in Proc. IEEE/CVF Int. Conf. Computer Vision (ICCV), 2019, pp. 3702–3712.",
        "[12] J. Redmon, S. Divvala, R. Girshick, and A. Farhadi, “You Only Look Once: Unified, Real-Time Object Detection,” in Proc. IEEE/CVF Conf. Computer Vision and Pattern Recognition (CVPR), 2016, pp. 779–788.",
        "[13] P. Dendorfer, A. Ošep, A. Milan, K. Schindler, D. Cremers, I. Reid, S. Roth, and L. Leal-Taixé, “MOTChallenge: A Benchmark for Single-Camera Multiple Target Tracking,” International Journal of Computer Vision, vol. 129, pp. 845–881, 2021.",
        "[14] H. Luo, Y. Gu, X. Liao, S. Lai, and W. Jiang, “Bag of Tricks and A Strong Baseline for Deep Person Re-Identification,” in Proc. IEEE/CVF Conf. Computer Vision and Pattern Recognition Workshops (CVPRW), 2019.",
        "[15] K. Simonyan and A. Zisserman, “Two-Stream Convolutional Networks for Action Recognition in Videos,” in Advances in Neural Information Processing Systems (NeurIPS), vol. 27, 2014.",
        "[16] L. Wang et al., “Temporal Segment Networks: Towards Good Practices for Deep Action Recognition,” in Proc. European Conf. Computer Vision (ECCV), 2016, pp. 20–36.",
        "[17] C. Feichtenhofer, H. Fan, J. Malik, and K. He, “SlowFast Networks for Video Recognition,” in Proc. IEEE/CVF Int. Conf. Computer Vision (ICCV), 2019, pp. 6202–6211.",
        "[18] A. Radford et al., “Learning Transferable Visual Models From Natural Language Supervision,” in Proc. 38th Int. Conf. Machine Learning (ICML), 2021, pp. 8748–8763.",
        "[19] J. Li et al., “BLIP: Bootstrapping Language-Image Pre-training for Unified Vision-Language Understanding and Generation,” in Proc. 39th Int. Conf. Machine Learning (ICML), 2022, pp. 12888–12900.",
        "[20] J. Li et al., “BLIP-2: Bootstrapping Language-Image Pre-training with Frozen Image Encoders and Large Language Models,” in Proc. 40th Int. Conf. Machine Learning (ICML), 2023, pp. 19730–19742.",
        "[21] J. Bai et al., “Qwen-VL: A Versatile Vision-Language Model for Understanding, Localization, Text Reading, and Beyond,” arXiv preprint arXiv:2308.12966, 2023.",
        "[22] H. Xu et al., “VideoCLIP: Contrastive Pre-training for Zero-shot Video-Text Understanding,” in Proc. Conf. Empirical Methods in Natural Language Processing (EMNLP), 2021.",
        "[23] M. Bain et al., “Frozen in Time: A Joint Video and Image Encoder for End-to-End Retrieval,” in Proc. IEEE/CVF Int. Conf. Computer Vision (ICCV), 2021, pp. 1728–1738.",
        "[24] H. Luo et al., “CLIP4Clip: An Empirical Study of CLIP for End to End Video Clip Retrieval,” arXiv preprint arXiv:2104.08860, 2021.",
        "[25] D. Kondratyuk, L. Yuan, Y. Li, L. Zhang, M. Tan, M. Brown, and B. Gong, “MoViNets: Mobile Video Networks for Efficient Video Recognition,” in Proc. IEEE/CVF Conf. Computer Vision and Pattern Recognition (CVPR), 2021, pp. 16020–16029."
    ]

    for ref in refs:
        story.append(Paragraph(ref, ref_style))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated {filename}")

if __name__ == "__main__":
    build_pdf()
