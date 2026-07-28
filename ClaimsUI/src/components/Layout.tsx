import { NavLink, Outlet } from "react-router-dom";
import { User, ShieldCheck, Search, HardHat, Network, GitMerge } from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { to: "/policyholder", label: "Policyholder", icon: User, color: "policyholder" },
  { to: "/policyholder-orchestrator", label: "PH Orchestrator", icon: GitMerge, color: "policyholder" },
  { to: "/adjuster", label: "Adjuster", icon: ShieldCheck, color: "adjuster" },
  { to: "/adjuster-orchestrator", label: "Adj Orchestrator", icon: GitMerge, color: "adjuster" },
  { to: "/siu", label: "SIU", icon: Search, color: "siu" },
  { to: "/vendor-manager", label: "Vendor Manager", icon: HardHat, color: "vendor" },
  { to: "/orchestrator", label: "Orchestrator / HITL", icon: Network, color: "orchestrator" },
];

export function Layout() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b bg-card sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-6">
          <NavLink to="/" className="font-display font-bold text-lg whitespace-nowrap">
            Jarvis Claims Console
          </NavLink>
          <nav className="flex gap-1 flex-wrap">
            {navItems.map(({ to, label, icon: Icon, color }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors border",
                    isActive
                      ? `bg-[hsl(var(--${color}))] text-white border-transparent`
                      : "border-transparent text-muted-foreground hover:bg-muted"
                  )
                }
              >
                <Icon className="h-4 w-4" />
                {label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main className="flex-1 max-w-7xl mx-auto w-full px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
