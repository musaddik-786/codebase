export type PersonaId = "policyholder" | "adjuster" | "siu" | "vendor" | "orchestrator";

export interface AgentDef {
  name: string;
  slug: string;
  port: number;
  baseUrl: string;
  status: "full" | "placeholder";
  description: string;
  quickTestPrompt: string;
}

export interface PersonaDef {
  id: PersonaId;
  label: string;
  description: string;
  color: string;
  mcpPort: number;
  agents: AgentDef[];
}

const baseUrl = (port: number) => `http://localhost:${port}`;

export const personas: Record<PersonaId, PersonaDef> = {
  policyholder: {
    id: "policyholder",
    label: "Policyholder",
    description: "Digital Self-Service",
    color: "policyholder",
    mcpPort: 7700,
    agents: [
      {
        name: "FNOLOrchestrator", slug: "fnol_orchestrator", port: 7710, baseUrl: baseUrl(7710), status: "full",
        description: "Orchestrates full policyholder intake: FNOL collection + document submission in one conversation",
        quickTestPrompt: "I need to file a claim. There was water damage in my kitchen — a pipe burst under the sink.",
      },
      {
        name: "VoiceTextIntakeAgent", slug: "voice_text_intake", port: 7701, baseUrl: baseUrl(7701), status: "full",
        description: "FNOL intake via voice transcript or typed description",
        quickTestPrompt: "I had a car accident on June 10th 2026 at the intersection of Main St and 5th Ave. Another driver ran a red light and hit my front bumper. Significant damage to hood and bumper. No injuries. Policy number POL-2024-88821.",
      },
      {
        name: "DuplicateClaimCheckAgent", slug: "duplicate_check", port: 7702, baseUrl: baseUrl(7702), status: "full",
        description: "Detects duplicate FNOL submissions for the same incident",
        quickTestPrompt: "Check if there are any duplicate claims for claim CLM-2026-1001",
      },
      {
        name: "ClaimSegmentationAgent", slug: "segmentation", port: 7703, baseUrl: baseUrl(7703), status: "full",
        description: "Segments claim by loss type, severity, and handling route",
        quickTestPrompt: "Segment claim CLM-2026-1001 and recommend the appropriate handling path",
      },
      {
        name: "ClaimStatusAgent", slug: "claim_status", port: 7704, baseUrl: baseUrl(7704), status: "full",
        description: "Returns real-time claim status and stage progress",
        quickTestPrompt: "What is the current status of claim CLM-2026-1001?",
      },
      {
        name: "DocumentSubmissionAgent", slug: "document_submission", port: 7705, baseUrl: baseUrl(7705), status: "full",
        description: "Uploads documents, classifies by type with embeddings, extracts evidence, links to FNOL",
        quickTestPrompt: "For claim CLM-2026-1001: I am submitting a police report. Case #PR-2026-4421. Incident date: June 10 2026. Location: Main St & 5th Ave. Reporting Officer: Sgt. Maria Torres, Badge #4892. Vehicle collision — rear-end impact. Witnesses: James Wu (415-555-0198). No arrests made. Property damage estimated at $8,500.",
      },
      {
        name: "FeedbackAgent", slug: "feedback", port: 7706, baseUrl: baseUrl(7706), status: "full",
        description: "Captures policyholder sentiment and satisfaction feedback",
        quickTestPrompt: "For claim CLM-2026-1001: The process was smooth and I received clear updates at each stage. Very satisfied with the speed of resolution.",
      },
      {
        name: "PolicyCoverageVerificationAgent", slug: "policy_coverage", port: 7707, baseUrl: baseUrl(7707), status: "full",
        description: "Verifies policy coverage applicability and net payable for a claim",
        quickTestPrompt: "Verify coverage for claim CLM-2026-1001",
      },
      {
        name: "ClaimReadinessAgent", slug: "claim_readiness", port: 7708, baseUrl: baseUrl(7708), status: "full",
        description: "Scores FNOL completeness and claim submission readiness",
        quickTestPrompt: "Score the readiness of claim CLM-2026-1001 for formal submission",
      },
      {
        name: "CommunicationAgent", slug: "communication", port: 7709, baseUrl: baseUrl(7709), status: "full",
        description: "Drafts status notification messages to the policyholder",
        quickTestPrompt: "Draft a status notification for claim CLM-2026-1001",
      },
    ],
  },
  adjuster: {
    id: "adjuster",
    label: "Claims Adjuster",
    description: "Claim Intake to Settlement",
    color: "adjuster",
    mcpPort: 8900,
    agents: [
      {
        name: "AdjusterOrchestrator", slug: "adjuster_orchestrator", port: 8920, baseUrl: baseUrl(8920), status: "full",
        description: "Orchestrates the full Claim Intake → Settlement flow across all 15 adjuster agents with HITL gates",
        quickTestPrompt: "Run the adjuster workflow for claim CLM-2026-1001",
      },
      {
        name: "ClaimClassificationAgent", slug: "claim_classification", port: 8901, baseUrl: baseUrl(8901), status: "full",
        description: "Classifies claim by damage type, severity, complexity, and fraud risk score",
        quickTestPrompt: "Classify claim CLM-2026-1001",
      },
      {
        name: "TriageAgent", slug: "triage", port: 8902, baseUrl: baseUrl(8902), status: "full",
        description: "Runs triage to assign severity level and routing priority",
        quickTestPrompt: "Run triage on claim CLM-2026-1001",
      },
      {
        name: "FraudScreeningAgent", slug: "fraud_screening", port: 8903, baseUrl: baseUrl(8903), status: "full",
        description: "Screens for fraud red flags using AI signals and history",
        quickTestPrompt: "Screen claim CLM-2026-1001 for fraud indicators",
      },
      {
        name: "RoutingAgent", slug: "routing", port: 8904, baseUrl: baseUrl(8904), status: "full",
        description: "Routes claim to the right adjuster based on complexity and specialization",
        quickTestPrompt: "Route claim CLM-2026-1001 to the appropriate adjuster",
      },
      {
        name: "EvidenceValidationAgent", slug: "evidence_validation", port: 8905, baseUrl: baseUrl(8905), status: "full",
        description: "Validates submitted evidence items for completeness and authenticity",
        quickTestPrompt: "Validate all evidence submitted for claim CLM-2026-1001",
      },
      {
        name: "ExternalDataAgent", slug: "external_data", port: 8906, baseUrl: baseUrl(8906), status: "full",
        description: "Fetches weather, drone imagery, and third-party verification data",
        quickTestPrompt: "Fetch external data (weather and drone imagery) for claim CLM-2026-1001",
      },
      {
        name: "DamageAssessmentAgent", slug: "damage_assessment", port: 8907, baseUrl: baseUrl(8907), status: "full",
        description: "Assesses damage items, conditions, and estimated repair costs",
        quickTestPrompt: "Assess the damage for claim CLM-2026-1001",
      },
      {
        name: "VerificationAgent", slug: "verification", port: 8908, baseUrl: baseUrl(8908), status: "full",
        description: "Runs identity, policy, and external cross-verification checks",
        quickTestPrompt: "Run all verification checks for claim CLM-2026-1001",
      },
      {
        name: "LossAssessmentAgent", slug: "loss_assessment", port: 8909, baseUrl: baseUrl(8909), status: "full",
        description: "Calculates total estimated loss and net payable amount",
        quickTestPrompt: "Assess the total loss for claim CLM-2026-1001",
      },
      {
        name: "ReserveRecommendationAgent", slug: "reserve_recommendation", port: 8910, baseUrl: baseUrl(8910), status: "full",
        description: "Recommends reserve amount based on loss estimates and fraud risk",
        quickTestPrompt: "Recommend a reserve amount for claim CLM-2026-1001",
      },
      {
        name: "FinancialLeakageAgent", slug: "financial_leakage", port: 8911, baseUrl: baseUrl(8911), status: "full",
        description: "Scores financial leakage risk — overbilling, duplication, inflated costs",
        quickTestPrompt: "Score financial leakage risk for claim CLM-2026-1001",
      },
      {
        name: "RepairVsReplacementAgent", slug: "repair_vs_replacement", port: 8912, baseUrl: baseUrl(8912), status: "full",
        description: "Compares repair vs replacement cost and recommends the better option",
        quickTestPrompt: "Recommend repair vs replacement for claim CLM-2026-1001",
      },
      {
        name: "SettlementRecommendationAgent", slug: "settlement_recommendation", port: 8913, baseUrl: baseUrl(8913), status: "full",
        description: "Recommends settlement action: STP, negotiate, or escalate",
        quickTestPrompt: "Recommend settlement action for claim CLM-2026-1001",
      },
      {
        name: "PaymentEligibilityAgent", slug: "payment_eligibility", port: 8914, baseUrl: baseUrl(8914), status: "full",
        description: "Checks all payment eligibility gates before triggering disbursement",
        quickTestPrompt: "Check payment eligibility for claim CLM-2026-1001",
      },
      {
        name: "PaymentTriggerAgent", slug: "payment_trigger", port: 8915, baseUrl: baseUrl(8915), status: "full",
        description: "Triggers payment disbursement once all eligibility checks pass",
        quickTestPrompt: "Trigger payment for claim CLM-2026-1001",
      },
    ],
  },
  siu: {
    id: "siu",
    label: "SIU Investigator",
    description: "Fraud Detection & Investigation",
    color: "siu",
    mcpPort: 9000,
    agents: [
      {
        name: "FraudRiskScoringAgent", slug: "fraud_risk_scoring", port: 9001, baseUrl: baseUrl(9001), status: "full",
        description: "Scores overall fraud risk from signals, flags, and claim history",
        quickTestPrompt: "Score fraud risk for claim CLM-2026-1001",
      },
      {
        name: "CaseAssignmentAgent", slug: "case_assignment", port: 9002, baseUrl: baseUrl(9002), status: "full",
        description: "Assigns the SIU case to the best available investigator",
        quickTestPrompt: "Assign an investigator to claim CLM-2026-1001",
      },
      {
        name: "BehavioralAnalyticsAgent", slug: "behavioral_analytics", port: 9003, baseUrl: baseUrl(9003), status: "full",
        description: "Analyzes claimant/vendor behavior for frequency and timing anomalies",
        quickTestPrompt: "Analyze behavioral patterns for SIU case SIU-2026-0001",
      },
      {
        name: "EntityRelationshipAgent", slug: "entity_relationship", port: 9004, baseUrl: baseUrl(9004), status: "full",
        description: "Builds entity relationship graph linking claimants, vendors, and adjusters",
        quickTestPrompt: "Build the entity relationship graph for claim CLM-2026-1001",
      },
      {
        name: "FraudPatternAgent", slug: "fraud_pattern", port: 9005, baseUrl: baseUrl(9005), status: "full",
        description: "Detects known fraud patterns and generates risk flags",
        quickTestPrompt: "Detect fraud patterns for claim CLM-2026-1001",
      },
      {
        name: "NetworkAnalysisAgent", slug: "network_analysis", port: 9006, baseUrl: baseUrl(9006), status: "full",
        description: "Detects fraud rings and collusion patterns in the claim network",
        quickTestPrompt: "Detect fraud rings connected to claim CLM-2026-1001",
      },
      {
        name: "EvidenceCorrelationAgent", slug: "evidence_correlation", port: 9007, baseUrl: baseUrl(9007), status: "full",
        description: "Cross-references notes, timeline events, and evidence for inconsistencies",
        quickTestPrompt: "Correlate all evidence for claim CLM-2026-1001",
      },
      {
        name: "FraudEscalationAgent", slug: "fraud_escalation", port: 9008, baseUrl: baseUrl(9008), status: "full",
        description: "Escalates high-risk fraud claims to SIU for full investigation",
        quickTestPrompt: "Escalate claim CLM-2026-1001 to SIU — fraud score above threshold",
      },
      {
        name: "FraudResolutionAgent", slug: "fraud_resolution", port: 9009, baseUrl: baseUrl(9009), status: "full",
        description: "Records the SIU investigation decision and closes the case",
        quickTestPrompt: "Resolve SIU case SIU-2026-0001 with a confirmed fraud decision",
      },
      {
        name: "LegalEscalationAgent", slug: "legal_escalation", port: 9010, baseUrl: baseUrl(9010), status: "full",
        description: "Refers confirmed fraud cases to legal for prosecution or recovery",
        quickTestPrompt: "Refer SIU case SIU-2026-0001 to legal escalation",
      },
      {
        name: "WatchlistUpdateAgent", slug: "watchlist_update", port: 9011, baseUrl: baseUrl(9011), status: "full",
        description: "Adds confirmed fraudsters to the fraud watchlist",
        quickTestPrompt: "Add the claimant from claim CLM-2026-1001 to the fraud watchlist",
      },
      {
        name: "SIUClosureAgent", slug: "siu_closure", port: 9012, baseUrl: baseUrl(9012), status: "full",
        description: "Checks closure readiness and closes the SIU investigation",
        quickTestPrompt: "Check closure readiness for SIU case SIU-2026-0001",
      },
    ],
  },
  vendor: {
    id: "vendor",
    label: "Vendor Manager",
    description: "Vendor & Field Operations",
    color: "vendor",
    mcpPort: 9100,
    agents: [
      {
        name: "VendorOnboardingAgent", slug: "vendor_onboarding", port: 9101, baseUrl: baseUrl(9101), status: "full",
        description: "Submits and approves vendor applications, creates vendor_master records",
        quickTestPrompt: "Submit a new vendor application: AutoFix Pro, specialty: Auto Repair, location: San Francisco CA, license: LIC-2024-8821, insurance valid until 2027-06-01",
      },
      {
        name: "VendorMatchingAgent", slug: "vendor_matching", port: 9102, baseUrl: baseUrl(9102), status: "full",
        description: "Matches the best available vendor to a claim based on specialty and location",
        quickTestPrompt: "Match a vendor for claim CLM-2026-1001",
      },
      {
        name: "VendorQualificationAgent", slug: "vendor_qualification", port: 9103, baseUrl: baseUrl(9103), status: "full",
        description: "Scores vendor compliance: license, insurance, certifications, background check",
        quickTestPrompt: "Score qualification for vendor VND-2024-001",
      },
      {
        name: "VendorCapacityManagementAgent", slug: "vendor_capacity", port: 9104, baseUrl: baseUrl(9104), status: "full",
        description: "Evaluates vendor workload vs capacity threshold and throttles assignment eligibility",
        quickTestPrompt: "Check capacity status for vendor VND-2024-001",
      },
      {
        name: "VendorCostBenchmarkAgent", slug: "vendor_cost_benchmark", port: 9105, baseUrl: baseUrl(9105), status: "full",
        description: "Benchmarks vendor cost estimates against market rates and flags overages",
        quickTestPrompt: "Benchmark costs for vendor VND-2024-001 on claim CLM-2026-1001",
      },
      {
        name: "DispatchAgent", slug: "dispatch", port: 9106, baseUrl: baseUrl(9106), status: "full",
        description: "Creates work orders and dispatches vendors to the field",
        quickTestPrompt: "Dispatch vendor VND-2024-001 to claim CLM-2026-1001 for auto repair",
      },
      {
        name: "VendorPerformanceAgent", slug: "vendor_performance", port: 9107, baseUrl: baseUrl(9107), status: "full",
        description: "Calculates vendor performance score (VIS) from ratings and job history",
        quickTestPrompt: "Calculate performance score for vendor VND-2024-001",
      },
      {
        name: "SLAComplianceAgent", slug: "sla_compliance", port: 9108, baseUrl: baseUrl(9108), status: "full",
        description: "Checks vendor SLA compliance across active jobs",
        quickTestPrompt: "Check SLA compliance for vendor VND-2024-001",
      },
      {
        name: "EscalationAgent", slug: "vendor_escalation", port: 9109, baseUrl: baseUrl(9109), status: "full",
        description: "Escalates overdue or non-compliant vendor jobs",
        quickTestPrompt: "Escalate overdue jobs for vendor VND-2024-001 on claim CLM-2026-1001",
      },
      {
        name: "ETAPredictionAgent", slug: "eta_prediction", port: 9110, baseUrl: baseUrl(9110), status: "full",
        description: "Predicts job completion ETA based on workload and historical performance",
        quickTestPrompt: "Predict the ETA for claim CLM-2026-1001 with vendor VND-2024-001",
      },
    ],
  },
  orchestrator: {
    id: "orchestrator",
    label: "Orchestrator / HITL",
    description: "Orchestrates end-to-end claim lifecycle with human-in-the-loop approvals",
    color: "orchestrator",
    mcpPort: 9200,
    agents: [
      {
        name: "OrchestratorBrainAgent", slug: "orchestration", port: 9201, baseUrl: baseUrl(9201), status: "full",
        description: "Drives the full claim lifecycle and manages HITL approval gates",
        quickTestPrompt: "Advance claim CLM-2026-1001 through the next stage of the claim lifecycle",
      },
    ],
  },
};

export const ORCHESTRATION_MCP_BASE = `http://localhost:9200/api/v1/orchestration/api/orchestration`;

export const adjusterGroups: { title: string; slugs: string[] }[] = [
  { title: "Full Adjuster Orchestrator", slugs: ["adjuster_orchestrator"] },
  { title: "Claim Intake & Triage", slugs: ["claim_classification", "triage", "fraud_screening", "routing"] },
  { title: "Loss Investigation", slugs: ["evidence_validation", "external_data", "damage_assessment", "verification"] },
  { title: "Loss Assessment", slugs: ["loss_assessment", "reserve_recommendation", "financial_leakage", "repair_vs_replacement"] },
  { title: "Claim Decision & Settlement", slugs: ["settlement_recommendation", "payment_eligibility", "payment_trigger"] },
];

export const siuGroups: { title: string; slugs: string[] }[] = [
  { title: "Fraud Intake", slugs: ["fraud_risk_scoring", "case_assignment"] },
  { title: "Fraud Investigation", slugs: ["behavioral_analytics", "network_analysis", "entity_relationship", "evidence_correlation", "fraud_pattern"] },
  { title: "Fraud Resolution", slugs: ["fraud_resolution", "legal_escalation", "watchlist_update", "siu_closure", "fraud_escalation"] },
];

export const vendorGroups: { title: string; slugs: string[] }[] = [
  { title: "Smart Vendor Match & Assignment", slugs: ["vendor_onboarding", "vendor_matching", "vendor_qualification", "vendor_cost_benchmark", "eta_prediction"] },
  { title: "Dispatch & Capacity", slugs: ["dispatch", "vendor_capacity"] },
  { title: "Vendor Management", slugs: ["vendor_performance", "sla_compliance", "vendor_escalation"] },
];

export const policyholderGroups: { title: string; slugs: string[] }[] = [
  { title: "File a New Claim", slugs: ["fnol_orchestrator"] },
  { title: "Follow My Claim", slugs: ["claim_status", "claim_readiness"] },
  { title: "Submit Documents", slugs: ["document_submission"] },
  { title: "Coverage & Communication", slugs: ["policy_coverage", "communication"] },
  { title: "Other Agents", slugs: ["duplicate_check", "segmentation", "feedback"] },
];

export const REQUIRED_GATES = [
  "damage_assessment_review",
  "reserve_approval",
  "settlement_approval",
  "siu_decision_approval",
  "payment_approval",
  "claim_closure_approval",
];

export const OPTIONAL_GATES = [
  "fnol_review",
  "triage_approval",
  "vendor_assignment_approval",
];
