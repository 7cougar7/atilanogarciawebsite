// 404 illustration. The SVG must render inline (not via <img>) because 404.css animates
// its element IDs (#tree, #leaf, #wood-stump, ...), which only works when the SVG is in
// the document. It's imported as a raw string from the source .svg file (single source
// of truth, no hand-transcription) and inlined — safe, since it's our own static markup.
import svgMarkup from "../assets/404.svg?raw";

export default function NotFound() {
  return (
    <div
      className="col text-center"
      dangerouslySetInnerHTML={{ __html: svgMarkup }}
    />
  );
}
