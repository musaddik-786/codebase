import { Link } from "react-router-dom";
import { User, ShieldCheck, Search, HardHat, Network, Zap } from "lucide-react";

const cards = [
  {
    to: "/policyholder",
    icon: User,
    color: "policyholder",
    title: "Policyholder",
    desc: "Digital Self-Service",
    detail: "File new claims, track status, submit documents, verify coverage, and get notifications.",
    agentCount: 9,
  },
  {
    to: "/adjuster",
    icon: ShieldCheck,
    color: "adjuster",
    title: "Claims Adjuster",
    desc: "Claim Intake to Settlement",
    detail: "Triage, investigate, assess loss, check reserves, and drive claims to settlement.",
    agentCount: 15,
  },
  {
    to: "/siu",
    icon: Search,
    color: "siu",
    title: "SIU Investigator",
    desc: "Fraud Detection & Investigation",
    detail: "Score fraud risk, analyze behavioral patterns, detect fraud rings, and resolve cases.",
    agentCount: 12,
  },
  {
    to: "/vendor-manager",
    icon: HardHat,
    color: "vendor",
    title: "Vendor Manager",
    desc: "Vendor & Field Operations",
    detail: "Onboard, match, dispatch, and manage vendor performance, SLA compliance, and capacity.",
    agentCount: 10,
  },
  {
    to: "/orchestrator",
    icon: Network,
    color: "orchestrator",
    title: "Claims Orchestration / Brain Agent",
    desc: "End-to-end lifecycle with HITL",
    detail: "Drives the full claim lifecycle across all agents and manages human-in-the-loop approvals.",
    agentCount: 1,
  },
];

export function Home() {
  const totalAgents = cards.reduce((sum, c) => sum + c.agentCount, 0);

  return (
    <div>
      <h1 className="text-3xl mb-2">Jarvis Claims Agent Console</h1>
      <p className="text-muted-foreground mb-2 max-w-2xl">
        A unified interface for interacting with the Jarvis LangGraph claims agents —
        Policyholder self-service, Adjuster workflows, SIU fraud investigation, Vendor
        management, and the Orchestrator brain agent with HITL approvals.
      </p>

      {/* Status strip */}
      <div className="flex items-center gap-2 mb-8 p-2.5 rounded-lg border bg-muted/30 w-fit text-sm">
        <Zap className="h-4 w-4 text-green-600" />
        <span>
          <strong>{totalAgents} agents</strong> fully implemented across 4 personas + Orchestrator.
          All backed by Azure OpenAI gpt-5.1 and Azure PostgreSQL.
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {cards.map(({ to, icon: Icon, color, title, desc, detail, agentCount }) => (
          <Link
            key={to}
            to={to}
            className="border rounded-xl p-5 bg-card hover:shadow-md transition-shadow flex flex-col gap-2"
          >
            <div className="flex items-start justify-between">
              <div
                className="h-10 w-10 rounded-lg flex items-center justify-center text-white"
                style={{ backgroundColor: `hsl(var(--${color}))` }}
              >
                <Icon className="h-5 w-5" />
              </div>
              <span
                className="text-[11px] px-2 py-0.5 rounded-full border font-medium"
                style={{
                  color: `hsl(var(--${color}))`,
                  borderColor: `hsl(var(--${color}) / 0.35)`,
                  backgroundColor: `hsl(var(--${color}) / 0.08)`,
                }}
              >
                {agentCount} agent{agentCount !== 1 ? "s" : ""}
              </span>
            </div>
            <h2 className="text-lg">{title}</h2>
            <p className="text-sm font-medium" style={{ color: `hsl(var(--${color}))` }}>
              {desc}
            </p>
            <p className="text-sm text-muted-foreground">{detail}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
