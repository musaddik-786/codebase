import { useLocation, Link } from "wouter";
import { useState } from "react";
import { cn } from "@/lib/utils";
import { usePersona } from "@/lib/persona-context";
import {
  FileText,
  List,
  Search,
  FolderOpen,
  LayoutDashboard,
  Settings,
  ClipboardList,
  ChevronDown,
  Gauge,
  SearchCheck,
  Calculator,
  Scale,
  Handshake,
  ShieldCheck,
  Send,
  Zap,
  Monitor,
  BookOpen,
  UserPlus,
  BarChart3,
  Activity,
  ShieldAlert,
  DollarSign,
  Timer,
} from "lucide-react";
import logo from "@assets/image_1782114370781.png";

interface NavItem {
  name: string;
  path: string;
  icon: React.ComponentType<{ className?: string }>;
}

const lossAdjustmentNav: NavItem[] = [
  { name: "Loss Dashboard", path: "/loss-dashboard", icon: Gauge },
  { name: "Loss Adjustment Investigation", path: "/loss-investigation", icon: SearchCheck },
  { name: "Loss Assessment", path: "/loss-assessment", icon: Calculator },
  { name: "Repair vs Replacement", path: "/repair-vs-replacement", icon: Scale },
  { name: "Smart Vendor Match", path: "/smart-vendor-match", icon: Handshake },
  { name: "Verification Intelligence", path: "/verification-intelligence", icon: ShieldCheck },
  { name: "Expert Dispatch", path: "/expert-dispatch", icon: Send },
];

const vendorNav: NavItem[] = [
  { name: "Vendor Dashboard", path: "/vendor-dashboard", icon: LayoutDashboard },
  { name: "Vendor Directory", path: "/vendor-directory", icon: BookOpen },
  { name: "Vendor Onboarding", path: "/vendor-onboarding", icon: UserPlus },
  { name: "Vendor Performance", path: "/vendor-performance", icon: BarChart3 },
  { name: "Vendor Assignment Mon...", path: "/vendor-assignment-monitor", icon: Activity },
  { name: "Vendor Risk & Compliance", path: "/vendor-risk-compliance", icon: ShieldAlert },
  { name: "Cost & Estimate Analytics", path: "/cost-estimate-analytics", icon: DollarSign },
  { name: "Vendor SLA Tracker", path: "/vendor-sla-tracker", icon: Timer },
  { name: "Document Hub", path: "/document-hub", icon: FolderOpen },
];

const siuNav: NavItem[] = [
  { name: "Fraud Dashboard", path: "/fraud-dashboard", icon: LayoutDashboard },
  { name: "SIU Investigation Workb...", path: "/siu-workbench", icon: SearchCheck },
  { name: "Vendor Fraud Check", path: "/vendor-fraud-check", icon: ShieldAlert },
  { name: "Document Hub", path: "/document-hub", icon: FolderOpen },
];

function NavLink({ item, isActive, indent }: { item: NavItem; isActive: boolean; indent?: boolean }) {
  const Icon = item.icon;
  return (
    <Link href={item.path}>
      <div
        className={cn(
          "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all cursor-pointer",
          indent && "ml-3",
          isActive
            ? "bg-[#2563eb] text-white shadow-md shadow-blue-500/20"
            : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
        )}
      >
        <Icon className={cn("h-[18px] w-[18px] flex-shrink-0", isActive ? "text-white" : "text-gray-400")} />
        <span className="truncate">{item.name}</span>
      </div>
    </Link>
  );
}

export function Sidebar() {
  const [location] = useLocation();
  const { activePersona } = usePersona();
  const [lossOpen, setLossOpen] = useState(true);

  const policyholderNav: NavItem[] = [
    { name: "My Claims", path: "/my-claims", icon: List },
    { name: "Smart Loss Reporting", path: "/smart-loss-reporting", icon: FileText },
    { name: "Follow My Claims", path: "/follow-my-claims", icon: Search },
    { name: "Document Hub", path: "/document-hub", icon: FolderOpen },
  ];

  const defaultNav: NavItem[] = [
    { name: "Dashboard", path: "/", icon: LayoutDashboard },
    { name: "Settings", path: "/settings", icon: Settings },
  ];

  const lossGroupActive = lossAdjustmentNav.some(
    (i) => location === i.path || (location === "/" && i.path === "/loss-dashboard")
  );

  return (
    <div className="w-[256px] h-screen border-r bg-white flex flex-col flex-shrink-0">
      <div className="p-6 flex flex-col gap-3">
        <img src={logo} alt="Hexaware Logo" className="h-4 object-contain self-start" />
        <div className="leading-tight">
          <div className="font-extrabold text-[#0f172a] text-[15px] tracking-tight">Hexaware Agentic</div>
          <div className="font-bold text-[#0f172a] text-[15px] tracking-tight">Claims Solution</div>
        </div>
      </div>

      <div className="flex-1 px-4 py-2 space-y-1 overflow-y-auto">
        {activePersona.id === "policyholder" &&
          policyholderNav.map((item) => (
            <NavLink
              key={item.path}
              item={item}
              isActive={
                location === item.path ||
                (location === "/" && item.path === "/smart-loss-reporting")
              }
            />
          ))}

        {activePersona.id === "adjuster" && (
          <>
            <NavLink
              item={{ name: "Intelligent FNOL", path: "/intelligent-fnol", icon: FileText }}
              isActive={location === "/intelligent-fnol"}
            />

            <button
              type="button"
              onClick={() => setLossOpen((o) => !o)}
              className={cn(
                "w-full flex items-center justify-between gap-2 px-3 py-2.5 rounded-lg text-sm font-medium transition-all cursor-pointer",
                lossGroupActive && !lossOpen
                  ? "bg-blue-50 text-blue-700"
                  : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
              )}
            >
              <span className="flex items-center gap-3">
                <ClipboardList className="h-[18px] w-[18px] text-gray-400" />
                Loss Adjustment
              </span>
              <ChevronDown
                className={cn("h-4 w-4 text-gray-400 transition-transform", lossOpen && "rotate-180")}
              />
            </button>
            {lossOpen && (
              <div className="space-y-1 border-l border-gray-100 ml-4 pl-1">
                {lossAdjustmentNav.map((item) => (
                  <NavLink
                    key={item.path}
                    item={item}
                    isActive={
                      location === item.path ||
                      (location === "/" && item.path === "/loss-dashboard")
                    }
                    indent
                  />
                ))}
              </div>
            )}

            <NavLink
              item={{ name: "Parametric Claims", path: "/parametric-claims", icon: Zap }}
              isActive={location === "/parametric-claims"}
            />
            <NavLink
              item={{ name: "Claims Cockpit", path: "/claims-cockpit", icon: Monitor }}
              isActive={location === "/claims-cockpit"}
            />
            <NavLink
              item={{ name: "Follow My Claims", path: "/follow-my-claims", icon: Search }}
              isActive={location === "/follow-my-claims"}
            />
            <NavLink
              item={{ name: "Document Hub", path: "/document-hub", icon: FolderOpen }}
              isActive={location === "/document-hub"}
            />
          </>
        )}

        {activePersona.id === "vendor" &&
          vendorNav.map((item) => (
            <NavLink
              key={item.path}
              item={item}
              isActive={
                location === item.path ||
                (location === "/" && item.path === "/vendor-dashboard")
              }
            />
          ))}

        {activePersona.id === "siu" &&
          siuNav.map((item) => (
            <NavLink
              key={item.path}
              item={item}
              isActive={
                location === item.path ||
                (location === "/" && item.path === "/fraud-dashboard")
              }
            />
          ))}

        {activePersona.id !== "policyholder" &&
          activePersona.id !== "adjuster" &&
          activePersona.id !== "vendor" &&
          activePersona.id !== "siu" &&
          defaultNav.map((item) => (
            <NavLink key={item.path} item={item} isActive={location === item.path} />
          ))}
      </div>

      <div className="p-4 border-t border-gray-100">
        <div className="text-xs text-gray-400 text-center">v1.0.0 (Demo)</div>
      </div>
    </div>
  );
}
