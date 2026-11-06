import { BrandIcon } from "@/components/ui/BrandIcon";

const LINKS = [
  { href: "#analyse", label: "Analyse" },
  { href: "#containment", label: "Containment" },
  { href: "#break-it", label: "Break it" },
];

export const REPO_URL = "https://github.com/chitrakumarsai/prereg-agent";

export function Logo() {
  return (
    <span className="inline-flex items-center gap-2.5 font-medium tracking-tight">
      <svg width="22" height="22" viewBox="0 0 22 22" aria-hidden="true">
        <rect x="1" y="1" width="20" height="20" rx="2" fill="none" stroke="currentColor" strokeWidth="1.5" />
        <path d="M6 8h10M6 11.5h6M6 15h8" stroke="currentColor" strokeWidth="1.5" />
        <circle cx="16.5" cy="15" r="2" fill="var(--p-accent)" />
      </svg>
      Prereg
    </span>
  );
}

export function Nav() {
  return (
    <header className="sticky top-0 z-40 border-b border-line/70 bg-bg/85 backdrop-blur-md">
      <nav aria-label="Main navigation" className="wrap flex h-16 items-center justify-between">
        <a href="#top" className="text-ink" aria-label="Prereg home">
          <Logo />
        </a>
        <ul className="hidden items-center gap-8 text-sm text-muted md:flex">
          {LINKS.map((l) => (
            <li key={l.href}>
              <a className="link-draw py-1 hover:text-ink" href={l.href}>
                {l.label}
              </a>
            </li>
          ))}
        </ul>
        <div className="flex items-center gap-3">
          <a
            href={REPO_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="hidden h-9 w-9 items-center justify-center rounded-md text-ink transition-colors hover:bg-surface sm:inline-flex"
            aria-label="Source code on GitHub"
          >
            <BrandIcon name="github" size={18} mono />
          </a>
          <a href="#analyse" className="btn btn-primary h-9 px-4 text-sm">
            Analyse a CSV
          </a>
        </div>
      </nav>
    </header>
  );
}
