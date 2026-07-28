import { Routes, Route } from "react-router-dom";
import { Layout } from "@/components/Layout";
import { Home } from "@/pages/Home";
import { Policyholder } from "@/pages/Policyholder";
import { PolicyholderOrchestrator } from "@/pages/PolicyholderOrchestrator";
import { Adjuster } from "@/pages/Adjuster";
import { AdjusterOrchestrator } from "@/pages/AdjusterOrchestrator";
import { SIU } from "@/pages/SIU";
import { VendorManager } from "@/pages/VendorManager";
import { Orchestrator } from "@/pages/Orchestrator";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/policyholder" element={<Policyholder />} />
        <Route path="/policyholder-orchestrator" element={<PolicyholderOrchestrator />} />
        <Route path="/adjuster" element={<Adjuster />} />
        <Route path="/adjuster-orchestrator" element={<AdjusterOrchestrator />} />
        <Route path="/siu" element={<SIU />} />
        <Route path="/vendor-manager" element={<VendorManager />} />
        <Route path="/orchestrator" element={<Orchestrator />} />
      </Route>
    </Routes>
  );
}
