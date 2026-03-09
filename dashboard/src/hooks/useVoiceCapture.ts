import { useCallback, useRef } from "react";
import { useGameStore } from "../store/gameStore";

export function useVoiceCapture(
  sendBinary: (data: ArrayBuffer) => void,
) {
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const contextRef = useRef<AudioContext | null>(null);
  const { setRecording } = useGameStore();

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });

      const audioContext = new AudioContext({ sampleRate: 16000 });
      const source = audioContext.createMediaStreamSource(stream);

      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      processor.onaudioprocess = (e) => {
        const inputData = e.inputBuffer.getChannelData(0);
        const pcm = new Int16Array(inputData.length);
        for (let i = 0; i < inputData.length; i++) {
          const sample = Math.max(-1, Math.min(1, inputData[i]!));
          pcm[i] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
        }
        const buffer = new ArrayBuffer(1 + pcm.byteLength);
        const view = new Uint8Array(buffer);
        view[0] = 0x01;
        view.set(new Uint8Array(pcm.buffer), 1);
        sendBinary(buffer);
      };

      source.connect(processor);
      processor.connect(audioContext.destination);

      mediaStreamRef.current = stream;
      processorRef.current = processor;
      contextRef.current = audioContext;
      setRecording(true);
    } catch (err) {
      console.error("Failed to start recording:", err);
    }
  }, [sendBinary, setRecording]);

  const stopRecording = useCallback(() => {
    processorRef.current?.disconnect();
    contextRef.current?.close();
    mediaStreamRef.current?.getTracks().forEach((t) => t.stop());
    processorRef.current = null;
    contextRef.current = null;
    mediaStreamRef.current = null;
    setRecording(false);
  }, [setRecording]);

  return { startRecording, stopRecording };
}
