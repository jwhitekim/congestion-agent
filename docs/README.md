# AnEmptySeat 실행 가이드

실시간 혼잡도 감지 웹 애플리케이션 (Django + YOLOv8 + OCSort)

---

## 프로젝트 구조 요약

```
AnEmptySeat/
├── backend/          # Django 백엔드 (API, YOLO 추론, 혼잡도 분석)
├── frontend/         # 웹 UI (HTML, CSS, JS)
├── models/           # 사전 학습된 ML 모델 (.pt, .pkl)
├── docs/             # 문서
├── manage.py         # Django 진입점
├── requirements.txt  # Python 의존성
└── .env              # 환경 변수 (SECRET_KEY)
```

---

## 1. Windows에서 실행 (개발 환경)

### 1-1. Conda 환경 설정

`docs/install_in_windows.txt` 참고:

```bash
# 콘다 환경 생성 (Python 3.10 필수)
conda create -n anemptyseat python=3.10 -y
conda activate anemptyseat

# 기본 패키지 설치
conda install -c conda-forge numpy scipy matplotlib pillow networkx sympy -y

# PyTorch 설치 (CPU 전용)
conda install pytorch torchvision torchaudio cpuonly -c pytorch

# 나머지 패키지 설치
pip install ultralytics filterpy scikit-learn opencv-python

# lap 패키지 (conda-forge 채널 사용)
conda install -c conda-forge lap pyqt -y

# 웹/서버 패키지 설치
pip install chromedriver-autoinstaller requests selenium selenium-stealth django python-decouple

# OCSort (의존성 없이 설치)
pip install ocsort --no-deps
```

> GPU를 사용하는 경우 PyTorch 설치 시 `cpuonly` 대신 CUDA 버전을 선택하세요.

### 1-2. 환경 변수 설정

프로젝트 루트에 `.env` 파일이 있는지 확인:

```
SECRET_KEY=your_secret_key_here
```

`.env` 파일이 없다면 생성:

```bash
echo "SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')" > .env
```

### 1-3. 개발 서버 실행

```bash
# 프로젝트 루트에서 실행 (manage.py가 있는 위치)
conda activate anemptyseat
python manage.py runserver
```

브라우저에서 `http://127.0.0.1:8000` 접속

---

## 2. Linux / Ubuntu에서 실행

### 2-1. Python 3.10 설치

```bash
sudo apt install software-properties-common -y
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.10 python3.10-venv -y
```

### 2-2. 가상 환경 설정

```bash
cd ~/AnEmptySeat

# 가상 환경 생성 및 활성화
python3.10 -m venv venv
source venv/bin/activate

pip install --upgrade pip setuptools wheel
```

### 2-3. 의존성 설치

```bash
# 기본 패키지
pip install numpy scipy opencv-python matplotlib pillow networkx sympy

# PyTorch CPU 전용
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# ML / 추론 패키지
pip install ultralytics filterpy scikit-learn lapx PyQt5

# 웹 / 서버 패키지
pip install chromedriver-autoinstaller requests selenium selenium-stealth django python-decouple

# OCSort (의존성 없이 설치)
pip install ocsort --no-deps
```

### 2-4. 개발 서버 실행

```bash
source venv/bin/activate
python manage.py runserver 0.0.0.0:8000
```

브라우저에서 `http://<서버IP>:8000` 접속

---

## 3. 프로덕션 배포 (Gunicorn + Nginx)

### 3-1. Gunicorn으로 실행

```bash
source venv/bin/activate
gunicorn --bind 127.0.0.1:8000 backend.config.wsgi:application
```

### 3-2. Gunicorn 서비스 관리 (systemd)

```bash
# 서비스 파일 등록
sudo systemctl daemon-reload

# 서비스 시작 및 자동 시작 설정
sudo systemctl start gunicorn
sudo systemctl enable gunicorn

# 상태 확인
sudo systemctl status gunicorn

# 재시작
sudo systemctl restart gunicorn
```

### 3-3. Nginx 재시작

```bash
sudo systemctl restart nginx
```

---

## 4. 주요 URL

| URL | 설명 |
|-----|------|
| `http://localhost:8000/` | 메인 대시보드 |
| `http://localhost:8000/stream/<영상명>/` | 실시간 스트림 |
| `http://localhost:8000/stream/api/predictions/` | 혼잡도 예측 API |

---

## 5. 모델 및 보조 스크립트

```bash
# 혼잡도 임계값 캘리브레이션
python calibrate.py

# 학습 데이터 생성
python generate_data.py

# 테스트 영상 생성
python generate_video.py

# 예측 모델 재학습
python train_model.py
```

---

## 6. 트러블슈팅

| 증상 | 해결 방법 |
|------|-----------|
| `lap` 설치 오류 (Windows) | `conda install -c conda-forge lap -y` 사용 |
| `lap` 설치 오류 (Linux) | `pip install lapx` 사용 |
| YOLO 모델 로드 실패 | `models/` 폴더에 `.pt` 파일이 있는지 확인 |
| 포트 충돌 | `python manage.py runserver 0.0.0.0:8080` 으로 포트 변경 |
| `SECRET_KEY` 오류 | 프로젝트 루트에 `.env` 파일 존재 여부 확인 |
| GPU 미사용 | PyTorch CUDA 버전 설치 필요 (`cpuonly` 제거 후 CUDA 빌드 설치) |
