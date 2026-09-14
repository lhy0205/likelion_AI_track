# 폰에서 찍은 사진을 받아 OCR해서 돌려주는 서버.
#
#   pip install -r requirements.txt
#   python main.py
#
# 띄우면 폰에서 접속할 주소가 찍힌다. 폰과 이 컴퓨터가 같은 와이파이에 있어야 한다.

import io
import os
import socket
import time

import uvicorn
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, ImageOps

from engines import get_engine

PORT = int(os.environ.get("PORT", "8000"))
MAX_SIDE = int(os.environ.get("MAX_SIDE", "1600"))

app = FastAPI(title="OCR Camera Server")

# 데모라 전부 열어둔다. 실제 서비스면 출처를 좁혀야 한다.
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

STATS = {"requests": 0, "latencies": []}


def lan_ip():
    # 밖으로 나가는 소켓을 열어보고 어떤 주소를 쓰는지 확인한다. 실제로 보내지는 않는다.
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def shrink(img, max_side=MAX_SIDE):
    # 폰 사진은 4000px가 넘는다. 그대로 넣으면 몇 초씩 걸리는데 OCR에는 1600이면 충분하다.
    if max(img.width, img.height) <= max_side:
        return img, 1.0
    k = max_side / max(img.width, img.height)
    return img.resize((int(img.width * k), int(img.height * k)), Image.LANCZOS), k


@app.on_event("startup")
def warmup():
    # 미리 만들어 두지 않으면 첫 요청이 수십 초 걸려서 데모가 망가진다.
    get_engine()
    ip = lan_ip()
    print()
    print("=" * 58)
    print("  폰에서 접속할 주소")
    print()
    print(f"      http://{ip}:{PORT}")
    print()
    print("  같은 와이파이에 있어야 하고, 방화벽이 포트를 막으면 안 된다.")
    print("=" * 58)
    print()


@app.get("/health")
def health():
    return {"ok": True, "engine": get_engine().name, "max_side": MAX_SIDE}


@app.get("/stats")
def stats():
    lat = STATS["latencies"]
    if not lat:
        return {"requests": 0}
    ordered = sorted(lat)
    return {
        "requests": STATS["requests"],
        "avg_ms": round(sum(lat) / len(lat), 1),
        "p50_ms": round(ordered[len(ordered) // 2], 1),
        "max_ms": round(max(lat), 1),
    }


@app.post("/ocr")
async def ocr(file: UploadFile = File(...)):
    started = time.perf_counter()

    raw = await file.read()
    img = Image.open(io.BytesIO(raw)).convert("RGB")

    # 폰 사진은 회전 정보가 EXIF에 들어 있다. 안 돌리면 글자가 누운 채로 들어간다.
    img = ImageOps.exif_transpose(img)
    original = f"{img.width}x{img.height}"

    img, scale = shrink(img)

    t = time.perf_counter()
    items = get_engine().read(img)
    ocr_ms = (time.perf_counter() - t) * 1000

    total_ms = (time.perf_counter() - started) * 1000
    STATS["requests"] += 1
    STATS["latencies"].append(total_ms)

    confs = [it["conf"] for it in items]
    return {
        "text": " ".join(it["text"] for it in items),
        "items": items,
        "count": len(items),
        "avg_conf": round(sum(confs) / len(confs), 3) if confs else 0.0,
        "min_conf": round(min(confs), 3) if confs else 0.0,
        "original_size": original,
        "processed_size": f"{img.width}x{img.height}",
        "scale": round(scale, 3),
        "ocr_ms": round(ocr_ms, 1),
        "total_ms": round(total_ms, 1),
        "engine": get_engine().name,
        "bytes": len(raw),
    }


if __name__ == "__main__":
    # 0.0.0.0으로 열어야 폰에서 붙는다. 127.0.0.1은 이 컴퓨터에서만 보인다.
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
