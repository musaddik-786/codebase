import { useCallback, useRef, useState } from "react";

import { FNOL_AGENT_URL } from "@/config/agents";
const TRANSCRIBE_ENDPOINT = `${FNOL_AGENT_URL}/transcribe`;

export function useVoiceInput(onResult: (text: string) => void) {
  const [listening, setListening] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const send = useCallback(
    async (audio: Blob) => {
      setTranscribing(true);
      try {
        const formData = new FormData();
        formData.append("file", audio, "recording.webm");
        const res = await fetch(TRANSCRIBE_ENDPOINT, {
          method: "POST",
          body: formData,
        });
        if (!res.ok) throw new Error(`Transcription failed: ${res.status}`);
        const data = await res.json();
        const text = data.text ?? data.transcript ?? data.transcription ?? "";
        if (text) onResult(text);
      } catch (err) {
        console.error("Transcription error:", err);
      } finally {
        setTranscribing(false);
      }
    },
    [onResult]
  );

  const start = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        void send(new Blob(chunksRef.current, { type: "audio/webm" }));
      };
      recorderRef.current = recorder;
      recorder.start();
      setListening(true);
    } catch (err) {
      console.error("Microphone access error:", err);
      setListening(false);
    }
  }, [send]);

  const stop = useCallback(() => {
    recorderRef.current?.stop();
    recorderRef.current = null;
    setListening(false);
  }, []);

  const toggle = useCallback(() => {
    if (transcribing) return;
    if (listening) stop();
    else void start();
  }, [transcribing, listening, stop, start]);

  return { listening, transcribing, toggle };
}
