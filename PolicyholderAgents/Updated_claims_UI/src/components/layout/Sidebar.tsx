import { useLocation, Link } from "wouter";
import { cn } from "@/lib/utils";
import { usePersona } from "@/lib/persona-context";
import { 
  FileText, 
  List, 
  Search, 
  FolderOpen,
  LayoutDashboard,
  Settings
} from "lucide-react";
import logo from "@assets/image_1782114370781.png";

export function Sidebar() {
  const [location] = useLocation();
  const { activePersona } = usePersona();

  const policyholderNav = [
    { name: "Smart Loss Reporting", path: "/smart-loss-reporting", icon: FileText },
    { name: "My Claims", path: "/my-claims", icon: List },
    { name: "Follow My Claims", path: "/follow-my-claims", icon: Search },
    { name: "Document Hub", path: "/document-hub", icon: FolderOpen },
  ];

  const defaultNav = [
    { name: "Dashboard", path: "/", icon: LayoutDashboard },
    { name: "Settings", path: "/settings", icon: Settings },
  ];

  const navItems = activePersona.id === "policyholder" ? policyholderNav : defaultNav;

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
        {navItems.map((item) => {
          const isActive = location === item.path || (location === "/" && item.path === "/smart-loss-reporting" && activePersona.id === "policyholder");
          const Icon = item.icon;
          
          return (
            <Link key={item.path} href={item.path}>
              <div
                className={cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all cursor-pointer",
                  isActive
                    ? "bg-[#2563eb] text-white shadow-md shadow-blue-500/20"
                    : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
                )}
              >
                <Icon className={cn("h-[18px] w-[18px]", isActive ? "text-white" : "text-gray-400")} />
                {item.name}
              </div>
            </Link>
          );
        })}
      </div>
      
      <div className="p-4 border-t border-gray-100">
        <div className="text-xs text-gray-400 text-center">v1.0.0 (Demo)</div>
      </div>
    </div>
  );
}
