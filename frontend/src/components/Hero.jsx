import { useEffect, useLayoutEffect, useRef, useState } from "react";
import "./Hero.css";

// "It builds itself" hero. On every load the page constructs — a faint grid wipes in,
// the name draws letter-by-letter (each glyph's outline traces, then fills), then the
// eyebrow/rule/tagline/tick settle. prefers-reduced-motion shows the finished state
// immediately (handled in CSS).
//
// Responsive: the name renders one SVG per word in a flex-wrap row, each measured to
// its exact text width. Words sit on one line when they fit and wrap to stacked lines
// when they don't — with identical glyph size everywhere (shared CSS height + internal
// font-size), since SVG <text> can't reflow on its own.
const DEFAULTS = {
  name: "Atilano Garcia",
  eyebrow: "Software Engineer · Austin, TX",
  tagline:
    "I build full-stack web apps for a living, and side projects for the fun of it.",
};

// Per-letter draw timing. A constant draw duration keeps every letter watchable; the
// gap between letters shrinks slightly across the word for a gentle acceleration that
// never bunches into a "pop" (verified on tools/screenshots/filmstrip.mjs).
const START = 0.9; // s — after the grid settles
const DUR = 0.82; // s — each letter's draw
const GAP_FIRST = 0.21; // s — gap between the first letters
const GAP_LAST = 0.15; // s — gap between the last letters

function letterTimings(n) {
  const out = [];
  let delay = START;
  for (let i = 0; i < n; i++) {
    if (i > 0) {
      const gt = (i - 1) / Math.max(1, n - 2);
      delay += GAP_FIRST + (GAP_LAST - GAP_FIRST) * gt;
    }
    out.push({ delay, dur: DUR });
  }
  return out;
}

export default function Hero(props = {}) {
  const name = props.name || DEFAULTS.name;
  const eyebrow = props.eyebrow || DEFAULTS.eyebrow;
  const tagline = props.tagline || DEFAULTS.tagline;

  const words = name.split(" ");
  const totalLetters = words.reduce((sum, w) => sum + w.length, 0);
  const times = letterTimings(totalLetters);

  // Signal "hero:done" once the build sequence settles, so chrome outside React (the
  // nav) can fly in afterward. Synced to React mount, so it tracks the actual
  // animation start regardless of when the bundle loaded. Fires immediately under
  // reduced motion (the hero shows its settled state right away).
  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const HERO_TOTAL_MS = 5400; // just after the last element (corner coords) settles
    const t = setTimeout(
      () => document.dispatchEvent(new CustomEvent("hero:done")),
      reduce ? 0 : HERO_TOTAL_MS,
    );
    return () => clearTimeout(t);
  }, []);

  // Measure each word's rendered text so its SVG viewBox hugs the glyphs exactly.
  // Runs before paint (useLayoutEffect), so the estimate is never visible.
  const textRefs = useRef([]);
  const [widths, setWidths] = useState(() => words.map((w) => w.length * 95));
  useLayoutEffect(() => {
    setWidths(
      words.map((w, i) => {
        const el = textRefs.current[i];
        return el ? Math.ceil(el.getComputedTextLength()) : w.length * 95;
      }),
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [name]);

  const PAD = 12; // user-unit breathing room on each side of a word
  let gi = 0; // running global letter index across all words (continuous cascade)

  return (
    <section className="hero">
      <div className="hero-grid" aria-hidden="true" />
      <div className="hero-stage">
        <p className="hero-eyebrow">{eyebrow}</p>
        <h1 className="hero-name" aria-label={name}>
          {words.map((word, wi) => {
            const vw = widths[wi] + PAD * 2;
            const startGi = gi;
            gi += word.length;
            return (
              <svg
                key={wi}
                className="hero-word"
                viewBox={`0 0 ${vw} 210`}
                role="presentation"
                aria-hidden="true"
              >
                <text
                  ref={(el) => {
                    textRefs.current[wi] = el;
                  }}
                  x={vw / 2}
                  y="155"
                  textAnchor="middle"
                  className="hero-name-text"
                >
                  {word.split("").map((ch, ci) => {
                    const { delay, dur } = times[startGi + ci];
                    return (
                      <tspan
                        key={ci}
                        className="hero-glyph"
                        style={{ "--d": `${delay.toFixed(3)}s`, "--dur": `${dur.toFixed(3)}s` }}
                      >
                        {ch}
                      </tspan>
                    );
                  })}
                </text>
              </svg>
            );
          })}
        </h1>
        <div className="hero-rule" aria-hidden="true" />
        <p className="hero-tag">{tagline}</p>
        <span className="hero-tick" aria-hidden="true" />
      </div>
      <span className="hero-coord hero-coord--tl">grid · 48</span>
      <span className="hero-coord hero-coord--br">build 001</span>
      {/* Scroll cue — fades in just after the build settles. */}
      <div className="hero-scroll" aria-hidden="true">
        <span className="hero-scroll-label">Scroll</span>
        <span className="hero-scroll-line" />
      </div>
    </section>
  );
}
