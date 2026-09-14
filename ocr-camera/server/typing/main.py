# 따라 치는 용. 서버 최소 버전.
#
#   pip install fastapi "uvicorn[standard]" python-multipart pillow rapidocr onnxruntime
#   python main.py
#
# 완성본은 ../main.py 와 ../engines.py. 다 치고 나서 비교해 볼 것.

import io
import socket
import time

import numpy as np
import uvicorn
from fastapi import FastAPI, File, UploadFile
from PIL import Image, ImageOps
from rapidocr import LangRec, ModelType, OCRVersion, RapidOCR

MAX_SIDE = 1600          # 폰 사진은 4000px가 넘는다. 그대로 넣으면 느리다.

app = FastAPI()

# 기본값은 중국어다. 한국어 인식 모델을 따로 지정해야 한다.
engine = RapidOCR(params={
    "Rec.lang_type": LangRec.KOREAN,
    "Rec.ocr_version": OCRVersion.PPOCRV4,
    "Rec.model_type": ModelType.MOBILE,
})


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/ocr")
async def ocr(file: UploadFile = File(...)):
    raw = await file.read()
    img = Image.open(io.BytesIO(raw))

    # 폰으로 세로로 찍으면 회전 정보가 EXIF에만 들어간다. 이걸 안 풀면 글자가 누워서 들어간다.
    img = ImageOps.exif_transpose(img).convert("RGB")
    before = img.size

    if max(img.size) > MAX_SIDE:
        r = MAX_SIDE / max(img.size)
        img = img.resize((int(img.width * r), int(img.height * r)))

    t = time.perf_counter()
    res = engine(np.array(img))
    ms = round((time.perf_counter() - t) * 1000, 1)

    items = []
    if res and res.txts:
        items = [{"text": t_, "conf": round(float(c), 3)}
                 for t_, c in zip(res.txts, res.scores)]

    print(f"{file.filename}  {before} -> {img.size}  {len(raw)//1024}KB  "
          f"{ms}ms  덩어리 {len(items)}")

    return {
        "text": " ".join(i["text"] for i in items),
        "items": items,
        "count": len(items),
        "ocr_ms": ms,
    }


if __name__ == "__main__":
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()

    print(f"\n  폰에서 접속할 주소:  http://{ip}:8000\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
