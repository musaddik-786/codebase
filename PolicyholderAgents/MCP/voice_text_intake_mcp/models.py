from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Union


def _coerce_bool(v):
    """Accept bool, or truthy strings like 'yes'/'true'/'1' from the LLM."""
    if v is None or isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.lower() in ("true", "yes", "1", "occupied", "y")
    return bool(v)


class CreateFnolSubmissionRequest(BaseModel):
    fnol_number: Optional[str] = Field(None, description="Unique FNOL identifier, e.g. FNOL-2026-00123. Auto-generated if omitted.")
    policy_number: str
    policyholder_name: Optional[str] = None
    policyholder_address: Optional[str] = None
    policy_effective_date: Optional[str] = None
    policy_expiration_date: Optional[str] = None
    loss_type: Optional[str] = None
    cause_of_loss: Optional[str] = None
    date_of_loss: Optional[str] = None
    time_of_loss: Optional[str] = None
    area_affected: Optional[str] = None
    occupancy_at_loss: Optional[bool] = None
    sudden_vs_gradual: Optional[str] = None
    emotional_context: Optional[str] = None
    severity: Optional[str] = None
    urgency_indicator: Optional[str] = None
    voice_transcript: Optional[str] = None
    text_input: Optional[str] = None
    overall_confidence: Optional[int] = None
    confidence_notes: Optional[str] = None
    status: Optional[str] = "draft"

    @field_validator("occupancy_at_loss", mode="before")
    @classmethod
    def parse_occupancy_create(cls, v):
        return _coerce_bool(v)


class UpdateFnolSubmissionRequest(BaseModel):
    policy_number: Optional[str] = None
    policyholder_name: Optional[str] = None
    policyholder_address: Optional[str] = None
    loss_type: Optional[str] = None
    loss_type_source: Optional[str] = None
    cause_of_loss: Optional[str] = None
    cause_of_loss_source: Optional[str] = None
    date_of_loss: Optional[str] = None
    date_of_loss_source: Optional[str] = None
    time_of_loss: Optional[str] = None
    time_of_loss_source: Optional[str] = None
    area_affected: Optional[str] = None
    area_affected_source: Optional[str] = None
    occupancy_at_loss: Optional[bool] = None
    occupancy_at_loss_source: Optional[str] = None
    sudden_vs_gradual: Optional[str] = None
    sudden_vs_gradual_source: Optional[str] = None
    emotional_context: Optional[str] = None
    emotional_context_source: Optional[str] = None
    severity: Optional[str] = None
    severity_source: Optional[str] = None
    urgency_indicator: Optional[str] = None
    urgency_indicator_source: Optional[str] = None
    voice_transcript: Optional[str] = None
    text_input: Optional[str] = None
    overall_confidence: Optional[int] = None
    confidence_notes: Optional[str] = None
    status: Optional[str] = None
    estimated_cost: Optional[float] = None

    @field_validator("occupancy_at_loss", mode="before")
    @classmethod
    def parse_occupancy_update(cls, v):
        return _coerce_bool(v)


class ExtractFnolFieldsRequest(BaseModel):
    raw_text: str = Field(..., description="Voice transcript (from browser STT) or free-text description from the policyholder")
    fnol_id: int = Field(..., description="FNOL submission ID to attach extraction results to")
    input_type: Optional[str] = Field("text", description="'voice_transcript' or 'text'")


class SaveVoiceTextExtractionRequest(BaseModel):
    fnol_id: int
    input_type: str = Field(..., description="'voice_transcript' or 'text'")
    raw_input: Optional[str] = None
    transcribed_text: Optional[str] = None
    extracted_loss_type: Optional[str] = None
    extracted_cause: Optional[str] = None
    extracted_area: Optional[str] = None
    extracted_temporal: Optional[str] = None
    sudden_gradual_signal: Optional[str] = None
    emotional_context: Optional[str] = None
    extraction_confidence: Optional[float] = None


class AiInferenceItem(BaseModel):
    field_name: str
    inferred_value: Optional[str] = None
    confidence: Optional[float] = None
    source: str = Field(..., description="'voice_transcript', 'text_input', 'ai_inferred'")
    source_details: Optional[str] = None


class SaveAiInferencesRequest(BaseModel):
    fnol_id: int
    inferences: List[AiInferenceItem]


class LogQuestionAnswerRequest(BaseModel):
    fnol_id: int
    question_text: str
    field_name: str
    answer_text: Optional[str] = None
    answer_type: Optional[str] = None
    was_skipped: Optional[bool] = False
    question_order: Optional[int] = 0


class FieldAttributionItem(BaseModel):
    field_name: str
    field_label: str
    field_value: Optional[str] = None
    source: str
    confidence: Optional[int] = None
    was_edited: Optional[bool] = False
    was_confirmed: Optional[bool] = False
    original_value: Optional[str] = None
    edited_value: Optional[str] = None


class SaveFieldAttributionRequest(BaseModel):
    fnol_id: int
    attributions: List[FieldAttributionItem]
