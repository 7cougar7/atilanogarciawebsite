import "./BuildItself.css";

// Concept prototype: "It builds itself." On load the page constructs — a faint grid
// wipes in, a hairline draws, the type sets itself — then settles dead still into a
// clean minimal hero. All motion is CSS (auto-runs on mount); prefers-reduced-motion
// gets the finished state with no animation.
export default function BuildItself() {
  return (
    <main className="bi">
      <div className="bi-grid" aria-hidden="true" />
      <div className="bi-stage">
        <p className="bi-eyebrow">Software Engineer — Austin, TX</p>
        <h1 className="bi-name">Atilano&nbsp;Garcia</h1>
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
