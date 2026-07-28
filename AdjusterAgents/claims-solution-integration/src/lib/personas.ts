export type PersonaId = "policyholder" | "adjuster" | "vendor" | "siu";

export interface Persona {
  id: PersonaId;
  name: string;
  role: string;
  portalTitle: string;
  icon: string;
}

export const personas: Record<PersonaId, Persona> = {
  policyholder: {
    id: "policyholder",
    name: "John Davis",
    role: "Policyholder",
    portalTitle: "Policyholder Portal",
    icon: "user",
  },
  adjuster: {
    id: "adjuster",
    name: "Michael Chen",
    role: "Adjuster",
    portalTitle: "Adjuster Portal",
    icon: "briefcase",
  },
  vendor: {
    id: "vendor",
    name: "Rachel Martinez",
    role: "Vendor Manager",
    portalTitle: "Vendor Manager Portal",
    icon: "truck",
  },
  siu: {
    id: "siu",
    name: "David Wilson",
    role: "SIU / Fraud",
    portalTitle: "SIU / Fraud Portal",
    icon: "shield-alert",
  },
};
