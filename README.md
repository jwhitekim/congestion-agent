# 사람 머리 탐지와 선 밀도 분석을 이용한 실시간 전이학습 기반 실내 혼잡도 분석 시스템

**Real-time Indoor Congestion Analysis System Using Transfer Learning-based Head Detection and Line Density Analysis**

![Python](https://img.shields.io/badge/Python-3.10-blue?logo=python)
![Django](https://img.shields.io/badge/Django-5.2-092E20?logo=django)
![YOLOv8](https://img.shields.io/badge/YOLOv8m-Ultralytics-FF6B35)
![mAP50](https://img.shields.io/badge/mAP50-0.9247-brightgreen)
![License](https://img.shields.io/badge/License-MIT-green)

전이학습 기반 사람 머리 탐지(YOLOv8m), OC-SORT 객체 추적, 그리고 객체 간 **연결선 밀도(Line Density)** 알고리즘을 결합하여 카메라 한 대만으로 실내 공간의 혼잡도를 실시간 4단계로 분류하고 웹 대시보드에 스트리밍하는 시스템입니다.

> Transfer learning-based head detection (YOLOv8m) + OC-SORT tracking + novel **line density algorithm** — classifies indoor congestion into 4 levels in real time using a single camera, no dedicated hardware required.

---

## Demo

<!-- Add dashboard screenshot here: docs/assets/dashboard.png -->
<!-- Add YOLO inference result here: docs/assets/inference.png -->

> Screenshots coming soon. See [docs/how_to_run.md](docs/README.md) to run locally.

---

## How It Works

The system is composed of **6 modules** that form a real-time analysis pipeline:

```
① Video Input
      ↓
② Head Detection  (YOLOv8m, transfer-learned on AI-Hub indoor crowd data)
      ↓
③ Object Tracking  (OC-SORT — stable IDs across frames, prevents duplicate counting)
      ↓
④ Line Density Calculation  (Euclidean distance between object pairs → edge count)
      ↓
⑤ Congestion Classification  (calibrated thresholds → 4-level label)
      ↓
⑥ Web Dashboard  (Django REST API + MJPEG stream, 30 FPS+)
```

### Why Line Density?

Simple person-count-to-area ratios produce negligibly small values because the frame area (pixels²) dwarfs the object count. Instead, this system treats every detected head as a **node** and draws an **edge** between any two nodes within a configurable distance threshold. The **count of edges** reflects how tightly people are clustered, and is mapped to one of four congestion levels using calibrated thresholds.

| Level | Label |
|-------|-------|
| 1 | Normal (여유) |
| 2 | Common (보통) |
| 3 | Crowded (혼잡) |
| 4 | Very Crowded (매우 혼잡) |

---

## Model Performance

The head detection model was fine-tuned from COCO-pretrained YOLOv8m weights using the **AI-Hub Indoor/Outdoor Crowd Characteristic Dataset** (train/val split = 8:2).

| Metric | Score |
|--------|-------|
| Precision | 0.908 |
| Recall | 0.907 |
| **mAP50** | **0.9247** |
| mAP50-95 | 0.6768 |

<!-- Add performance graph or confusion matrix here: docs/assets/metrics.png -->

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Object Detection | YOLOv8m (Ultralytics) |
| Object Tracking | OC-SORT |
| Congestion Prediction | RandomForestRegressor (scikit-learn) |
| Backend | Django 5.2, Django REST Framework |
| Video Streaming | MJPEG via `StreamingHttpResponse` (30 FPS+) |
| Frontend | Vanilla JavaScript, HTML5, CSS3 |
| Deployment | Gunicorn + Nginx on AWS EC2 |

---

## Project Structure

```
AnEmptySeat/
├── backend/
│   └── videostream/
│       ├── views.py                    # Detection, streaming & API views
│       └── analytics/
│           ├── calc_spatial_density.py # Line density algorithm (core)
│           ├── congestion_calc.py      # 4-level classification
│           └── prediction_system.py    # RandomForest future prediction
├── frontend/
│   └── static/script.js               # Vanilla JS dashboard (fetch + setInterval)
├── models/
│   ├── best_model.joblib               # Serialized RandomForest
│   └── *.pt                            # YOLOv8 weights
├── docs/
│   └── how_to_run.md
├── calibrate.py       # Calibrate congestion thresholds from sample footage
├── generate_data.py   # Generate simulated training data
├── train_model.py     # Re-train the prediction model
├── generate_video.py  # Create synthetic test video
├── manage.py
└── requirements.txt
```

---

## API Endpoints

| Endpoint | Description | Update Rate |
|----------|-------------|-------------|
| `GET /` | Main dashboard | — |
| `GET /stream/<name>/` | Live stream page | — |
| `GET /stream/video_feed/` | MJPEG video stream | Real-time |
| `GET /stream/status/<name>/` | Person count + congestion level (JSON) | Every 5 s |
| `GET /stream/api/predictions/` | Future congestion forecast (JSON) | Every 10 s |

---

## Getting Started

See [docs/how_to_run.md](docs/how_to_run.md) for the full setup guide.

```bash
pip install -r requirements.txt
python manage.py runserver
```

<details>
<summary>Utility scripts</summary>

| Script | Purpose |
|--------|---------|
| `calibrate.py` | Compute optimal congestion thresholds from sample footage |
| `generate_data.py` | Generate simulated hour/day occupancy data for training |
| `train_model.py` | Re-train and serialize the RandomForest model |
| `generate_video.py` | Create synthetic test video clips |

</details>

<details>
<summary>Known limitations & future work</summary>

| Area | Current Limitation | Planned Improvement |
|------|--------------------|---------------------|
| Prediction data | Trained on simulated data; real-world variables absent | Retrain on weeks of real in-store data |
| Occlusion | Overlapping people or furniture can be missed | Top-view camera angle; heavier model variant |
| Scalability | MJPEG streaming is CPU-intensive under many viewers | Nginx RTMP / WebRTC / HLS-DASH |
| Prediction model | RandomForest with hand-crafted features | LSTM for proper time-series modelling |
| Perspective | 2D pixel distances ignore camera depth distortion | Homography correction for real-world distances |

</details>

---

## Acknowledgements

- [Ultralytics YOLOv8](https://docs.ultralytics.com/ko/models/yolov8/)
- [OC-SORT](https://arxiv.org/abs/2203.14360) — Observation-Centric SORT
- [AI-Hub Indoor/Outdoor Crowd Characteristic Dataset](https://aihub.or.kr)
- Capstone Design 2025, Department of Electronic Engineering, KNUT
  - Advisor: Prof. Song Chang-ik
  - Team DongJunSu: Kim Dong-in (2222007), Kim Jun-hee (2122014)
