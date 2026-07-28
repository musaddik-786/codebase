import { Bell, ChevronDown, User, Briefcase, Truck, ShieldAlert } from "lucide-react";
import { useLocation } from "wouter";
import { usePersona } from "@/lib/persona-context";
import { personas, PersonaId } from "@/lib/personas";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const iconMap = {
  user: User,
  briefcase: Briefcase,
  truck: Truck,
  "shield-alert": ShieldAlert,
};

export function Header() {
  const { activePersona, setActivePersona } = usePersona();
  const [, navigate] = useLocation();

  const handleSwitch = (id: PersonaId) => {
    setActivePersona(id);
    navigate("/");
  };

  return (
    <header className="h-16 border-b bg-white flex items-center justify-between px-6 flex-shrink-0">
      <div className="flex-1">
        <h1 className="text-[17px] font-bold text-[#0f172a]">{activePersona.portalTitle}</h1>
      </div>

      <div className="flex items-center gap-4">
        <button className="relative text-gray-400 hover:text-gray-600 transition-colors">
          <Bell className="h-5 w-5" />
          <span className="absolute top-0 right-0 h-2 w-2 rounded-full bg-red-500 border border-white"></span>
        </button>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="flex items-center gap-2 border rounded-full px-3 py-1.5 hover:bg-gray-50 transition-colors bg-white shadow-sm">
              <div className="h-6 w-6 rounded-full bg-gray-100 flex items-center justify-center text-gray-600">
                <User className="h-4 w-4" />
              </div>
              <span className="text-sm font-medium text-gray-700">{activePersona.name}</span>
              <ChevronDown className="h-4 w-4 text-gray-400" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-64 p-2">
            <div className="px-2 py-1.5 text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">
              Switch Role
            </div>
            {Object.values(personas).map((persona) => {
              const Icon = iconMap[persona.icon as keyof typeof iconMap];
              const isActive = activePersona.id === persona.id;
              
              return (
                <DropdownMenuItem
                  key={persona.id}
                  onClick={() => handleSwitch(persona.id as PersonaId)}
                  className="flex items-center justify-between px-2 py-2 rounded-md cursor-pointer data-[highlighted]:bg-gray-100"
                >
                  <div className="flex items-center gap-3">
                    <div className="h-8 w-8 rounded-full bg-gray-100 flex items-center justify-center text-gray-500">
                      <Icon className="h-4 w-4" />
                    </div>
                    <div className="flex flex-col">
                      <span className="text-sm font-medium text-gray-900">{persona.name}</span>
                      <span className="text-xs text-gray-500">{persona.role}</span>
                    </div>
                  </div>
                  {isActive && (
                    <span className="bg-emerald-100 text-emerald-700 text-[10px] font-bold px-2 py-0.5 rounded-full">
                      Active
                    </span>
                  )}
                </DropdownMenuItem>
              );
            })}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
