import { useRef, useState } from "react";
import { Mic } from "lucide-react";

import { FNOL_AGENT_URL } from "@/config/agents";
const TRANSCRIBE_ENDPOINT = `${FNOL_AGENT_URL}/transcribe`;

export function Step1Describe({
  description,
  policyNumber,
  onDescriptionChange,
  estimatedCost,
  onEstimatedCostChange,
  onNext,
  policyVerified = false,
}: {
  description: string;
  policyNumber: string;
  onDescriptionChange: (value: string) => void;
  estimatedCost: string;
  onEstimatedCostChange: (value: string) => void;
  onNext: () => void;
  policyVerified?: boolean;
}) {
  const [listening, setListening] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  const fetchStoredTranscription = async (): Promise<string> => {
    const policy = policyNumber.trim();
    if (!policy) return "";
    try {
      const res = await fetch(
        `/api/voice-extraction?policyNumber=${encodeURIComponent(
          policy
        )}&inputType=voice_transcript`
      );
      if (!res.ok) return "";
      const data = await res.json();
      return typeof data?.text === "string" ? data.text : "";
    } catch (err) {
      console.error("Voice extraction fetch error:", err);
      return "";
    }
  };

  const sendForTranscription = async (audio: Blob) => {
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
      const transcribed =
        data.text ?? data.transcript ?? data.transcription ?? "";
      // Prefer the persisted transcription from fnol_voice_text_extraction so
      // the description box mirrors exactly what was stored.
      const stored = await fetchStoredTranscription();
      const text = stored || transcribed;
      if (text) {
        // Each new transcription replaces the description instead of appending to it.
        onDescriptionChange(text);
      }
    } catch (err) {
      console.error("Transcription error:", err);
    } finally {
      setTranscribing(false);
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      chunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        void sendForTranscription(blob);
      };
      mediaRecorderRef.current = recorder;
      recorder.start();
      setListening(true);
    } catch (err) {
      console.error("Microphone access error:", err);
      setListening(false);
    }
  };

  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
    mediaRecorderRef.current = null;
    setListening(false);
  };

  const handleMicClick = () => {
    if (!policyVerified || transcribing) return;
    if (listening) {
      stopRecording();
    } else {
      void startRecording();
    }
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-8 max-w-5xl mx-auto">
      <div className="flex flex-col items-center text-center mb-8">
        <h2 className="text-xl font-bold text-gray-900">Tell Us What Happened</h2>
        <p className="text-gray-500 mt-2">
          Speak or type to describe the incident. Our AI will extract key information automatically.
        </p>
      </div>

      <div className="flex justify-center mb-8">
        <button
          type="button"
          onClick={handleMicClick}
          disabled={!policyVerified}
          aria-disabled={!policyVerified}
          className={`flex flex-col items-center group ${
            policyVerified ? "" : "cursor-not-allowed"
          }`}
        >
          <div
            className={`h-24 w-24 rounded-full flex items-center justify-center transition-transform ${
              policyVerified
                ? `bg-gradient-to-br from-indigo-900 to-blue-600 shadow-lg shadow-blue-500/30 group-hover:scale-105 ${
                    listening ? "scale-105 ring-4 ring-blue-300/60 animate-pulse" : ""
                  }`
                : "bg-gray-300 shadow-none"
            }`}
          >
            <Mic className="h-10 w-10 text-white" />
          </div>
          <span
            className={`mt-4 text-sm font-medium transition-colors ${
              policyVerified
                ? "text-gray-600 group-hover:text-blue-600"
                : "text-gray-400"
            }`}
          >
            {!policyVerified
              ? "Verify your policy to start speaking"
              : transcribing
              ? "Transcribing..."
              : listening
              ? "Listening... tap to stop"
              : "Tap to start speaking"}
          </span>
        </button>
      </div>

      <div className="flex items-center gap-4 my-8">
        <div className="flex-1 h-px bg-gray-200"></div>
        <span className="text-xs font-bold text-gray-400 uppercase tracking-wider">
          OR TYPE YOUR DESCRIPTION
        </span>
        <div className="flex-1 h-px bg-gray-200"></div>
      </div>

      <textarea
        className="w-full h-32 p-4 rounded-xl border border-gray-200 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 outline-none resize-none transition-all"
        placeholder="e.g. I was driving down Main St yesterday around 2pm when the car in front of me slammed on their brakes..."
        value={description}
        onChange={(e) => onDescriptionChange(e.target.value)}
      ></textarea>

      <div className="mt-4">
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Estimated Damage Amount{" "}
          <span className="font-normal text-gray-400">(optional)</span>
        </label>
        <div className="relative">
          <span className="absolute inset-y-0 left-0 flex items-center pl-4 text-gray-400 font-medium pointer-events-none">
            $
          </span>
          <input
            type="number"
            min="0"
            step="any"
            value={estimatedCost}
            onChange={(e) => onEstimatedCostChange(e.target.value)}
            placeholder="0.00"
            className="w-full pl-8 pr-4 py-3 rounded-xl border border-gray-200 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 outline-none transition-all"
          />
        </div>
        <p className="text-xs text-gray-400 mt-1">
          Your best estimate helps determine coverage eligibility. You can update this later.
        </p>
      </div>

      <button
        type="button"
        onClick={onNext}
        disabled={!policyVerified}
        aria-disabled={!policyVerified}
        className={`w-full mt-6 py-4 rounded-xl font-bold text-lg shadow-md transition-all ${
          policyVerified
            ? "bg-gradient-to-r from-violet-600 to-blue-600 text-white hover:shadow-lg hover:opacity-95"
            : "bg-gray-200 text-gray-400 cursor-not-allowed"
        }`}
      >
        Chat with AI
      </button>
      {!policyVerified && (
        <p className="mt-3 text-center text-xs text-gray-400">
          Verify your policy above to start speaking or chat with AI.
        </p>
      )}
    </div>
  );
}
