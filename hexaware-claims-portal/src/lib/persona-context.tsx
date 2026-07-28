import { createContext, useContext, useState, ReactNode } from "react";
import { Persona, personas, PersonaId } from "./personas";

interface PersonaContextType {
  activePersona: Persona;
  setActivePersona: (id: PersonaId) => void;
}

const PersonaContext = createContext<PersonaContextType | undefined>(undefined);

export function PersonaProvider({ children }: { children: ReactNode }) {
  const [activePersonaId, setActivePersonaId] = useState<PersonaId>("policyholder");

  return (
    <PersonaContext.Provider
      value={{
        activePersona: personas[activePersonaId],
        setActivePersona: setActivePersonaId,
      }}
    >
      {children}
    </PersonaContext.Provider>
  );
}

export function usePersona() {
  const context = useContext(PersonaContext);
  if (context === undefined) {
    throw new Error("usePersona must be used within a PersonaProvider");
  }
  return context;
}
