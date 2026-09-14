# 카메라 OCR — Expo + 서버

폰으로 찍으면 노트북 서버가 읽어서 돌려줍니다.

```
폰 (Expo)  --사진-->  노트북 (FastAPI)  -->  OCR 엔진
           <--결과--
```

---

## OCR 엔진

`rapidocr` 3.x의 PP-OCR 계열 ONNX 모델을 쓴다. **torch를 안 쓴다.**

이 노트북에서 EasyOCR은 못 쓴다. Smart App Control이 torch의 서명 없는 DLL을 막는다.

```
import torch -> OSError [WinError 4551] 애플리케이션 제어 정책에서 이 파일을 차단
```

### 실측 (샘플 5장, 서버를 띄워 HTTP로 확인)

| 설정 | 평균 CER | 이미지당 |
|---|---:|---:|
| `OCR_QUALITY=fast` (기본) | 0.32 | 1.4초 |
| `OCR_QUALITY=accurate` | **0.08** | 9초 |

둘은 글자를 **찾는** 모델만 다르다. 읽는 모델은 같다.
라이브 데모는 fast, 정확도를 보여줄 때만 accurate로 바꾸면 된다.

개별 결과 (fast 기준)

| 정답 | 인식 | 신뢰도 |
|---|---|---:|
| 영수증 합계 12500원 | `영수증 합계 12500원 \|` | 0.995 |
| 주문번호 A-2026-0908 | `주문번호 A-2026-0908` | 0.980 |

폰 사진 크기(4000px)를 1600px로 줄여 **0.84초**.

### 환경변수

```bash
set OCR_LANG=korean        # korean(기본) / ch / en / japan ...
set OCR_QUALITY=accurate   # fast(기본) / accurate
set MAX_SIDE=800           # 서버가 줄일 긴 변 (기본 1600)
```

엔진 자체를 바꿀 수도 있다.

```bash
set OCR_ENGINE=clova
set CLOVA_URL=...
set CLOVA_SECRET=...
```

| 엔진 | 한글 | 이 노트북 |
|---|---|---|
| `rapidocr` (기본) | 좋음 | 동작 확인 |
| `easyocr` | 좋음 | 불가 (torch 차단) |
| `clova` | 매우 좋음 | 가능 (키 필요, 이미지가 외부로 나감) |

모델은 처음 실행할 때 자동으로 받아서 캐시에 둔다. **세션 전에 한 번 돌려둘 것.**

## 1. 서버 띄우기

```bash
cd server
pip install -r requirements.txt
python main.py
```

띄우면 폰에서 접속할 주소가 찍힙니다.

```
==========================================================
  준비 완료. 폰에서 아래 주소로 접속하세요.

      http://192.168.0.10:8000

  폰과 노트북이 같은 와이파이에 있어야 합니다.
==========================================================
```

엔진을 바꾸려면 환경변수만 주면 됩니다.

```bash
set OCR_QUALITY=accurate        # 정확도 우선 (느려짐)
set OCR_LANG=en                 # 영어 전용
```

CLOVA를 쓸 때는 두 개를 더 줍니다.

```bash
set OCR_ENGINE=clova
set CLOVA_URL=https://...apigw.ntruss.com/custom/v1/.../general
set CLOVA_SECRET=...
```

### 잘 되는지 먼저 확인

```bash
curl http://localhost:8000/health
```

## 2. 앱 띄우기

```bash
npx create-expo-app app --template blank
cd app
npx expo install expo-camera
```

만들어진 `App.js`를 이 폴더의 `App.js`로 덮어씁니다.
그리고 **맨 위 `SERVER` 주소를 서버가 알려준 주소로 바꿉니다.**

```js
const SERVER = 'http://192.168.0.10:8000';
```

```bash
npx expo start
```

폰의 Expo Go 앱으로 QR을 찍습니다. **카메라는 시뮬레이터에서 안 되니 실물 폰이 필요합니다.**

## 3. 안 될 때

| 증상 | 원인 |
|---|---|
| 앱에서 요청이 그냥 멈춤 | 폰과 노트북이 다른 와이파이 |
| Network request failed | `SERVER` 주소가 틀렸거나 방화벽 |
| 서버 로그에 아무것도 안 찍힘 | 요청이 도달을 못 한 것 — 방화벽부터 보세요 |
| 글자가 누워서 인식됨 | 서버가 EXIF 회전을 이미 처리합니다. 그래도 이상하면 알려주세요 |
| 첫 요청만 엄청 느림 | 엔진이 그때 로딩된 것. 서버는 시작할 때 미리 만들어 둡니다 |

설치부터 촬영까지 따라 하는 순서는 [SETUP.md](SETUP.md) 에 있습니다.
팀원들에게는 그 파일을 주세요.

## 4. 세션에서 볼 것

앱이 측정값을 같이 보여줍니다. 이게 6주차 서빙 내용과 이어집니다.

```
OCR 시간     서버가 글자를 읽는 데 쓴 시간
서버 전체    이미지 열기 + 축소 + OCR
왕복 전체    폰에서 잰 시간
```

**왕복에서 서버 시간을 빼면 네트워크와 업로드에 쓴 시간입니다.**
사진 화질을 `quality: 0.7`에서 `1.0`으로 올려보면 이 값이 어떻게 변하는지 보세요.
업로드 용량도 같이 찍힙니다.

그리고 서버는 긴 변을 1600px로 줄여서 OCR에 넣습니다.
`MAX_SIDE`를 바꿔가며 **정확도와 속도를 맞바꾸는 지점**을 찾아보는 것도 좋은 실습입니다.

```bash
set MAX_SIDE=800
```
