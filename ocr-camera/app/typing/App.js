// 따라 치는 용. 앱 최소 버전.
// 완성본은 ../App.js. 다 치고 나서 비교해 볼 것.
//
// SERVER는 서버가 띄울 때 알려준 주소로 바꾼다. 여기 틀리면 아무것도 안 된다.

import { CameraView, useCameraPermissions } from 'expo-camera';
import { useRef, useState } from 'react';
import { Button, Image, ScrollView, Text, View } from 'react-native';

const SERVER = 'http://192.168.0.10:8000';

export default function App() {
  const [permission, requestPermission] = useCameraPermissions();
  const [photo, setPhoto] = useState(null);
  const [result, setResult] = useState(null);
  const [log, setLog] = useState('');
  const cam = useRef(null);

  if (!permission?.granted) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', padding: 24 }}>
        <Text style={{ marginBottom: 12 }}>카메라 권한이 필요하다</Text>
        <Button title="권한 허용" onPress={requestPermission} />
      </View>
    );
  }

  async function shoot() {
    const shot = await cam.current.takePictureAsync({ quality: 0.7 });
    setPhoto(shot);
    setResult(null);
    setLog('보내는 중');

    const started = Date.now();
    const form = new FormData();

    // RN에서는 파일을 이 모양의 객체로 넣는다. 문자열이 아니다.
    form.append('file', { uri: shot.uri, name: 'photo.jpg', type: 'image/jpeg' });

    try {
      // headers에 Content-Type을 직접 쓰면 boundary가 빠져서 서버가 파일을 못 읽는다.
      const res = await fetch(SERVER + '/ocr', { method: 'POST', body: form });
      const data = await res.json();
      setResult(data);
      setLog(`OCR ${data.ocr_ms}ms · 왕복 ${Date.now() - started}ms`);
    } catch (e) {
      setLog('실패: ' + e.message + '  (주소, 와이파이, 방화벽 순으로 확인)');
    }
  }

  if (!photo) {
    return (
      <View style={{ flex: 1 }}>
        <CameraView ref={cam} style={{ flex: 1 }} facing="back" />
        <Button title="찍기" onPress={shoot} />
      </View>
    );
  }

  return (
    <ScrollView contentContainerStyle={{ padding: 16, paddingTop: 60 }}>
      <Image source={{ uri: photo.uri }} style={{ height: 200 }} resizeMode="contain" />
      <Text style={{ marginTop: 12, color: '#666' }}>{log}</Text>
      <Text style={{ fontSize: 20, marginVertical: 12 }}>{result?.text}</Text>

      {result?.items.map((it, i) => (
        <Text key={i} style={{ color: it.conf < 0.5 ? 'red' : '#333' }}>
          {it.conf.toFixed(2)}  {it.text}
        </Text>
      ))}

      <View style={{ marginTop: 20 }}>
        <Button title="다시 찍기" onPress={() => setPhoto(null)} />
      </View>
    </ScrollView>
  );
}
