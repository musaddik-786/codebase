export interface ClaimJourneyUpdate {
  title: string;
  actor: string;
  detail: string;
  timestamp: string;
}

export interface ClaimJourney {
  id: string;
  status: string;
  policyNumber: string;
  policyholder: string;
  type: string;
  dateOfLoss: string;
  stages: string[];
  stageIndex: number;
  whatsHappeningNow: string;
  whatHappensNext: string;
  nextStatusLabel: string;
  latestUpdate: ClaimJourneyUpdate | null;
  updates: ClaimJourneyUpdate[];
  progress: number;
  estCompletion: string;
}

export interface ClaimInsights {
  // Readiness (ClaimReadinessAgent)
  completenessScore: number | null;
  missingFields: string[] | null;
  docsStatus: string | null;
  missingDocs: string[] | null;
  overallResult: string | null;
  // Segmentation (ClaimSegmentationAgent)
  stpCategory: string | null;
  severity: string | null;
  complexity: string | null;
  // Coverage (PolicyCoverageVerificationAgent)
  coverageVerdict: string | null;
  netPayable: number | null;
  exclusionTriggered: boolean;
  exclusionDetails: string | null;
}
