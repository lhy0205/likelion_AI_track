// 아래 SERVER 주소를 expo 서버가 알려준 주소로 바꿔야 한다.

import { CameraView, useCameraPermissions } from 'expo-camera';
import { useRef, useState } from 'react';
import {
  ActivityIndicator,
  Image,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';

const SERVER = 'http://192.168.0.10:8000';

export default function App() {
  const [permission, requestPermission] = useCameraPermissions();
  const [photo, setPhoto] = useState(null);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const cameraRef = useRef(null);

  if (!permission) {
    return (
      <View style={styles.center}>
        <ActivityIndicator />
      </View>
    );
  }

  if (!permission.granted) {
    return (
      <View style={styles.center}>
        <Text style={styles.title}>카메라 권한이 필요합니다</Text>
        <TouchableOpacity style={styles.button} onPress={requestPermission}>
          <Text style={styles.buttonText}>권한 허용</Text>
        </TouchableOpacity>
      </View>
    );
  }

  async function takePhoto() {
    if (!cameraRef.current || busy) return;
    setError(null);
    setResult(null);

    // quality를 1.0으로 올리면 업로드가 눈에 띄게 느려진다
    const shot = await cameraRef.current.takePictureAsync({ quality: 0.7 });
    setPhoto(shot);
    upload(shot);
  }

  async function upload(shot) {
    setBusy(true);
    const started = Date.now();

    try {
      const form = new FormData();

      // RN에서는 파일을 이 모양의 객체로 넣는다
      form.append('file', { uri: shot.uri, name: 'photo.jpg', type: 'image/jpeg' });

      // Content-Type을 직접 지정하면 boundary가 빠져서 서버가 파일을 못 읽는다
      const res = await fetch(`${SERVER}/ocr`, { method: 'POST', body: form });
      if (!res.ok) throw new Error(`서버 응답 ${res.status}`);

      const data = await res.json();
      data.round_trip_ms = Date.now() - started;
      setResult(data);
    } catch (e) {
      setError(
        `${e.message}\n\n` +
          `폰과 노트북이 같은 와이파이인지,\n` +
          `SERVER 주소가 맞는지 (${SERVER}),\n` +
          `방화벽이 포트를 막고 있지 않은지 확인하세요.`
      );
    } finally {
      setBusy(false);
    }
  }

  function reset() {
    setPhoto(null);
    setResult(null);
    setError(null);
  }

  if (!photo) {
    return (
      <View style={styles.container}>
        <CameraView ref={cameraRef} style={styles.camera} facing="back" />
        <View style={styles.bottomBar}>
          <Text style={styles.hint}>글자가 화면을 꽉 채우게 찍으세요</Text>
          <TouchableOpacity style={styles.shutter} onPress={takePhoto} />
        </View>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={{ paddingBottom: 40 }}>
      <Image source={{ uri: photo.uri }} style={styles.preview} />

      {busy && (
        <View style={styles.block}>
          <ActivityIndicator size="large" />
          <Text style={styles.hint}>읽는 중</Text>
        </View>
      )}

      {error && (
        <View style={styles.block}>
          <Text style={styles.errorTitle}>실패</Text>
          <Text style={styles.errorBody}>{error}</Text>
        </View>
      )}

      {result && (
        <View style={styles.block}>
          <Text style={styles.label}>읽은 글자</Text>
          <Text style={styles.text}>{result.text || '(못 읽었습니다)'}</Text>

          <Text style={styles.label}>덩어리 {result.count}개</Text>
          {result.items.map((it, i) => (
            <Text key={i} style={[styles.item, it.conf < 0.5 && styles.itemLow]}>
              {it.conf.toFixed(2)}  {it.text}
            </Text>
          ))}

          <Text style={styles.label}>측정값</Text>
          <Text style={styles.meta}>엔진        {result.engine}</Text>
          <Text style={styles.meta}>평균 신뢰도  {result.avg_conf}</Text>
          <Text style={styles.meta}>사진 크기    {result.original_size} → {result.processed_size}</Text>
          <Text style={styles.meta}>업로드      {(result.bytes / 1024).toFixed(0)} KB</Text>
          <Text style={styles.meta}>OCR         {result.ocr_ms} ms</Text>
          <Text style={styles.meta}>서버 전체    {result.total_ms} ms</Text>
          <Text style={styles.meta}>왕복        {result.round_trip_ms} ms</Text>
          <Text style={styles.note}>
            왕복에서 서버 시간을 빼면 네트워크와 업로드에 쓴 시간입니다.
          </Text>
        </View>
      )}

      <TouchableOpacity style={styles.button} onPress={reset}>
        <Text style={styles.buttonText}>다시 찍기</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#12151B' },
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#12151B',
    padding: 24,
  },
  camera: { flex: 1 },
  bottomBar: { padding: 24, alignItems: 'center', backgroundColor: '#12151B' },
  shutter: {
    width: 72,
    height: 72,
    borderRadius: 36,
    backgroundColor: '#fff',
    borderWidth: 4,
    borderColor: '#8B95A3',
  },
  preview: { width: '100%', height: 280, resizeMode: 'contain', backgroundColor: '#000' },
  block: { margin: 16, padding: 16, backgroundColor: '#1E232C', borderRadius: 12 },
  title: { color: '#fff', fontSize: 18, marginBottom: 16 },
  label: { color: '#8B95A3', fontSize: 12, marginTop: 14, marginBottom: 6, letterSpacing: 1 },
  text: { color: '#fff', fontSize: 20, lineHeight: 28 },
  item: { color: '#EAEEF3', fontSize: 14, fontFamily: 'monospace', marginTop: 3 },
  itemLow: { color: '#E5484D' },
  meta: { color: '#EAEEF3', fontSize: 13, fontFamily: 'monospace', marginTop: 2 },
  note: { color: '#68727F', fontSize: 12, marginTop: 10, lineHeight: 17 },
  hint: { color: '#8B95A3', fontSize: 13, marginBottom: 14 },
  errorTitle: { color: '#E5484D', fontSize: 16, fontWeight: 'bold', marginBottom: 8 },
  errorBody: { color: '#EAEEF3', fontSize: 13, lineHeight: 20 },
  button: {
    margin: 16,
    padding: 16,
    borderRadius: 10,
    backgroundColor: '#E5484D',
    alignItems: 'center',
  },
  buttonText: { color: '#fff', fontSize: 16, fontWeight: 'bold' },
});
