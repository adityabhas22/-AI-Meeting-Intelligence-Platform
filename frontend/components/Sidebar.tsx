"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "Meetings", match: (p: string) => p === "/" || p.startsWith("/meetings") },
  { href: "/search", label: "Search", match: (p: string) => p.startsWith("/search") },
  { href: "/analytics", label: "Analytics", match: (p: string) => p.startsWith("/analytics") },
];

const ICONS: Record<string, React.ReactNode> = {
  "/": (
    <path d="M4 6h16M4 12h16M4 18h10" strokeWidth="2" strokeLinecap="round" />
  ),
  "/search": (
    <>
      <circle cx="11" cy="11" r="7" strokeWidth="2" />
      <path d="M21 21l-4.3-4.3" strokeWidth="2" strokeLinecap="round" />
    </>
  ),
  "/analytics": (
    <path d="M4 19V5M4 19h16M9 19v-6M14 19V9M19 19v-9" strokeWidth="2" strokeLinecap="round" />
  ),
};

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-zinc-200 bg-white px-3 py-6">
      <Link href="/" className="mb-8 flex items-center gap-2.5 px-2">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-sm font-bold text-white">
          MI
        </span>
        <span className="text-[15px] font-semibold tracking-tight text-zinc-900">
          Meeting Intel
        </span>
      </Link>
      <nav className="flex flex-col gap-1">
        {LINKS.map((link) => {
          const active = link.match(pathname);
          return (
            <Link
              key={link.href}
              href={link.href}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                active
                  ? "bg-indigo-50 text-indigo-700"
                  : "text-zinc-600 hover:bg-zinc-100 hover:text-zinc-900"
              }`}
            >
              <svg
                className="h-[18px] w-[18px]"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
              >
                {ICONS[link.href]}
              </svg>
              {link.label}
            </Link>
          );
        })}
      </nav>
      <p className="mt-auto px-3 text-xs text-zinc-400">
        From recording to decisions.
      </p>
    </aside>
  );
}
