import "./BuildItself.css";

// Concept prototype: "It builds itself." On load the page constructs — a faint grid
// wipes in, a hairline draws, the type sets itself — then settles dead still into a
// clean minimal hero. All motion is CSS (auto-runs on mount); prefers-reduced-motion
// gets the finished state with no animation.
const NAME = "Atilano Garcia";

export default function BuildItself() {
  return (
    <main className="bi">
      <div className="bi-grid" aria-hidden="true" />
      <div className="bi-stage">
        <p className="bi-eyebrow">Software Engineer — Austin, TX</p>
        {/* Real SVG <text> (selectable, accessible) — each glyph's outline draws via
            stroke-dashoffset, then fills. Stays responsive: the SVG scales by viewBox. */}
        <svg
          className="bi-name"
          viewBox="0 0 1200 210"
          role="img"
          aria-label={NAME}
        >
          <text x="600" y="155" textAnchor="middle" className="bi-name-text">
            {NAME.split("").map((ch, i) => (
              <tspan key={i} className="bi-glyph" style={{ "--d": `${1 + i * 0.06}s` }}>
                {ch === " " ? " " : ch}
              </tspan>
            ))}
          </text>
        </svg>
        <div className="bi-rule" aria-hidden="true" />
        <p className="bi-tag">
          I design and build systems that move data at scale — and the occasional
          experiment on the side.
        </p>
        <span className="bi-tick" aria-hidden="true" />
      </div>
      <span className="bi-coord bi-coord--tl">grid · 48</span>
      <span className="bi-coord bi-coord--br">build 001</span>
    </main>
  );
}
