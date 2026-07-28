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
