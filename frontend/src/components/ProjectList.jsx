// Renders the "Latest Projects" list. Mirrors the server-rendered fallback markup in
// templates/partials/_projects.html. The `dark-color` class is theme-driven via CSS
// variables (color_layout.css), so it renders correctly in both themes with no JS.
export default function ProjectList({ projects = [], viewMoreUrl }) {
  return (
    <>
      <div className="row">
        <div className="col text-center">
          <ul className="list-unstyled text-left d-inline-block dark-color">
            {projects.map((p) => (
              <li key={p.url}>
                <a
                  href={p.url}
                  target="_blank"
                  rel="noreferrer"
                  className="dark-color"
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
            <a
              href={viewMoreUrl}
              target="_blank"
              rel="noreferrer"
              className="dark-color"
            >
              View more projects &raquo;
            </a>
          </div>
        </div>
      )}
    </>
  );
}
