# OCR 엔진 교체 지점.
# main.py는 어떤 엔진을 쓰는지 모른다. read()가 같은 모양을 돌려주기만 하면 된다.
#   [{"text": ..., "conf": ..., "box": [[x, y], ...]}]

import os

_engine = None


class RapidEngine:
    # PP-OCR 계열 ONNX 모델. torch를 안 쓴다.
    # 모델은 처음 쓸 때 자동으로 받아서 캐시에 둔다.
    #
    # OCR_LANG    korean(기본) / ch / en / japan ...
    # OCR_QUALITY fast(기본) / accurate
    #
    # fast와 accurate는 글자를 '찾는' 모델만 다르다. 읽는 모델은 같다.
    # 실측(샘플 5장 평균): fast CER 0.32 / 1.4초,  accurate CER 0.08 / 9초

    name = "rapidocr"

    def __init__(self):
        from rapidocr import EngineType, LangDet, LangRec, ModelType, OCRVersion, RapidOCR

        lang = os.environ.get("OCR_LANG", "korean").strip().lower()
        quality = os.environ.get("OCR_QUALITY", "fast").strip().lower()
        det_type = ModelType.SERVER if quality == "accurate" else ModelType.MOBILE

        try:
            lang_rec = LangRec(lang)
        except ValueError:
            raise SystemExit(
                f"모르는 언어: {lang}\n"
                f"가능: {', '.join(e.value for e in LangRec)}"
            )

        # 검출은 v4 중국어 모델을 쓴다. 글자 위치를 찾는 일이라 언어와 상관없고,
        # v5/v6 검출 모델은 우리 쪽 이미지에서 오히려 점수가 나빴다.
        self.engine = RapidOCR(params={
            "Det.engine_type": EngineType.ONNXRUNTIME,
            "Det.ocr_version": OCRVersion.PPOCRV4,
            "Det.lang_type": LangDet.CH,
            "Det.model_type": det_type,
            "Rec.engine_type": EngineType.ONNXRUNTIME,
            "Rec.ocr_version": OCRVersion.PPOCRV4,
            "Rec.lang_type": lang_rec,
            "Rec.model_type": ModelType.MOBILE,
        })
        self.name = f"rapidocr-{lang}-{quality}"

    def read(self, img):
        import numpy as np

        res = self.engine(np.array(img))
        if not res or not res.txts:
            return []

        boxes = res.boxes if res.boxes is not None else [None] * len(res.txts)
        scores = res.scores if res.scores is not None else [0.0] * len(res.txts)
        out = []
        for box, text, score in zip(boxes, res.txts, scores):
            out.append({
                "text": text,
                "conf": float(score),
                "box": [[float(x), float(y)] for x, y in box] if box is not None else [],
            })
        return out


class EasyEngine:
    # torch 기반. 한글 인식이 좋지만 설치 환경을 탄다.
    # 윈도우에서 Smart App Control이 켜져 있으면 torch DLL이 막혀서 import부터 실패한다.

    name = "easyocr"

    def __init__(self):
        import easyocr

        langs = [s.strip() for s in os.environ.get("OCR_LANG", "ko,en").split(",")]
        self.engine = easyocr.Reader(langs, gpu=False, verbose=False)

    def read(self, img):
        import numpy as np

        out = []
        for box, text, conf in self.engine.readtext(np.array(img)):
            out.append({
                "text": text,
                "conf": float(conf),
                "box": [[float(x), float(y)] for x, y in box],
            })
        return out


class ClovaEngine:
    # 네이버 CLOVA OCR. 한글 정확도는 이쪽이 제일 낫다.
    # CLOVA_URL, CLOVA_SECRET 두 개가 필요하다.
    # 이미지가 외부로 나가니 영수증이나 신분증을 쓸 거면 감안할 것.

    name = "clova"

    def __init__(self):
        self.url = os.environ["CLOVA_URL"]
        self.secret = os.environ["CLOVA_SECRET"]

    def read(self, img):
        import base64
        import io
        import json
        import time
        import urllib.request

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)

        payload = {
            "version": "V2",
            "requestId": str(time.time()),
            "timestamp": int(time.time() * 1000),
            "images": [{
                "format": "jpg",
                "name": "camera",
                "data": base64.b64encode(buf.getvalue()).decode(),
            }],
        }
        req = urllib.request.Request(
            self.url,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", "X-OCR-SECRET": self.secret},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())

        out = []
        for field in data.get("images", [{}])[0].get("fields", []):
            verts = field.get("boundingPoly", {}).get("vertices", [])
            out.append({
                "text": field.get("inferText", ""),
                "conf": float(field.get("inferConfidence", 0.0)),
                "box": [[v.get("x", 0.0), v.get("y", 0.0)] for v in verts],
            })
        return out


ENGINES = {"rapidocr": RapidEngine, "easyocr": EasyEngine, "clova": ClovaEngine}


def get_engine():
    # 한 번 만들어 두고 재사용한다. 요청마다 새로 만들면 몇 초씩 날아간다.
    global _engine
    if _engine is None:
        name = os.environ.get("OCR_ENGINE", "rapidocr").strip().lower()
        if name not in ENGINES:
            raise SystemExit(f"모르는 엔진: {name} (가능: {', '.join(ENGINES)})")
        print(f"[engine] {name} 준비 중")
        _engine = ENGINES[name]()
        print(f"[engine] {_engine.name} 준비 완료")
    return _engine
