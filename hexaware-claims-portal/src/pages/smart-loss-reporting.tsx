import { useState } from "react";
import { CheckCircle2 } from "lucide-react";
import { GradientBanner } from "@/components/ui/GradientBanner";
import { StepTracker } from "@/components/fnol/StepTracker";
import { Step1Describe } from "@/components/fnol/Step1Describe";
import { Step2VerifyPolicy } from "@/components/fnol/Step2VerifyPolicy";
import { Step3AnswerQuestions } from "@/components/fnol/Step3AnswerQuestions";
import { Step4AddEvidence } from "@/components/fnol/Step4AddEvidence";
import { Step5ReviewForm } from "@/components/fnol/Step5ReviewForm";
import { Step6ConfirmSubmit } from "@/components/fnol/Step6ConfirmSubmit";
import { aiFields } from "@/lib/fnol-data";
import type { EvidencePhoto } from "@/components/fnol/Step4AddEvidence";

export default function SmartLossReporting() {
  const [currentStep, setCurrentStep] = useState(1);
  const [submitted, setSubmitted] = useState(false);

  const [description, setDescription] = useState("");
  const [questionIndex, setQuestionIndex] = useState(0);
  const [comments, setComments] = useState("");
  const [photos, setPhotos] = useState<EvidencePhoto[]>([]);
  const [confirmed, setConfirmed] = useState<boolean[]>(() =>
    aiFields.map(() => false)
  );

  const next = () => setCurrentStep((s) => Math.min(6, s + 1));
  const back = () => setCurrentStep((s) => Math.max(1, s - 1));

  const addPhotos = (files: FileList) => {
    const incoming = Array.from(files)
      .filter((file) => file.type.startsWith("image/"))
      .map((file) => ({
        id: `${file.name}-${file.size}-${file.lastModified}-${Math.random()
          .toString(36)
          .slice(2, 8)}`,
        name: file.name,
        url: URL.createObjectURL(file),
      }));
    if (incoming.length > 0) {
      setPhotos((prev) => [...prev, ...incoming]);
    }
  };

  const removePhoto = (id: string) => {
    setPhotos((prev) => {
      const target = prev.find((photo) => photo.id === id);
      if (target) {
        URL.revokeObjectURL(target.url);
      }
      return prev.filter((photo) => photo.id !== id);
    });
  };

  const reset = () => {
    setSubmitted(false);
    setCurrentStep(1);
    setDescription("");
    setQuestionIndex(0);
    setComments("");
    photos.forEach((photo) => URL.revokeObjectURL(photo.url));
    setPhotos([]);
    setConfirmed(aiFields.map(() => false));
  };

  if (submitted) {
    return (
      <div className="animate-in fade-in duration-500">
        <GradientBanner
          title="Intelligent FNOL"
          subtitle="AI-powered First Notice of Loss with clear data attribution"
        />
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-12 max-w-3xl mx-auto text-center">
          <div className="h-16 w-16 rounded-full bg-emerald-50 flex items-center justify-center mx-auto mb-5">
            <CheckCircle2 className="h-9 w-9 text-emerald-500" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900">
            FNOL Submitted Successfully
          </h2>
          <p className="text-gray-500 mt-2">
            Your claim has been created and routed for review. You can track its
            progress in My Claims.
          </p>
          <div className="mt-5 inline-flex items-center gap-2 rounded-lg bg-gray-50 border border-gray-200 px-4 py-2 text-sm font-semibold text-gray-700">
            Claim Reference: FNOL-2026-483729
          </div>
          <div className="mt-8">
            <button
              type="button"
              onClick={reset}
              className="rounded-xl bg-gradient-to-r from-violet-600 to-blue-600 text-white font-bold px-6 py-3 shadow-md hover:shadow-lg transition-all"
            >
              Start a New Report
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="animate-in fade-in duration-500">
      <GradientBanner
        title="Intelligent FNOL"
        subtitle="AI-powered First Notice of Loss with clear data attribution"
      />

      <StepTracker currentStep={currentStep} />

      {currentStep === 1 && (
        <Step1Describe
          description={description}
          onDescriptionChange={setDescription}
          onNext={next}
        />
      )}
      {currentStep === 2 && <Step2VerifyPolicy onNext={next} />}
      {currentStep === 3 && (
        <Step3AnswerQuestions
          index={questionIndex}
          onIndexChange={setQuestionIndex}
          onNext={next}
        />
      )}
      {currentStep === 4 && (
        <Step4AddEvidence
          comments={comments}
          onCommentsChange={setComments}
          photos={photos}
          onAddPhotos={addPhotos}
          onRemovePhoto={removePhoto}
          onNext={next}
          onBack={back}
        />
      )}
      {currentStep === 5 && (
        <Step5ReviewForm
          comments={comments}
          photos={photos}
          onNext={next}
          onBack={back}
        />
      )}
      {currentStep === 6 && (
        <Step6ConfirmSubmit
          confirmed={confirmed}
          onConfirmedChange={setConfirmed}
          onSubmit={() => setSubmitted(true)}
          onBack={back}
        />
      )}
    </div>
  );
}
