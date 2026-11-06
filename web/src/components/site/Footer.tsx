import { Logo, REPO_URL } from "./Nav";

export function Footer() {
  return (
    <footer className="border-t border-line py-12">
      <div className="wrap flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <Logo />
          <p className="mt-2 max-w-[48ch] text-sm text-muted">
            A pre-registering, sandboxed data analyst. Built for the Vultr Agent Rush hackathon, Blast Radius Zero track.
          </p>
        </div>
        <ul className="flex flex-wrap gap-x-6 gap-y-2 text-sm">
          <li>
            <a className="link-draw" href={REPO_URL} target="_blank" rel="noopener noreferrer">
              Source on GitHub
            </a>
          </li>
          <li>
            <a className="link-draw" href="/api/docs">
              API reference
            </a>
          </li>
          <li className="text-muted">MIT licence</li>
        </ul>
      </div>
    </footer>
  );
}
