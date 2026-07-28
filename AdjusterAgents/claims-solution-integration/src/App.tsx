import { Switch, Route, Router as WouterRouter } from "wouter";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import { TooltipProvider } from "@/components/ui/tooltip";
import { PersonaProvider, usePersona } from "@/lib/persona-context";
import NotFound from "@/pages/not-found";

import { Layout } from "@/components/layout/Layout";
import SmartLossReporting from "@/pages/smart-loss-reporting";
import MyClaims from "@/pages/my-claims";
import FollowMyClaims from "@/pages/follow-my-claims";
import DocumentHub from "@/pages/document-hub";
import PlaceholderDashboard from "@/pages/placeholder-dashboard";
import ComingSoon from "@/pages/coming-soon";
import LossDashboard from "@/pages/adjuster/loss-dashboard";
import LossInvestigation from "@/pages/adjuster/loss-investigation";
import LossAssessment from "@/pages/adjuster/loss-assessment";
import RepairVsReplacement from "@/pages/adjuster/repair-vs-replacement";
import SmartVendorMatch from "@/pages/adjuster/smart-vendor-match";
import VerificationIntelligence from "@/pages/adjuster/verification-intelligence";
import ExpertDispatch from "@/pages/adjuster/expert-dispatch";
import VendorDashboard from "@/pages/vendor/vendor-dashboard";
import VendorDirectory from "@/pages/vendor/vendor-directory";
import VendorOnboarding from "@/pages/vendor/vendor-onboarding";
import VendorPerformance from "@/pages/vendor/vendor-performance";
import VendorAssignmentMonitor from "@/pages/vendor/vendor-assignment-monitor";
import VendorRiskCompliance from "@/pages/vendor/vendor-risk-compliance";
import VendorCostAnalytics from "@/pages/vendor/vendor-cost-analytics";
import VendorSlaTracker from "@/pages/vendor/vendor-sla-tracker";
import FraudDashboard from "@/pages/siu/fraud-dashboard";
import SiuWorkbench from "@/pages/siu/siu-workbench";
import VendorFraudCheck from "@/pages/siu/vendor-fraud-check";

const queryClient = new QueryClient();

function RoleBasedRouter() {
  const { activePersona } = usePersona();

  if (activePersona.id === "policyholder") {
    return (
      <Layout>
        <Switch>
          <Route path="/" component={SmartLossReporting} />
          <Route path="/smart-loss-reporting" component={SmartLossReporting} />
          <Route path="/my-claims" component={MyClaims} />
          <Route path="/follow-my-claims" component={FollowMyClaims} />
          <Route path="/document-hub" component={DocumentHub} />
          <Route component={NotFound} />
        </Switch>
      </Layout>
    );
  }

  if (activePersona.id === "adjuster") {
    return (
      <Layout>
        <Switch>
          <Route path="/" component={LossDashboard} />
          <Route path="/loss-dashboard" component={LossDashboard} />
          <Route path="/loss-investigation" component={LossInvestigation} />
          <Route path="/loss-assessment" component={LossAssessment} />
          <Route path="/repair-vs-replacement" component={RepairVsReplacement} />
          <Route path="/smart-vendor-match" component={SmartVendorMatch} />
          <Route path="/verification-intelligence" component={VerificationIntelligence} />
          <Route path="/expert-dispatch" component={ExpertDispatch} />
          <Route path="/intelligent-fnol" component={SmartLossReporting} />
          <Route path="/parametric-claims">
            <ComingSoon title="Parametric Claims" />
          </Route>
          <Route path="/claims-cockpit">
            <ComingSoon title="Claims Cockpit" />
          </Route>
          <Route path="/follow-my-claims" component={FollowMyClaims} />
          <Route path="/document-hub" component={DocumentHub} />
          <Route component={NotFound} />
        </Switch>
      </Layout>
    );
  }

  if (activePersona.id === "vendor") {
    return (
      <Layout>
        <Switch>
          <Route path="/" component={VendorDashboard} />
          <Route path="/vendor-dashboard" component={VendorDashboard} />
          <Route path="/vendor-directory" component={VendorDirectory} />
          <Route path="/vendor-onboarding" component={VendorOnboarding} />
          <Route path="/vendor-performance" component={VendorPerformance} />
          <Route path="/vendor-assignment-monitor" component={VendorAssignmentMonitor} />
          <Route path="/vendor-risk-compliance" component={VendorRiskCompliance} />
          <Route path="/cost-estimate-analytics" component={VendorCostAnalytics} />
          <Route path="/vendor-sla-tracker" component={VendorSlaTracker} />
          <Route path="/document-hub" component={DocumentHub} />
          <Route component={NotFound} />
        </Switch>
      </Layout>
    );
  }

  if (activePersona.id === "siu") {
    return (
      <Layout>
        <Switch>
          <Route path="/" component={FraudDashboard} />
          <Route path="/fraud-dashboard" component={FraudDashboard} />
          <Route path="/siu-workbench" component={SiuWorkbench} />
          <Route path="/vendor-fraud-check" component={VendorFraudCheck} />
          <Route path="/document-hub" component={DocumentHub} />
          <Route component={NotFound} />
        </Switch>
      </Layout>
    );
  }

  return (
    <Layout>
      <PlaceholderDashboard />
    </Layout>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <PersonaProvider>
          <WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, "")}>
            <RoleBasedRouter />
          </WouterRouter>
          <Toaster />
        </PersonaProvider>
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;
