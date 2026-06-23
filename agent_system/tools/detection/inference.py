import torch
from ultralytics import YOLO


class YoloPredictor:
    def __init__(self, model_path: str):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = YOLO(model_path).to(self.device)

    def predict(self, frame, imgsz=640, conf=0.07, iou=0.7, max_det=300, **kwargs):
        result = self.model.predict(
            source=frame,
            imgsz=imgsz,
            conf=conf,
            iou=iou,
            device=self.device,
            max_det=max_det,
            verbose=False,
            **kwargs,
        )[0]
        return process_predicted_results(result)

def process_predicted_results(result):
    boxes = result.boxes.xyxy
    confidences = result.boxes.conf
    classes = result.boxes.cls

    if isinstance(boxes, torch.Tensor):
        boxes = boxes.tolist()
    if isinstance(confidences, torch.Tensor):
        confidences = confidences.tolist()
    if isinstance(classes, torch.Tensor):
        classes = classes.tolist()

    data_list = [box + [conf, cls] for box, conf, cls in zip(boxes, confidences, classes)]
    return torch.tensor(data_list, dtype=torch.float32)
