import { useState } from "react";
import { Mic } from "lucide-react";

const VOICE_ENDPOINT = "http://localhost:7701/chat_voice";

export function Step1Describe({
  description,
  onDescriptionChange,
  onNext,
}: {
  description: string;
  onDescriptionChange: (value: string) => void;
  onNext: () => void;
}) {
  const [listening, setListening] = useState(false);

  const handleMicClick = async () => {
    setListening(true);
    try {
      await fetch(VOICE_ENDPOINT, { method: "POST" });
    } catch {
      // Local voice service may be unavailable or blocked by CORS;
      // keep the UI functional regardless.
    } finally {
      setListening(false);
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
          className="flex flex-col items-center group"
        >
          <div
            className={`h-24 w-24 rounded-full bg-gradient-to-br from-indigo-900 to-blue-600 flex items-center justify-center shadow-lg shadow-blue-500/30 group-hover:scale-105 transition-transform ${
              listening ? "scale-105 ring-4 ring-blue-300/60 animate-pulse" : ""
            }`}
          >
            <Mic className="h-10 w-10 text-white" />
          </div>
          <span className="mt-4 text-sm font-medium text-gray-600 group-hover:text-blue-600 transition-colors">
            {listening ? "Listening..." : "Tap to start speaking"}
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

      <button
        type="button"
        onClick={onNext}
        className="w-full mt-6 py-4 rounded-xl bg-gradient-to-r from-violet-600 to-blue-600 text-white font-bold text-lg shadow-md hover:shadow-lg transition-all hover:opacity-95"
      >
        Analyze with AI
      </button>
    </div>
  );
}
