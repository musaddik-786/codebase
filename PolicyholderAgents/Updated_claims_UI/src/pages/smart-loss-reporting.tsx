import { useEffect, useRef, useState } from "react";
import { CheckCircle2 } from "lucide-react";

const MCP_BASE = import.meta.env.VITE_MCP_URL ?? "http://localhost:7720";
const FNOL_ORCHESTRATOR_URL = import.meta.env.VITE_FNOL_ORCHESTRATOR_URL ?? "http://localhost:7730";

// Maps UI field label → DB value column name for PATCH calls.
const FIELD_TO_COLUMN: Record<string, string> = {
  "Type of Loss":              "loss_type",
  "Cause of Loss":             "cause_of_loss",
  "Area Affected":             "area_affected",
  "Date of Loss":              "date_of_loss",
  "Time of Loss":              "time_of_loss",
  "Sudden vs Gradual":         "sudden_vs_gradual",
  "Occupancy at Time of Loss": "occupancy_at_loss",
  "Severity":                  "severity",
  "Emotional Context":         "emotional_context",
  "Urgency Indicator":         "urgency_indicator",
  "Estimated Damage Amount":   "estimated_cost",
};

// Maps UI field label → DB source column name (all 10 fields now have one).
const FIELD_TO_SOURCE_COLUMN: Record<string, string> = {
  "Type of Loss":              "loss_type_source",
  "Cause of Loss":             "cause_of_loss_source",
  "Area Affected":             "area_affected_source",
  "Date of Loss":              "date_of_loss_source",
  "Time of Loss":              "time_of_loss_source",
  "Sudden vs Gradual":         "sudden_vs_gradual_source",
  "Occupancy at Time of Loss": "occupancy_at_loss_source",
  "Severity":                  "severity_source",
  "Emotional Context":         "emotional_context_source",
  "Urgency Indicator":         "urgency_indicator_source",
};
import { GradientBanner } from "@/components/ui/GradientBanner";
import { StepTracker } from "@/components/fnol/StepTracker";
import { Stage1PolicyLookup } from "@/components/fnol/Stage1PolicyLookup";
import { Stage2AnswerQuestions } from "@/components/fnol/Stage2AnswerQuestions";
import { Stage3ReviewForm } from "@/components/fnol/Stage3ReviewForm";
import type {
  ChatMessage,
  EvidencePhoto,
  FnolField,
  PolicyField,
} from "@/lib/fnol-data";

export default function SmartLossReporting() {
  const [currentStep, setCurrentStep] = useState(1);
  const [submitted, setSubmitted] = useState(false);

  const [policyNumber, setPolicyNumber] = useState("");
  const [description, setDescription] = useState("");
  const [estimatedCost, setEstimatedCost] = useState("");
  const [comments, setComments] = useState("");
  const [photos, setPhotos] = useState<EvidencePhoto[]>([]);
  const [humanReview, setHumanReview] = useState<Record<string, string>>({});
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);

  const [lossFields, setLossFields] = useState<FnolField[]>([]);
  const [overallConfidence, setOverallConfidence] = useState<number | null>(null);
  const [fnolId, setFnolId] = useState<number | null>(null);
  const [fnolNumber, setFnolNumber] = useState<string | null>(null);
  const [submissionLoading, setSubmissionLoading] = useState(false);
  const [submissionError, setSubmissionError] = useState<string | null>(null);
  const [isSavingEdits, setIsSavingEdits] = useState(false);
  const [saveEditsError, setSaveEditsError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [uploadWarning, setUploadWarning] = useState<string | null>(null);

  const [sectionA, setSectionA] = useState<PolicyField[]>([]);

  useEffect(() => {
    // Only auto-fetch on Step 3 (review). Step 2 fields are populated
    // progressively via handleFnolRefresh after each agent turn — fetching
    // here on step-2 entry would show stale data from a previous session.
    if (currentStep !== 3) return;
    const trimmedPolicy = policyNumber.trim();
    if (trimmedPolicy === "") {
      setLossFields([]);
      setOverallConfidence(null);
      setSubmissionLoading(false);
      setSubmissionError("Enter a policy number to load extracted loss details.");
      return;
    }
    let cancelled = false;
    setSubmissionLoading(true);
    setSubmissionError(null);
    (async () => {
      try {
        const res = await fetch(
          `/api/fnol-submission?policyNumber=${encodeURIComponent(trimmedPolicy)}`
        );
        const data = await res.json().catch(() => null);
        if (!res.ok) {
          throw new Error(
            res.status === 404
              ? "No extracted loss details found yet."
              : (data && data.error) || "Could not load extracted loss details."
          );
        }
        if (!cancelled) {
          setLossFields(Array.isArray(data?.fields) ? data.fields : []);
          setOverallConfidence(
            typeof data?.overallConfidence === "number"
              ? data.overallConfidence
              : null
          );
          if (typeof data?.id === "number" && data.id > 0) setFnolId(data.id);
          setFnolNumber(
            typeof data?.fnolNumber === "string" && data.fnolNumber.trim()
              ? data.fnolNumber.trim()
              : null
          );
        }
      } catch (err) {
        if (!cancelled) {
          setLossFields([]);
          setOverallConfidence(null);
          setSubmissionError(
            err instanceof Error
              ? err.message
              : "Could not load extracted loss details."
          );
        }
      } finally {
        if (!cancelled) setSubmissionLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [currentStep, policyNumber]);

  useEffect(() => {
    if (currentStep !== 3) return;
    const trimmedPolicy = policyNumber.trim();
    if (trimmedPolicy === "") {
      setSectionA([]);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(
          `/api/policy-details?policyNumber=${encodeURIComponent(trimmedPolicy)}`
        );
        const data = await res.json().catch(() => null);
        if (!res.ok) {
          if (!cancelled) setSectionA([]);
          return;
        }
        if (!cancelled) {
          const rows: PolicyField[] = [
            { label: "Policy Number", value: data?.policyNumber ?? trimmedPolicy },
            { label: "Insured Name", value: data?.insuredName ?? null },
            { label: "Insured Address", value: data?.insuredAddress ?? null },
          ]
            .filter((row) => row.value != null && String(row.value).trim() !== "")
            .map((row) => ({ label: row.label, value: String(row.value) }));
          setSectionA(rows);
        }
      } catch {
        if (!cancelled) setSectionA([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [currentStep, policyNumber]);

  const photosRef = useRef(photos);
  photosRef.current = photos;
  useEffect(() => {
    return () => {
      photosRef.current.forEach((photo) => URL.revokeObjectURL(photo.url));
    };
  }, []);

  const next = () => setCurrentStep((s) => Math.min(3, s + 1));
  const back = () => setCurrentStep((s) => Math.max(1, s - 1));

  const handleClaimNumberFound = (claimNumber: string) => {
    setFnolNumber((prev) => prev ?? claimNumber);
  };

  const handleFnolRefresh = () => {
    const trimmedPolicy = policyNumber.trim();
    if (!trimmedPolicy) return;
    setSubmissionLoading(true);
    setSubmissionError(null);
    fetch(`/api/fnol-submission?policyNumber=${encodeURIComponent(trimmedPolicy)}`)
      .then((res) => {
        if (!res.ok) throw new Error("Could not refresh extracted loss details.");
        return res.json();
      })
      .then((data) => {
        setLossFields(Array.isArray(data?.fields) ? data.fields : []);
        setOverallConfidence(
          typeof data?.overallConfidence === "number" ? data.overallConfidence : null
        );
        if (typeof data?.id === "number" && data.id > 0) setFnolId(data.id);
        setFnolNumber((prev) =>
          prev ??
          (typeof data?.fnolNumber === "string" && data.fnolNumber.trim()
            ? data.fnolNumber.trim()
            : null)
        );
      })
      .catch((err) => {
        setSubmissionError(err instanceof Error ? err.message : "Refresh failed.");
      })
      .finally(() => setSubmissionLoading(false));
  };

  const addPhotos = (files: FileList) => {
    const incoming = Array.from(files).map((file) => ({
      id: `${file.name}-${file.size}-${file.lastModified}-${Math.random()
        .toString(36)
        .slice(2, 8)}`,
      name: file.name,
      url: URL.createObjectURL(file),
      isImage: file.type.startsWith("image/"),
      type: file.type,
      file,
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

  const updateHumanReview = (field: string, value: string) =>
    setHumanReview((prev) => ({ ...prev, [field]: value }));

  // Build a PATCH payload from humanReview entries that differ from the extracted values.
  // For each changed field, also sets the corresponding _source column to "human_edited"
  // so Stage 3 can show "Human Edited" instead of "AI Extracted".
  const buildEditPatch = () => {
    const patch: Record<string, string> = {};
    for (const [fieldLabel, editedValue] of Object.entries(humanReview)) {
      const original = lossFields.find((f) => f.field === fieldLabel)?.value ?? "";
      if (editedValue !== original) {
        const col = FIELD_TO_COLUMN[fieldLabel];
        if (col) patch[col] = editedValue;
        const sourceCol = FIELD_TO_SOURCE_COLUMN[fieldLabel];
        if (sourceCol) patch[sourceCol] = "human_edited";
      }
    }
    return patch;
  };

  // Called when the user clicks "Review and Confirm Fields" in Stage 2.
  // Silently persists any edited fields to the DB, then advances to Stage 3.
  const handleAdvanceToStage3 = async () => {
    if (isSavingEdits) return;
    setSaveEditsError(null);

    const patch = buildEditPatch();

    // Nothing to save — go straight to Stage 3.
    if (Object.keys(patch).length === 0) {
      next();
      return;
    }

    // Resolve fnolId — use cached state or re-fetch from the API.
    // fnolId can be null if the Vite plugin response wasn't available after
    // the last agent turn (e.g. dev server not yet restarted).
    let resolvedId = fnolId;
    if (resolvedId === null) {
      try {
        const r = await fetch(
          `/api/fnol-submission?policyNumber=${encodeURIComponent(policyNumber.trim())}`
        );
        if (r.ok) {
          const d = await r.json().catch(() => null);
          const raw = d?.id;
          const parsed = typeof raw === "number" ? raw : Number(raw) || null;
          if (parsed && parsed > 0) {
            resolvedId = parsed;
            setFnolId(parsed);
          }
        }
      } catch {
        // ignore — we'll skip the patch below if still null
      }
    }

    if (resolvedId === null) {
      // Can't patch without an ID — advance anyway (edits won't be persisted).
      next();
      return;
    }

    setIsSavingEdits(true);
    try {
      const res = await fetch(
        `${MCP_BASE}/api/v1/voice_text_intake/api/fnol/update_submission/${resolvedId}`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(patch),
        }
      );
      if (!res.ok) {
        const err = await res.json().catch(() => null);
        throw new Error((err && err.detail) || `Failed to save edits (${res.status})`);
      }
      next();
    } catch (err) {
      setSaveEditsError(
        err instanceof Error ? err.message : "Could not save field edits. Please try again."
      );
    } finally {
      setIsSavingEdits(false);
    }
  };

  // Called when the user clicks "Confirm & Submit FNOL" in Stage 3.
  // By this point field edits are already in the DB (saved on Stage 2 exit).
  // After the claim is created, staged evidence photos are uploaded to the
  // document submission endpoint so they appear in the Document Hub.
  const handleSubmit = async () => {
    if (isSubmitting) return;
    setIsSubmitting(true);
    setSubmitError(null);
    setUploadWarning(null);

    try {
      if (fnolId === null)
        throw new Error("FNOL record not found. Please go back and complete the chat.");

      // Persist estimated cost to fnol_submissions before submit so submit_fnol
      // can carry it into claims.estimated_cost.
      const costValue = parseFloat(estimatedCost);
      if (!isNaN(costValue) && costValue > 0) {
        await fetch(
          `${MCP_BASE}/api/v1/voice_text_intake/api/fnol/update_submission/${fnolId}`,
          {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ estimated_cost: costValue }),
          }
        ).catch(() => {});
      }

      const submitRes = await fetch(
        `${MCP_BASE}/api/v1/voice_text_intake/api/fnol/submit/${fnolId}`,
        { method: "POST" }
      );
      if (!submitRes.ok) {
        const err = await submitRes.json().catch(() => null);
        throw new Error((err && err.detail) || `Submission failed (${submitRes.status})`);
      }
      const result = await submitRes.json();
      const claimNumber = result?.claim_number ?? result?.fnol?.fnol_number ?? null;
      if (claimNumber) setFnolNumber(claimNumber);

      // Fire-and-forget: trigger background agent processing (PolicyCoverage →
      // Readiness → Segmentation → StatusLog) so Follow My Claims UI has data.
      if (claimNumber) {
        fetch(`${FNOL_ORCHESTRATOR_URL}/process`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ claim_number: claimNumber }),
        }).catch(() => {});
      }

      // Upload staged evidence photos now that we have a claim_number to link against.
      if (photos.length > 0 && claimNumber) {
        const uploadResults = await Promise.allSettled(
          photos.map((photo) => {
            const form = new FormData();
            form.append("claim_number", claimNumber);
            form.append("uploaded_by_role", "Policyholder");
            form.append("file", photo.file, photo.name);
            return fetch(
              `${MCP_BASE}/api/v1/document_submission/api/documents/upload`,
              { method: "POST", body: form }
            ).then((res) => {
              if (!res.ok) throw new Error(`${photo.name} — upload failed (${res.status})`);
            });
          })
        );

        const failed = uploadResults.filter((r) => r.status === "rejected");
        if (failed.length > 0) {
          const names = failed
            .map((r) => (r as PromiseRejectedResult).reason?.message ?? "unknown file")
            .join(", ");
          setUploadWarning(
            `${failed.length} of ${photos.length} evidence file${photos.length > 1 ? "s" : ""} could not be uploaded: ${names}. You can re-upload them from the Document Hub.`
          );
        }

        // Re-trigger background processing now that documents are in the DB
        // so the readiness check snapshot includes the uploaded evidence.
        const anyUploaded = uploadResults.some((r) => r.status === "fulfilled");
        if (anyUploaded) {
          fetch(`${FNOL_ORCHESTRATOR_URL}/process`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ claim_number: claimNumber }),
          }).catch(() => {});
        }
      }

      setSubmitted(true);
    } catch (err) {
      setSubmitError(
        err instanceof Error ? err.message : "Submission failed. Please try again."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const reset = () => {
    setSubmitted(false);
    setCurrentStep(1);
    setPolicyNumber("");
    setDescription("");
    setEstimatedCost("");
    setComments("");
    photos.forEach((photo) => URL.revokeObjectURL(photo.url));
    setPhotos([]);
    setHumanReview({});
    setChatMessages([]);
    setSectionA([]);
    setFnolId(null);
    setFnolNumber(null);
    setSaveEditsError(null);
    setSubmitError(null);
    setUploadWarning(null);
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
            Claim Reference: {fnolNumber ?? "Pending — check My Claims for your reference"}
          </div>
          {uploadWarning && (
            <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700 text-left max-w-md mx-auto">
              <span className="font-semibold">Evidence upload note: </span>
              {uploadWarning}
            </div>
          )}
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

      <StepTracker
        currentStep={currentStep}
        onStepClick={(step) => setCurrentStep(step)}
      />

      {currentStep === 1 && (
        <Stage1PolicyLookup
          policyNumber={policyNumber}
          onPolicyNumberChange={setPolicyNumber}
          description={description}
          onDescriptionChange={setDescription}
          estimatedCost={estimatedCost}
          onEstimatedCostChange={setEstimatedCost}
          onNext={next}
        />
      )}
      {currentStep === 2 && (
        <Stage2AnswerQuestions
          policyNumber={policyNumber}
          photos={photos}
          onAddPhotos={addPhotos}
          onRemovePhoto={removePhoto}
          comments={comments}
          onCommentsChange={setComments}
          humanReview={humanReview}
          onHumanReviewChange={updateHumanReview}
          messages={chatMessages}
          onMessagesChange={setChatMessages}
          initialDescription={description}
          lossFields={lossFields}
          overallConfidence={overallConfidence}
          submissionLoading={submissionLoading}
          submissionError={submissionError}
          onClaimNumberFound={handleClaimNumberFound}
          onFnolRefreshNeeded={handleFnolRefresh}
          isSavingEdits={isSavingEdits}
          saveEditsError={saveEditsError}
          onNext={() => { void handleAdvanceToStage3(); }}
          onBack={back}
        />
      )}
      {currentStep === 3 && (
        <Stage3ReviewForm
          policyNumber={policyNumber}
          sectionA={sectionA}
          photos={photos}
          comments={comments}
          humanReview={humanReview}
          lossFields={lossFields}
          isSubmitting={isSubmitting}
          submitError={submitError}
          onSubmit={() => { void handleSubmit(); }}
          onBack={back}
        />
      )}
    </div>
  );
}
