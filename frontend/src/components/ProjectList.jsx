import { colorClass } from "../theme.js";

// Renders the "Latest Projects" list. Mirrors the server-rendered fallback markup in
// templates/partials/_projects.html so the swap on mount is visually seamless.
export default function ProjectList({ projects = [], viewMoreUrl }) {
  const cls = colorClass();
  return (
    <>
      <div className="row">
        <div className="col text-center">
          <ul className={`list-unstyled text-left d-inline-block ${cls}`}>
            {projects.map((p) => (
              <li key={p.url}>
                <a
                  href={p.url}
                  target="_blank"
                  rel="noreferrer"
                  className={cls}
                  onClick={() => window.trackProjectView?.(p.name)}
                >
                  {p.label}
                </a>
              </li>
            ))}
          </ul>
        </div>
      </div>
      {viewMoreUrl && (
        <div className="row">
          <div className="col text-center">
            <a href={viewMoreUrl} target="_blank" rel="noreferrer" className={cls}>
              View more projects &raquo;
            </a>
          </div>
        </div>
      )}
    </>
  );
}
