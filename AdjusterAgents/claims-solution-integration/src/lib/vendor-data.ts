export interface Vendor {
  id: string;
  name: string;
  specialty: string;
  location: string;
  licenseExpiry: string;
  rating: number | null;
  status: "Active" | "Inactive" | "Under Review" | "Suspended";
  assignmentEligible: boolean;
  licenseNumber: string;
  vis?: number;
}

export const vendors: Vendor[] = [
  { id: "VND-2101", name: "Precision Auto Body Works", specialty: "Body Repair", location: "CA", licenseExpiry: "2027-01-15", rating: null, status: "Active", assignmentEligible: true, licenseNumber: "BR-CA-44012" },
  { id: "VND-2102", name: "ColorPro Paint & Refinish", specialty: "Paints", location: "CA", licenseExpiry: "2027-02-15", rating: null, status: "Active", assignmentEligible: true, licenseNumber: "PT-CA-44102" },
  { id: "VND-2103", name: "MechanixOne Auto Service", specialty: "Mechanical Repair", location: "TX", licenseExpiry: "2027-03-15", rating: null, status: "Active", assignmentEligible: true, licenseNumber: "MR-TX-44210" },
  { id: "VND-2104", name: "ClearShield Auto Glass", specialty: "Glass Repair", location: "FL", licenseExpiry: "2027-04-15", rating: null, status: "Active", assignmentEligible: true, licenseNumber: "GR-FL-44310" },
  { id: "VND-1003", name: "StormGuard Services", specialty: "Wind", location: "FL", licenseExpiry: "2027-06-20", rating: 3.1, status: "Active", assignmentEligible: true, licenseNumber: "WD-FL-31220", vis: 66 },
  { id: "VND-1004", name: "ProBuild Contractors", specialty: "Structural", location: "TX", licenseExpiry: "2026-09-10", rating: 3.4, status: "Active", assignmentEligible: true, licenseNumber: "ST-TX-31450", vis: 69 },
  { id: "VND-1005", name: "ClearView Glass", specialty: "Glass/Windows", location: "IL", licenseExpiry: "2027-01-25", rating: 3.7, status: "Active", assignmentEligible: true, licenseNumber: "GW-IL-31510", vis: 71 },
  { id: "VND-1006", name: "AquaShield Plumbing", specialty: "Water", location: "OH", licenseExpiry: "2026-12-15", rating: 3.9, status: "Active", assignmentEligible: true, licenseNumber: "WT-OH-31620", vis: 73 },
  { id: "VND-1007", name: "RoofMasters Inc", specialty: "Roofing", location: "GA", licenseExpiry: "2027-03-05", rating: 4.1, status: "Active", assignmentEligible: true, licenseNumber: "RF-GA-31710", vis: 76 },
  { id: "VND-1010", name: "FloodStop Remediation", specialty: "Water", location: "LA", licenseExpiry: "2027-05-18", rating: 4.8, status: "Active", assignmentEligible: true, licenseNumber: "WT-LA-32010", vis: 93 },
  { id: "VND-1011", name: "PrimeCraft Builders", specialty: "Structural", location: "NJ", licenseExpiry: "2027-04-22", rating: 4.7, status: "Active", assignmentEligible: true, licenseNumber: "ST-NJ-32110", vis: 90 },
  { id: "VND-1012", name: "SafeHaven Security", specialty: "Security Systems", location: "WA", licenseExpiry: "2027-02-28", rating: 4.6, status: "Active", assignmentEligible: true, licenseNumber: "SS-WA-32210", vis: 87 },
  { id: "VND-1013", name: "TrueNorth Roofing", specialty: "Roofing", location: "MN", licenseExpiry: "2026-11-30", rating: 3.5, status: "Active", assignmentEligible: true, licenseNumber: "RF-MN-32310", vis: 67 },
  { id: "VND-1014", name: "AllStar Maintenance", specialty: "General", location: "MI", licenseExpiry: "2026-10-12", rating: 3.3, status: "Active", assignmentEligible: true, licenseNumber: "GN-MI-32410", vis: 64 },
  { id: "VND-1015", name: "QuickFix Handyman", specialty: "General", location: "AZ", licenseExpiry: "2026-08-19", rating: 3.2, status: "Suspended", assignmentEligible: false, licenseNumber: "GN-AZ-32510", vis: 65 },
  { id: "VND-1016", name: "BrightSpark Electric", specialty: "Electrical", location: "CO", licenseExpiry: "2027-01-08", rating: 3.6, status: "Active", assignmentEligible: true, licenseNumber: "EL-CO-32610", vis: 70 },
  { id: "VND-1017", name: "SteelFrame Structural", specialty: "Structural", location: "PA", licenseExpiry: "2026-12-01", rating: 3.4, status: "Active", assignmentEligible: true, licenseNumber: "ST-PA-32710", vis: 68 },
  { id: "VND-1018", name: "AquaPure Water Services", specialty: "Water", location: "NC", licenseExpiry: "2027-03-14", rating: 3.5, status: "Active", assignmentEligible: true, licenseNumber: "WT-NC-32810", vis: 69 },
  { id: "VND-1019", name: "SummitView Construction", specialty: "Roofing", location: "UT", licenseExpiry: "2027-06-02", rating: 4.5, status: "Active", assignmentEligible: true, licenseNumber: "RF-UT-32910", vis: 82 },
  { id: "VND-1020", name: "FireGuard Systems", specialty: "Fire", location: "NV", licenseExpiry: "2026-09-25", rating: 3.0, status: "Under Review", assignmentEligible: false, licenseNumber: "FR-NV-33010", vis: 61 },
  { id: "VND-1021", name: "GreenLeaf Salvage Auto", specialty: "Salvage", location: "OR", licenseExpiry: "2027-02-11", rating: 4.2, status: "Active", assignmentEligible: true, licenseNumber: "SV-OR-33110", vis: 78 },
  { id: "VND-1009", name: "GreenTree Landscaping", specialty: "Landscaping", location: "AZ", licenseExpiry: "2026-07-30", rating: 4.4, status: "Inactive", assignmentEligible: false, licenseNumber: "LS-AZ-31910", vis: 84 },
  { id: "VND-1008", name: "ElectriFix Solutions", specialty: "Electrical", location: "NY", licenseExpiry: "2026-06-15", rating: 2.9, status: "Inactive", assignmentEligible: false, licenseNumber: "EL-NY-31810", vis: 62 },
  { id: "VND-1001", name: "Apex Repairs", specialty: "Fire", location: "NY", licenseExpiry: "2026-05-20", rating: 2.5, status: "Inactive", assignmentEligible: false, licenseNumber: "FR-NY-31110", vis: 60 },
  { id: "VND-1002", name: "BlueLine Restoration", specialty: "Water", location: "CA", licenseExpiry: "2026-04-10", rating: 2.8, status: "Inactive", assignmentEligible: false, licenseNumber: "WT-CA-31210", vis: 63 },
  { id: "VND-1022", name: "SecureTech Systems", specialty: "Security Systems", location: "GA", licenseExpiry: "2026-08-08", rating: 3.8, status: "Inactive", assignmentEligible: false, licenseNumber: "SS-GA-33210", vis: 74 },
];

export interface DeactivatedVendor {
  name: string;
  id: string;
  immediate: boolean;
  reason: string | null;
}

export const deactivatedVendors: DeactivatedVendor[] = [
  { name: "GreenTree Landscaping", id: "VND-1009", immediate: false, reason: null },
  { name: "ElectriFix Solutions", id: "VND-1008", immediate: true, reason: "Poor SLA performance" },
  { name: "Apex Repairs", id: "VND-1001", immediate: true, reason: "Poor SLA performance" },
  { name: "BlueLine Restoration", id: "VND-1002", immediate: true, reason: "Manager Decision, Fraud suspicion" },
  { name: "SecureTech Systems", id: "VND-1022", immediate: true, reason: "Manager Decision" },
  { name: "ColorPro Paint & Refinish", id: "VND-2102", immediate: true, reason: "Poor SLA performance" },
  { name: "Precision Auto Body Works", id: "VND-2101", immediate: true, reason: "Poor SLA performance" },
];

export interface VendorActivity {
  claimId: string;
  vendor: string;
  assignedDate: string;
  status: "Completed" | "Assigned" | "Pending Review" | "In Progress";
}

export const recentActivity: VendorActivity[] = [
  { claimId: "CLM-2025-019", vendor: "AquaShield Plumbing", assignedDate: "16/6/2026", status: "Completed" },
  { claimId: "CLM-2025-012", vendor: "FloodStop Remediation", assignedDate: "16/6/2026", status: "Assigned" },
  { claimId: "CLM-2026-005", vendor: "BrightSpark Electric", assignedDate: "16/6/2026", status: "Completed" },
  { claimId: "CLM-2025-018", vendor: "AquaShield Plumbing", assignedDate: "11/6/2026", status: "Pending Review" },
  { claimId: "CLM-2025-011", vendor: "FloodStop Remediation", assignedDate: "11/6/2026", status: "In Progress" },
  { claimId: "CLM-2025-004", vendor: "BrightSpark Electric", assignedDate: "11/6/2026", status: "Pending Review" },
  { claimId: "CLM-2025-007", vendor: "GreenLeaf Salvage Auto", assignedDate: "10/6/2026", status: "Assigned" },
  { claimId: "CLM-2025-017", vendor: "AquaShield Plumbing", assignedDate: "6/6/2026", status: "Assigned" },
  { claimId: "CLM-2025-010", vendor: "FloodStop Remediation", assignedDate: "6/6/2026", status: "Completed" },
];

export interface CostVariance {
  vendor: string;
  variance: number;
  avgEst: number;
  avgActual: number;
}

export const costVariances: CostVariance[] = [
  { vendor: "SummitView Construction", variance: 23.0, avgEst: 23000, avgActual: 28290 },
  { vendor: "AquaPure Water Services", variance: 21.0, avgEst: 21000, avgActual: 25410 },
  { vendor: "BrightSpark Electric", variance: 19.0, avgEst: 19000, avgActual: 22610 },
  { vendor: "SteelFrame Structural", variance: 17.0, avgEst: 17000, avgActual: 19890 },
  { vendor: "Apex Repairs", variance: -15.0, avgEst: 15000, avgActual: 12750 },
  { vendor: "QuickFix Handyman", variance: 15.0, avgEst: 15000, avgActual: 17250 },
  { vendor: "BlueLine Restoration", variance: -13.0, avgEst: 13000, avgActual: 11310 },
  { vendor: "TrueNorth Roofing", variance: 13.0, avgEst: 13000, avgActual: 14690 },
  { vendor: "StormGuard Services", variance: -11.0, avgEst: 11000, avgActual: 9790 },
  { vendor: "AllStar Maintenance", variance: 11.0, avgEst: 11000, avgActual: 12210 },
];

export interface PerformerGroup {
  label: string;
  sub: string;
  count: number;
  pct: number;
  color: string;
  vendors: { name: string; specialty: string; location: string; vis: number }[];
}

export const highPerformers = [
  { name: "FloodStop Remediation", specialty: "Water", location: "LA", vis: 93 },
  { name: "PrimeCraft Builders", specialty: "Structural", location: "NJ", vis: 90 },
  { name: "SafeHaven Security", specialty: "Security Systems", location: "WA", vis: 87 },
  { name: "GreenTree Landscaping", specialty: "Landscaping", location: "AZ", vis: 84 },
  { name: "SummitView Construction", specialty: "Roofing", location: "UT", vis: 82 },
  { name: "GreenLeaf Salvage Auto", specialty: "Salvage", location: "OR", vis: 78 },
];

export const mediumPerformers = [
  { name: "RoofMasters Inc", specialty: "Roofing", location: "GA", vis: 76 },
  { name: "SecureTech Systems", specialty: "Security Systems", location: "GA", vis: 74 },
  { name: "AquaShield Plumbing", specialty: "Water", location: "OH", vis: 73 },
  { name: "ClearView Glass", specialty: "Glass/Windows", location: "IL", vis: 71 },
  { name: "BrightSpark Electric", specialty: "Electrical", location: "CO", vis: 70 },
  { name: "ProBuild Contractors", specialty: "Structural", location: "TX", vis: 69 },
  { name: "AquaPure Water Services", specialty: "Water", location: "NC", vis: 69 },
  { name: "SteelFrame Structural", specialty: "Structural", location: "PA", vis: 68 },
  { name: "TrueNorth Roofing", specialty: "Roofing", location: "MN", vis: 67 },
  { name: "StormGuard Services", specialty: "Wind", location: "FL", vis: 66 },
  { name: "QuickFix Handyman", specialty: "General", location: "AZ", vis: 65 },
  { name: "AllStar Maintenance", specialty: "General", location: "MI", vis: 64 },
  { name: "BlueLine Restoration", specialty: "Water", location: "CA", vis: 63 },
  { name: "ElectriFix Solutions", specialty: "Electrical", location: "NY", vis: 62 },
];

export const lowPerformers: { name: string; specialty: string; location: string; vis: number }[] = [];

export const slaCompliant = [
  { name: "FloodStop Remediation", specialty: "Water", location: "LA", sla: 98 },
  { name: "PrimeCraft Builders", specialty: "Structural", location: "NJ", sla: 96 },
  { name: "SafeHaven Security", specialty: "Security Systems", location: "WA", sla: 95 },
  { name: "GreenTree Landscaping", specialty: "Landscaping", location: "AZ", sla: 94 },
  { name: "SummitView Construction", specialty: "Roofing", location: "UT", sla: 93 },
  { name: "GreenLeaf Salvage Auto", specialty: "Salvage", location: "OR", sla: 92 },
  { name: "RoofMasters Inc", specialty: "Roofing", location: "GA", sla: 91 },
];

export const slaAtRisk = [
  { name: "AquaShield Plumbing", specialty: "Water", location: "OH", sla: 89 },
  { name: "ClearView Glass", specialty: "Glass/Windows", location: "IL", sla: 88 },
  { name: "BrightSpark Electric", specialty: "Electrical", location: "CO", sla: 86 },
  { name: "ProBuild Contractors", specialty: "Structural", location: "TX", sla: 85 },
  { name: "AquaPure Water Services", specialty: "Water", location: "NC", sla: 83 },
  { name: "SteelFrame Structural", specialty: "Structural", location: "PA", sla: 81 },
  { name: "TrueNorth Roofing", specialty: "Roofing", location: "MN", sla: 79 },
  { name: "StormGuard Services", specialty: "Wind", location: "FL", sla: 78 },
  { name: "QuickFix Handyman", specialty: "General", location: "AZ", sla: 77 },
  { name: "AllStar Maintenance", specialty: "General", location: "MI", sla: 76 },
];

export const slaBreached = [
  { name: "Apex Repairs", specialty: "Fire", location: "NY", sla: 70 },
  { name: "BlueLine Restoration", specialty: "Water", location: "CA", sla: 72 },
  { name: "StormGuard Services", specialty: "Wind", location: "FL", sla: 73 },
];

export interface PendingVendor {
  name: string;
  specialty: string;
  state: string;
  submitted: string;
  license: string;
  expires: string;
  status: "Pending Review" | "Approved" | "Rejected";
}

export const pendingApprovals: PendingVendor[] = [
  { name: "Desert Roof Pros", specialty: "Roofing", state: "AZ", submitted: "2026-03-05", license: "RF-AZ-51820", expires: "2027-06-30", status: "Pending Review" },
  { name: "Lakeside Plumbing Co.", specialty: "Water", state: "MI", submitted: "2026-03-08", license: "WT-MI-52110", expires: "2027-09-12", status: "Pending Review" },
  { name: "Texas Fire Restoration", specialty: "Fire", state: "TX", submitted: "2026-03-10", license: "RF-TX-61834", expires: "2027-05-22", status: "Pending Review" },
  { name: "ProRestore Solutions", specialty: "Water", state: "CA", submitted: "2026-03-10", license: "WD-CA-50291", expires: "2027-08-15", status: "Pending Review" },
];

export const processedApplications: PendingVendor[] = [
  { name: "General Fire Solutions", specialty: "Fire", state: "TX", submitted: "2026-03-31", license: "", expires: "", status: "Approved" },
  { name: "Generali Water Solutions", specialty: "Water", state: "FL", submitted: "2026-03-23", license: "", expires: "", status: "Approved" },
  { name: "Midwest General Contractors", specialty: "General", state: "IL", submitted: "2026-02-18", license: "", expires: "", status: "Rejected" },
  { name: "SecureTech Systems", specialty: "Security Systems", state: "GA", submitted: "2026-02-20", license: "", expires: "", status: "Approved" },
  { name: "Coastal Wind Repairs", specialty: "Wind", state: "NC", submitted: "2026-02-22", license: "", expires: "", status: "Rejected" },
  { name: "TrueNorth Structural", specialty: "Structural", state: "MN", submitted: "2026-02-25", license: "", expires: "", status: "Approved" },
  { name: "Pacific Fire Restoration", specialty: "Fire", state: "WA", submitted: "2026-02-28", license: "", expires: "", status: "Rejected" },
  { name: "Evergreen Landscaping Co.", specialty: "Landscaping", state: "OR", submitted: "2026-03-01", license: "", expires: "", status: "Approved" },
];

export const topVendors = [
  { rank: 1, name: "FloodStop Remediation", specialty: "Water", location: "LA", vis: 93, breakdown: { specialtyMatch: 95, slaCompliance: 98, costAccuracy: 93, customerRating: 96, capacity: 88, reworkRate: 92, subrogation: 90, riskScore: 94, concentration: 89 } },
  { rank: 2, name: "PrimeCraft Builders", specialty: "Structural", location: "NJ", vis: 90, breakdown: { specialtyMatch: 92, slaCompliance: 96, costAccuracy: 90, customerRating: 94, capacity: 85, reworkRate: 89, subrogation: 88, riskScore: 91, concentration: 86 } },
  { rank: 3, name: "SafeHaven Security", specialty: "Security Systems", location: "WA", vis: 87, breakdown: { specialtyMatch: 90, slaCompliance: 95, costAccuracy: 88, customerRating: 92, capacity: 82, reworkRate: 86, subrogation: 84, riskScore: 88, concentration: 83 } },
  { rank: 4, name: "GreenTree Landscaping", specialty: "Landscaping", location: "AZ", vis: 84, breakdown: { specialtyMatch: 88, slaCompliance: 94, costAccuracy: 85, customerRating: 88, capacity: 80, reworkRate: 83, subrogation: 81, riskScore: 84, concentration: 80 } },
  { rank: 5, name: "SummitView Construction", specialty: "Roofing", location: "UT", vis: 82, breakdown: { specialtyMatch: 86, slaCompliance: 93, costAccuracy: 77, customerRating: 90, capacity: 78, reworkRate: 81, subrogation: 79, riskScore: 82, concentration: 78 } },
];

export const visWeights: { key: keyof (typeof topVendors)[0]["breakdown"]; label: string; weight: number }[] = [
  { key: "specialtyMatch", label: "Specialty Match", weight: 0.2 },
  { key: "slaCompliance", label: "SLA Compliance", weight: 0.15 },
  { key: "costAccuracy", label: "Cost Accuracy", weight: 0.15 },
  { key: "customerRating", label: "Customer Rating", weight: 0.125 },
  { key: "capacity", label: "Capacity / Workload", weight: 0.1 },
  { key: "reworkRate", label: "Rework Rate", weight: 0.1 },
  { key: "subrogation", label: "Subrogation Compliance", weight: 0.075 },
  { key: "riskScore", label: "Risk Score", weight: 0.05 },
  { key: "concentration", label: "Concentration Factor", weight: 0.05 },
];

export const bottomPerformers = [
  { name: "Apex Repairs", specialty: "Fire", location: "NY", vis: 60, issues: ["SLA breach (70%)", "High cost variance (-15%)", "High rework rate", "Low rating (2.5/5)"] },
  { name: "FireGuard Systems", specialty: "Fire", location: "NV", vis: 61, issues: ["SLA breach (88%)", "High rework rate"] },
  { name: "BlueLine Restoration", specialty: "Water", location: "CA", vis: 63, issues: ["SLA breach (72%)", "High cost variance (-13%)", "High rework rate", "Low rating (2.8/5)"] },
  { name: "AllStar Maintenance", specialty: "General", location: "MI", vis: 64, issues: ["High cost variance (+11%)", "High rework rate"] },
  { name: "StormGuard Services", specialty: "Wind", location: "FL", vis: 66, issues: ["SLA breach (73%)", "High cost variance (-11%)", "High rework rate"] },
];

export interface Assignment {
  claimId: string;
  vendor: string;
  specialty: string;
  status: "Reassigned" | "Assigned" | "Pending Review" | "Completed" | "In Progress";
  assignedDate: string;
  completionDate: string | null;
  slaStatus: "At Risk" | "Reassigned" | null;
}

export const assignments: Assignment[] = [
  { claimId: "CLM-2025-010", vendor: "StormGuard Services", specialty: "Wind", status: "Reassigned", assignedDate: "2026-03-16", completionDate: null, slaStatus: "Reassigned" },
  { claimId: "CLM-2025-007", vendor: "StormGuard Services", specialty: "Wind", status: "Assigned", assignedDate: "2026-03-01", completionDate: null, slaStatus: "At Risk" },
  { claimId: "CLM-2025-008", vendor: "StormGuard Services", specialty: "Wind", status: "Pending Review", assignedDate: "2026-03-06", completionDate: "2026-03-10", slaStatus: "At Risk" },
  { claimId: "CLM-2025-009", vendor: "StormGuard Services", specialty: "Wind", status: "Completed", assignedDate: "2026-03-11", completionDate: "2026-03-16", slaStatus: null },
  { claimId: "CLM-2025-010", vendor: "ProBuild Contractors", specialty: "Structural", status: "Pending Review", assignedDate: "2026-04-01", completionDate: "2026-04-04", slaStatus: "At Risk" },
  { claimId: "CLM-2025-011", vendor: "ProBuild Contractors", specialty: "Structural", status: "Completed", assignedDate: "2026-04-06", completionDate: "2026-04-10", slaStatus: null },
  { claimId: "CLM-2025-013", vendor: "ClearView Glass", specialty: "Glass/Windows", status: "Completed", assignedDate: "2026-05-01", completionDate: "2026-05-04", slaStatus: null },
  { claimId: "CLM-2025-014", vendor: "ClearView Glass", specialty: "Glass/Windows", status: "In Progress", assignedDate: "2026-05-06", completionDate: null, slaStatus: "At Risk" },
  { claimId: "CLM-2025-015", vendor: "ClearView Glass", specialty: "Glass/Windows", status: "Assigned", assignedDate: "2026-05-11", completionDate: null, slaStatus: "At Risk" },
  { claimId: "CLM-2025-016", vendor: "AquaShield Plumbing", specialty: "Water", status: "In Progress", assignedDate: "2026-06-01", completionDate: null, slaStatus: "At Risk" },
  { claimId: "CLM-2025-017", vendor: "AquaShield Plumbing", specialty: "Water", status: "Assigned", assignedDate: "2026-06-06", completionDate: null, slaStatus: "At Risk" },
  { claimId: "CLM-2025-018", vendor: "AquaShield Plumbing", specialty: "Water", status: "Pending Review", assignedDate: "2026-06-11", completionDate: "2026-06-14", slaStatus: null },
  { claimId: "CLM-2025-019", vendor: "AquaShield Plumbing", specialty: "Water", status: "Completed", assignedDate: "2026-06-16", completionDate: "2026-06-20", slaStatus: null },
  { claimId: "CLM-2025-012", vendor: "FloodStop Remediation", specialty: "Water", status: "Assigned", assignedDate: "2026-06-16", completionDate: null, slaStatus: null },
  { claimId: "CLM-2025-011", vendor: "FloodStop Remediation", specialty: "Water", status: "In Progress", assignedDate: "2026-06-11", completionDate: null, slaStatus: null },
  { claimId: "CLM-2026-005", vendor: "BrightSpark Electric", specialty: "Electrical", status: "Completed", assignedDate: "2026-06-16", completionDate: "2026-06-20", slaStatus: null },
  { claimId: "CLM-2025-004", vendor: "BrightSpark Electric", specialty: "Electrical", status: "Pending Review", assignedDate: "2026-06-11", completionDate: "2026-06-14", slaStatus: null },
  { claimId: "CLM-2025-020", vendor: "GreenTree Landscaping", specialty: "Landscaping", status: "In Progress", assignedDate: "2026-06-18", completionDate: null, slaStatus: null },
  { claimId: "CLM-2025-021", vendor: "TrueNorth Roofing", specialty: "Roofing", status: "Assigned", assignedDate: "2026-06-19", completionDate: null, slaStatus: null },
  { claimId: "CLM-2025-022", vendor: "AllStar Maintenance", specialty: "General", status: "In Progress", assignedDate: "2026-06-20", completionDate: null, slaStatus: null },
];

export const workloadDistribution = [
  { name: "AllStar Maintenance", jobs: 4, level: "Moderate" },
  { name: "StormGuard Services", jobs: 3, level: "Moderate" },
  { name: "ClearView Glass", jobs: 3, level: "Moderate" },
  { name: "AquaShield Plumbing", jobs: 3, level: "Moderate" },
  { name: "GreenTree Landscaping", jobs: 3, level: "Moderate" },
  { name: "FloodStop Remediation", jobs: 3, level: "Moderate" },
  { name: "TrueNorth Roofing", jobs: 3, level: "Moderate" },
  { name: "BrightSpark Electric", jobs: 3, level: "Moderate" },
  { name: "ElectriFix Solutions", jobs: 3, level: "Moderate" },
  { name: "BlueLine Restoration", jobs: 3, level: "Moderate" },
  { name: "SteelFrame Structural", jobs: 2, level: "Moderate" },
  { name: "AquaPure Water Services", jobs: 2, level: "Moderate" },
  { name: "SummitView Construction", jobs: 2, level: "Moderate" },
  { name: "ProBuild Contractors", jobs: 1, level: "Available" },
  { name: "FireGuard Systems", jobs: 1, level: "Available" },
  { name: "QuickFix Handyman", jobs: 1, level: "Available" },
  { name: "Apex Repairs", jobs: 1, level: "Available" },
  { name: "Precision Auto Body Works", jobs: 0, level: "Available" },
  { name: "ColorPro Paint & Refinish", jobs: 0, level: "Available" },
  { name: "MechanixOne Auto Service", jobs: 0, level: "Available" },
  { name: "ClearShield Auto Glass", jobs: 0, level: "Available" },
];

export interface RiskFlag {
  vendorId: string;
  name: string;
  specialty: string;
  risk: "High" | "Medium" | "Low";
  reason: string;
  status: "Active" | "Inactive" | "Under Review";
}

export const riskFlags: RiskFlag[] = [
  { vendorId: "VND-1001", name: "Apex Repairs", specialty: "Fire", risk: "Low", reason: "No anomaly detected", status: "Inactive" },
  { vendorId: "VND-1002", name: "BlueLine Restoration", specialty: "Water", risk: "Medium", reason: "Minor billing inconsistency flagged", status: "Inactive" },
  { vendorId: "VND-1003", name: "StormGuard Services", specialty: "Wind", risk: "High", reason: "Repeated high-cost supplementals", status: "Active" },
  { vendorId: "VND-1004", name: "ProBuild Contractors", specialty: "Structural", risk: "Low", reason: "Multiple claims from same address", status: "Active" },
  { vendorId: "VND-1005", name: "ClearView Glass", specialty: "Glass/Windows", risk: "Medium", reason: "Cost exceeds regional benchmark by 4…", status: "Active" },
  { vendorId: "VND-1006", name: "AquaShield Plumbing", specialty: "Water", risk: "High", reason: "Frequent change orders noted", status: "Active" },
  { vendorId: "VND-1007", name: "RoofMasters Inc", specialty: "Roofing", risk: "Low", reason: "Clean record, no concerns", status: "Active" },
  { vendorId: "VND-1008", name: "ElectriFix Solutions", specialty: "Electrical", risk: "Medium", reason: "New vendor, insufficient history", status: "Inactive" },
  { vendorId: "VND-1009", name: "GreenTree Landscaping", specialty: "Landscaping", risk: "High", reason: "Invoice patterns consistent", status: "Inactive" },
  { vendorId: "VND-1010", name: "FloodStop Remediation", specialty: "Water", risk: "Low", reason: "Clean record, no concerns", status: "Active" },
  { vendorId: "VND-1011", name: "PrimeCraft Builders", specialty: "Structural", risk: "Low", reason: "No anomaly detected", status: "Active" },
  { vendorId: "VND-1013", name: "TrueNorth Roofing", specialty: "Roofing", risk: "Medium", reason: "Cost overrun trend detected", status: "Active" },
  { vendorId: "VND-1014", name: "AllStar Maintenance", specialty: "General", risk: "High", reason: "High rework and cost variance", status: "Active" },
  { vendorId: "VND-1015", name: "QuickFix Handyman", specialty: "General", risk: "Medium", reason: "Suspended license pending review", status: "Inactive" },
  { vendorId: "VND-1016", name: "BrightSpark Electric", specialty: "Electrical", risk: "High", reason: "Suspicious overcharging detected", status: "Active" },
  { vendorId: "VND-1017", name: "SteelFrame Structural", specialty: "Structural", risk: "Medium", reason: "Cost exceeds estimate by 17%", status: "Active" },
  { vendorId: "VND-1018", name: "AquaPure Water Services", specialty: "Water", risk: "High", reason: "Suspicious overcharging detected", status: "Active" },
  { vendorId: "VND-1019", name: "SummitView Construction", specialty: "Roofing", risk: "Medium", reason: "Highest cost variance (23%)", status: "Active" },
  { vendorId: "VND-1020", name: "FireGuard Systems", specialty: "Fire", risk: "Low", reason: "Under license review", status: "Under Review" },
  { vendorId: "VND-1021", name: "GreenLeaf Salvage Auto", specialty: "Salvage", risk: "Low", reason: "Clean record, no concerns", status: "Active" },
  { vendorId: "VND-1022", name: "SecureTech Systems", specialty: "Security Systems", risk: "Low", reason: "No anomaly detected", status: "Inactive" },
];

export const costAnomalies = [
  { vendor: "AllStar Maintenance", pct: 11.0 },
  { vendor: "TrueNorth Roofing", pct: 13.0 },
  { vendor: "QuickFix Handyman", pct: 15.0 },
  { vendor: "SteelFrame Structural", pct: 17.0 },
  { vendor: "BrightSpark Electric", pct: 19.0 },
  { vendor: "AquaPure Water Services", pct: 21.0 },
  { vendor: "SummitView Construction", pct: 23.0 },
];

export const repeatedHighCost = [
  { vendor: "RoofMasters Inc", estimate: 17000 },
  { vendor: "ElectriFix Solutions", estimate: 19000 },
  { vendor: "GreenTree Landscaping", estimate: 21000 },
  { vendor: "SafeHaven Security", estimate: 23000 },
  { vendor: "SteelFrame Structural", estimate: 17000 },
  { vendor: "BrightSpark Electric", estimate: 19000 },
  { vendor: "AquaPure Water Services", estimate: 21000 },
];

export const relationshipPatterns = [
  { vendor: "Apex Repairs", vis: 60 },
  { vendor: "BlueLine Restoration", vis: 63 },
  { vendor: "StormGuard Services", vis: 66 },
  { vendor: "ProBuild Contractors", vis: 69 },
  { vendor: "FireGuard Systems", vis: 61 },
  { vendor: "AllStar Maintenance", vis: 64 },
  { vendor: "TrueNorth Roofing", vis: 67 },
];

export const licenseValidation = [
  { vendor: "GreenTree Landscaping", status: "Inactive" },
  { vendor: "FireGuard Systems", status: "Under Review" },
  { vendor: "QuickFix Handyman", status: "Suspended" },
  { vendor: "ElectriFix Solutions", status: "Inactive" },
  { vendor: "Apex Repairs", status: "Inactive" },
  { vendor: "BlueLine Restoration", status: "Inactive" },
  { vendor: "SecureTech Systems", status: "Inactive" },
];

export const billingPatterns = [
  { vendor: "SummitView Construction", variance: 23.0, avgEst: 23000, avgActual: 28290, suspicious: true },
  { vendor: "AquaPure Water Services", variance: 21.0, avgEst: 21000, avgActual: 25410, suspicious: true },
  { vendor: "BrightSpark Electric", variance: 19.0, avgEst: 19000, avgActual: 22610, suspicious: true },
  { vendor: "SteelFrame Structural", variance: 17.0, avgEst: 17000, avgActual: 19890, suspicious: true },
  { vendor: "QuickFix Handyman", variance: 15.0, avgEst: 15000, avgActual: 17250, suspicious: false },
  { vendor: "TrueNorth Roofing", variance: 13.0, avgEst: 13000, avgActual: 14690, suspicious: false },
  { vendor: "AllStar Maintenance", variance: 11.0, avgEst: 11000, avgActual: 12210, suspicious: false },
  { vendor: "FireGuard Systems", variance: 9.0, avgEst: 9000, avgActual: 9810, suspicious: false },
  { vendor: "FloodStop Remediation", variance: 7.0, avgEst: 7000, avgActual: 7490, suspicious: false },
  { vendor: "PrimeCraft Builders", variance: 5.0, avgEst: 5000, avgActual: 5250, suspicious: false },
  { vendor: "SafeHaven Security", variance: 3.0, avgEst: 23000, avgActual: 23690, suspicious: false },
  { vendor: "GreenTree Landscaping", variance: 1.0, avgEst: 21000, avgActual: 21210, suspicious: false },
  { vendor: "ElectriFix Solutions", variance: -1.0, avgEst: 19000, avgActual: 18810, suspicious: false },
  { vendor: "RoofMasters Inc", variance: -3.0, avgEst: 17000, avgActual: 16490, suspicious: false },
  { vendor: "AquaShield Plumbing", variance: -5.0, avgEst: 15000, avgActual: 14250, suspicious: false },
  { vendor: "ClearView Glass", variance: -7.0, avgEst: 13000, avgActual: 12090, suspicious: false },
];

export const serviceAreaStates = ["NY", "CA", "FL", "TX", "IL", "OH", "GA", "PA", "AZ", "WA", "NJ", "LA", "NV", "MI", "MN", "CO", "NC", "VA", "OR", "UT"];

export const specializations = ["Water", "Fire", "Wind", "Structural", "Roofing", "Electrical", "General", "Landscaping", "Glass/Windows", "Security Systems", "Salvage"];
