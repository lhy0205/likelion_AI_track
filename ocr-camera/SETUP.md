# 따라 하기 — 카메라 OCR

각자 자기 노트북에서 서버를 띄우고, 자기 폰으로 찍어봅니다.
순서대로 하면 됩니다. 막히면 맨 아래 표를 보세요.

준비물: 노트북, 실물 폰(시뮬레이터는 카메라가 없습니다), 같은 와이파이.

---

## 1. 서버 띄우기

```bash
cd ocr-camera/server
pip install -r requirements.txt
python main.py
```

처음 실행하면 OCR 모델을 자동으로 받습니다. 수십 MB라 1~2분 걸립니다.

다 뜨면 이렇게 나옵니다. **여기 나온 주소를 적어두세요.**

```
[engine] rapidocr-korean-fast 준비 완료

==========================================================
  폰에서 접속할 주소

      http://192.168.0.10:8000

==========================================================
```

### 서버만 먼저 확인

앱을 붙이기 전에 서버가 되는지부터 봅니다. 나중에 안 될 때 원인을 가르기 쉬워집니다.

```bash
curl http://localhost:8000/health
```

```json
{"ok": true, "engine": "rapidocr-korean-fast", "max_side": 1600}
```

---

## 2. 방화벽 열기

이걸 안 하면 폰에서 접속이 안 됩니다. **노트북에서 한 번만** 하면 됩니다.

### 윈도우

PowerShell을 **관리자 권한으로** 열고:

```powershell
New-NetFirewallRule -DisplayName "OCR demo" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow -Profile Any
```

세션 끝나고 되돌릴 때:

```powershell
Remove-NetFirewallRule -DisplayName "OCR demo"
```

### 맥

기본적으로 방화벽이 꺼져 있어서 그냥 됩니다.
켜져 있다면 서버를 처음 띄울 때 "python이 들어오는 연결을 수락하도록 하시겠습니까?" 창이 뜹니다. **허용**을 누르세요.

---

## 3. 내 노트북 주소 확인

서버가 띄울 때 알려주지만, 직접 확인하는 방법입니다.

### 윈도우

```powershell
(Find-NetRoute -RemoteIPAddress 8.8.8.8)[0].IPAddress
```

`ipconfig`를 쓰면 블루투스나 가상 어댑터 주소까지 다 나와서 뭘 골라야 할지 헷갈립니다.
위 명령은 **실제로 인터넷에 나갈 때 쓰는 주소** 하나만 알려줍니다.

### 맥

```bash
ipconfig getifaddr en0        # 와이파이
```

`169.254`로 시작하는 주소가 나오면 와이파이에 제대로 연결이 안 된 겁니다. 폰에서 못 붙습니다.

### 폰으로 확인

폰 브라우저에서 열어봅니다.

```
http://내주소:8000/health
```

`{"ok": true, ...}` 가 보이면 통과입니다. **여기까지 되면 나머지는 쉽습니다.**

---

## 4. 앱 만들기

```bash
npx create-expo-app app --template blank
cd app
npx expo install expo-camera expo-file-system
```

`npm install`이 3~5분 걸립니다.

만들어진 `App.js`를 이 저장소의 `app/App.js` 내용으로 덮어씁니다.
그리고 **맨 위 한 줄만** 자기 주소로 바꿉니다.

```js
const SERVER = 'http://192.168.0.10:8000';
```

```bash
npx expo start
```

폰에 Expo Go를 깔고 QR을 찍습니다.

---

## 5. 찍어보기

글자가 화면을 꽉 채우게 찍습니다. 결과와 함께 측정값이 같이 나옵니다.

```
OCR         842 ms      서버가 글자를 읽는 데 쓴 시간
서버 전체    889 ms      이미지 열기 + 축소 + OCR
왕복        1320 ms     폰에서 잰 시간
```

왕복에서 서버 시간을 빼면 **네트워크와 업로드에 쓴 시간**입니다.

### 바꿔보기

서버를 끄고 환경변수를 준 뒤 다시 띄웁니다. **앱은 건드리지 않습니다.**

윈도우

```powershell
$env:OCR_QUALITY="accurate"; python main.py
$env:MAX_SIDE="800"; python main.py
```

맥

```bash
OCR_QUALITY=accurate python main.py
MAX_SIDE=800 python main.py
```

| 바꿀 것 | 무엇이 달라지나 |
|---|---|
| `OCR_QUALITY=accurate` | 정확해지지만 이미지당 9초로 느려짐 |
| `MAX_SIDE=800` | 빨라지지만 작은 글씨를 놓침 |
| `OCR_LANG=en` | 영어 전용. 한글은 못 읽음 |
| `App.js`의 `quality: 1.0` | 업로드 용량이 커짐. 왕복 시간을 보세요 |

---

## 안 될 때

| 증상 | 볼 것 |
|---|---|
| 폰 브라우저에서 `/health`가 안 열림 | 방화벽, 그다음 와이파이가 같은지 |
| 앱에서 Network request failed | `SERVER` 주소 오타 |
| **서버 화면에 아무것도 안 찍힘** | 요청이 도달을 못 한 것. 앱이 아니라 네트워크 문제 |
| 주소가 `169.254`로 시작 | 와이파이 연결이 안 된 상태 |
| 첫 요청만 수십 초 | 모델을 그때 받는 중. 한 번 받으면 빨라짐 |
| 글자를 아예 못 읽음 | 더 가까이, 글자가 화면을 채우게 |

**서버 띄운 터미널을 보이게 두고 하세요.** 요청이 찍히는지 아닌지가 문제를 반으로 가릅니다.

---

## 참고

- 서버는 인증이 없습니다. 같은 와이파이에 있는 사람은 누구나 접근할 수 있으니 세션 끝나면 방화벽을 되돌리세요.
- 영수증이나 신분증을 찍으면 개인정보가 서버 로그에 남습니다.
- 폰은 와이파이로 붙습니다. 노트북이 랜선이면 **같은 공유기**에 물려 있어야 합니다.
