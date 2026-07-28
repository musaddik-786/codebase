import { cn } from "@/lib/utils";

interface GradientBannerProps {
  title: string;
  subtitle?: string;
  badge?: string;
  icon?: React.ReactNode;
  rightContent?: React.ReactNode;
  children?: React.ReactNode;
  className?: string;
}

export function GradientBanner({
  title,
  subtitle,
  badge,
  icon,
  rightContent,
  children,
  className,
}: GradientBannerProps) {
  return (
    <div
      className={cn(
        "rounded-2xl bg-gradient-to-r from-[#1e1b4b] to-[#5b21b6] p-6 shadow-lg text-white mb-6",
        className
      )}
    >
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div className="flex items-center gap-3">
          {icon && (
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/10 backdrop-blur-sm">
              {icon}
            </div>
          )}
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
              {badge && (
                <span className="rounded-full bg-white/20 px-2.5 py-0.5 text-xs font-medium text-white/90 backdrop-blur-sm border border-white/10">
                  {badge}
                </span>
              )}
            </div>
            {subtitle && <p className="mt-1 text-white/70 text-sm">{subtitle}</p>}
          </div>
        </div>
        {rightContent && <div>{rightContent}</div>}
      </div>
      {children && <div className="mt-6">{children}</div>}
    </div>
  );
}
