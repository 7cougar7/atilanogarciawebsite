import "./BuildItself.css";

// Concept prototype: "It builds itself." On load the page constructs — a faint grid
// wipes in, a hairline draws, the type sets itself — then settles dead still into a
// clean minimal hero. All motion is CSS (auto-runs on mount); prefers-reduced-motion
// gets the finished state with no animation.
const NAME = "Atilano Garcia";

// Ease-out reveal: the first letters draw slowly and far apart so the eye can
// follow each stroke, then the gaps collapse and each draw quickens — the name
// "accelerates" into place. easeOut(t) front-loads the delay so increments
// between letters shrink toward the end.
const START = 0.9; // s — after the grid/eyebrow settle
const DUR_FIRST = 0.95; // s — first letter's draw
const DUR_LAST = 0.82; // s — last letter's draw (stays appreciable, no whip)
const GAP_FIRST = 0.3; // s — gap between the first letters (slow, sequential)
const GAP_LAST = 0.13; // s — gap between the last letters (overlapping cascade, floored)

// Per-letter delay + draw duration. Acceleration comes from the gaps shrinking
// (GAP_FIRST -> GAP_LAST) so the next letter begins as the previous is finishing;
// the gap floors at GAP_LAST so the end cascades smoothly instead of popping. The
// draw duration barely changes, keeping every letter — including the last — watchable.
function letterTimings(n) {
  const out = [];
  let delay = START;
  for (let i = 0; i < n; i++) {
    const t = n > 1 ? i / (n - 1) : 0;
    if (i > 0) {
      const gt = (i - 1) / Math.max(1, n - 2); // 0..1 across the gaps
      delay += GAP_FIRST + (GAP_LAST - GAP_FIRST) * gt;
    }
    out.push({ delay, dur: DUR_FIRST + (DUR_LAST - DUR_FIRST) * t });
  }
  return out;
}

export default function BuildItself() {
  const chars = NAME.split("");
  const n = chars.length;
  const times = letterTimings(n);
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
            {chars.map((ch, i) => {
              const { delay, dur } = times[i];
              return (
                <tspan
                  key={i}
                  className="bi-glyph"
                  style={{ "--d": `${delay.toFixed(3)}s`, "--dur": `${dur.toFixed(3)}s` }}
                >
                  {ch === " " ? " " : ch}
                </tspan>
              );
            })}
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
