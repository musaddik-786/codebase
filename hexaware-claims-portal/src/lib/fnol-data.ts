export const customerText =
  "There was a water leak in my sink last night. The water broker and damaged the floor.";

export interface ExtractedRow {
  element: string;
  value: string;
  confidence: number;
}

export const extractedRows: ExtractedRow[] = [
  { element: "Loss Type", value: "Water Damage", confidence: 90 },
  { element: "Probable Cause", value: "Unknown - needs clarification", confidence: 85 },
  { element: "Area Mentioned", value: "Not specified", confidence: 87 },
  { element: "Date of Loss", value: 'June 21, 2026 (from "Last night")', confidence: 75 },
  { element: "Sudden vs Gradual", value: "Sudden", confidence: 70 },
];

export interface PolicyField {
  label: string;
  value: string;
}

export const policyInfo: PolicyField[] = [
  { label: "Policy Number", value: "HO-2025-78901234" },
  { label: "Insured Name", value: "John Davis" },
  { label: "Insured Address", value: "123 Main Street, Austin, TX 78701" },
  { label: "Policy Period", value: "01/01/2025 - 01/01/2026" },
];

export interface Question {
  question: string;
  options: string[];
}

export const questions: Question[] = [
  {
    question:
      'You mentioned "Last night". We\'ve set the loss date as June 21, 2026. Is this correct?',
    options: ["Yes, June 21, 2026", "No, let me specify the correct date"],
  },
  {
    question: "Which area of your home was affected?",
    options: ["Kitchen", "Bathroom", "Basement / Lower level", "Other / Not sure"],
  },
  {
    question: "Were emergency services or a plumber contacted?",
    options: ["Yes", "No"],
  },
  {
    question: "Was the damage sudden or did it develop gradually?",
    options: ["Sudden", "Gradual"],
  },
];

export const sectionA: PolicyField[] = [
  { label: "Policy Number", value: "HO-2025-78901234" },
  { label: "Insured Name", value: "John Davis" },
  { label: "Insured Address", value: "123 Main Street, Austin, TX 78701" },
];

export type LossSource = "AI-Inferred" | "Customer-Confirmed" | "Customer-Provided";

export interface LossRow {
  field: string;
  required: boolean;
  value: string;
  source: LossSource;
  extractedFrom: string;
}

export const sectionB: LossRow[] = [
  {
    field: "Type of Loss",
    required: true,
    value: "Water Damage",
    source: "AI-Inferred",
    extractedFrom: '"There was a water leak in my si..."',
  },
  {
    field: "Cause of Loss",
    required: true,
    value: "Unknown - needs clarification",
    source: "AI-Inferred",
    extractedFrom: '"There was a water leak in my si..."',
  },
  {
    field: "Area Affected",
    required: true,
    value: "Not specified",
    source: "AI-Inferred",
    extractedFrom: '"There was a water leak in my si..."',
  },
  {
    field: "Time of Loss",
    required: false,
    value: "Night",
    source: "AI-Inferred",
    extractedFrom: '"There was a water leak in my si..."',
  },
  {
    field: "Sudden vs Gradual",
    required: true,
    value: "Sudden",
    source: "AI-Inferred",
    extractedFrom: '"There was a water leak in my si..."',
  },
  {
    field: "Date of Loss",
    required: true,
    value: "June 21, 2026",
    source: "Customer-Confirmed",
    extractedFrom: "Confirmed by you",
  },
  {
    field: "Occupancy at Time of Loss",
    required: true,
    value: "Unknown",
    source: "AI-Inferred",
    extractedFrom: "Could not determine",
  },
  {
    field: "Emergency Services Contacted",
    required: false,
    value: "Yes",
    source: "Customer-Provided",
    extractedFrom: "Your answer to question",
  },
];

export interface AiField {
  label: string;
  value: string;
  confidence: number;
  required: boolean;
  extractedFrom: string;
}

export const aiFields: AiField[] = [
  {
    label: "Type of Loss",
    value: "Water Damage",
    confidence: 90,
    required: true,
    extractedFrom: '"There was a water leak in my sink last night. The ..."',
  },
  {
    label: "Cause of Loss",
    value: "Unknown - needs clarification",
    confidence: 85,
    required: true,
    extractedFrom: '"There was a water leak in my sink last night. The ..."',
  },
  {
    label: "Area Affected",
    value: "Not specified",
    confidence: 87,
    required: true,
    extractedFrom: '"There was a water leak in my sink last night. The ..."',
  },
  {
    label: "Time of Loss",
    value: "Night",
    confidence: 60,
    required: false,
    extractedFrom: '"There was a water leak in my sink last night. The ..."',
  },
  {
    label: "Sudden vs Gradual",
    value: "Sudden",
    confidence: 70,
    required: true,
    extractedFrom: '"There was a water leak in my sink last night. The ..."',
  },
  {
    label: "Occupancy at Time of Loss",
    value: "Unknown",
    confidence: 50,
    required: true,
    extractedFrom: "Could not determine",
  },
];
