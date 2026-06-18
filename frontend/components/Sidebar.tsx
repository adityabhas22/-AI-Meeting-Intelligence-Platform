"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/cn";

const LINKS = [
  { href: "/", label: "Meetings", match: (p: string) => p === "/" || p.startsWith("/meetings") },
  { href: "/record", label: "Record", match: (p: string) => p.startsWith("/record") },
  { href: "/search", label: "Search", match: (p: string) => p.startsWith("/search") },
  { href: "/analytics", label: "Analytics", match: (p: string) => p.startsWith("/analytics") },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-line bg-surface px-5 py-7">
      <Link href="/" className="mb-10 block">
        <span className="label">Meeting Intelligence</span>
        <span className="mt-1 block font-display text-2xl leading-none text-ink">The Record</span>
      </Link>

      <nav className="flex flex-col gap-0.5">
        {LINKS.map((link) => {
          const active = link.match(pathname);
          return (
            <Link
              key={link.href}
              href={link.href}
              className={cn(
                "group flex items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
                active ? "bg-accent-soft text-accent-ink" : "text-muted hover:bg-ink/5 hover:text-ink",
              )}
            >
              <span
                className={cn(
                  "h-4 w-px transition-colors",
                  active ? "bg-accent" : "bg-line group-hover:bg-faint",
                )}
              />
              <span className={active ? "font-medium" : ""}>{link.label}</span>
            </Link>
          );
        })}
      </nav>

      <p className="mt-auto font-mono text-[11px] leading-relaxed text-faint">
        From recording
        <br />
        to decisions.
      </p>
    </aside>
  );
}
