import { useRef, useState } from "react";
import { Camera, UploadCloud, ChevronRight, X } from "lucide-react";

export type EvidencePhoto = {
  id: string;
  name: string;
  url: string;
};

export function Step4AddEvidence({
  comments,
  onCommentsChange,
  photos,
  onAddPhotos,
  onRemovePhoto,
  onNext,
  onBack,
}: {
  comments: string;
  onCommentsChange: (value: string) => void;
  photos: EvidencePhoto[];
  onAddPhotos: (files: FileList) => void;
  onRemovePhoto: (id: string) => void;
  onNext: () => void;
  onBack: () => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  const openPicker = () => inputRef.current?.click();

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-8 max-w-5xl mx-auto">
      <div className="flex items-center gap-2 text-blue-700 font-semibold">
        <Camera className="h-5 w-5" />
        Upload Evidence (Optional)
      </div>
      <p className="text-sm text-gray-500 mt-1 mb-5">
        Add photos of the damage to help with your claim.
      </p>

      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        multiple
        className="hidden"
        onChange={(e) => {
          if (e.target.files && e.target.files.length > 0) {
            onAddPhotos(e.target.files);
          }
          e.target.value = "";
        }}
      />

      <div
        role="button"
        tabIndex={0}
        onClick={openPicker}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            openPicker();
          }
        }}
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragging(false);
          if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            onAddPhotos(e.dataTransfer.files);
          }
        }}
        className={`rounded-xl border-2 border-dashed px-6 py-12 flex flex-col items-center justify-center text-center transition-colors cursor-pointer outline-none focus-visible:border-blue-400 focus-visible:bg-blue-50/30 ${
          isDragging
            ? "border-blue-400 bg-blue-50/50"
            : "border-gray-200 hover:border-blue-400 hover:bg-blue-50/30"
        }`}
      >
        <UploadCloud className="h-10 w-10 text-gray-300 mb-3" />
        <div className="font-semibold text-gray-700">Drag photos here</div>
        <div className="text-sm text-gray-400 mt-1">or click to browse</div>
      </div>

      {photos.length > 0 && (
        <div className="mt-4">
          <div className="text-sm font-semibold text-gray-600 mb-2">
            {photos.length} photo{photos.length > 1 ? "s" : ""} attached
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
            {photos.map((photo) => (
              <div
                key={photo.id}
                className="group relative rounded-xl overflow-hidden border border-gray-200 bg-gray-50"
              >
                <img
                  src={photo.url}
                  alt={photo.name}
                  className="h-28 w-full object-cover"
                />
                <button
                  type="button"
                  aria-label={`Remove ${photo.name}`}
                  onClick={() => onRemovePhoto(photo.id)}
                  className="absolute top-1.5 right-1.5 h-7 w-7 rounded-full bg-black/60 text-white flex items-center justify-center hover:bg-black/80 transition-colors"
                >
                  <X className="h-4 w-4" />
                </button>
                <div className="px-2 py-1.5 text-[11px] text-gray-500 truncate">
                  {photo.name}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <textarea
        className="w-full h-24 mt-4 p-4 rounded-xl border border-gray-200 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 outline-none resize-none transition-all"
        placeholder="Add any comments about the photos (optional)..."
        value={comments}
        onChange={(e) => onCommentsChange(e.target.value)}
      ></textarea>

      <div className="flex items-center gap-3 mt-6">
        <button
          type="button"
          onClick={onBack}
          className="rounded-xl border border-gray-200 px-6 py-3 font-semibold text-gray-600 hover:bg-gray-50 transition-colors"
        >
          Back
        </button>
        <button
          type="button"
          onClick={onNext}
          className="flex-1 rounded-xl bg-blue-600 text-white font-bold py-3 shadow-md hover:bg-blue-700 transition-colors flex items-center justify-center gap-2"
        >
          Generate FNOL Report
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
