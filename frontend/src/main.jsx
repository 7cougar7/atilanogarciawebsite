import { createRoot } from "react-dom/client";

// Island registry, built automatically from every component file. A DOM node opts in
// with data-react-component="<Name>", where <Name> is the component file's basename
// (e.g. components/ProjectList.jsx -> "ProjectList"). Adding a page is now just dropping
// a new file in components/ — no manual registration here, so this file stops being a
// merge-conflict magnet. Props come from a {% ... |json_script:"id" %} element
// referenced via data-props-id (structured) and/or plain data-* attributes (scalars).
const COMPONENTS = {};
const modules = import.meta.glob("./components/*.jsx", { eager: true });
for (const [path, module] of Object.entries(modules)) {
  const name = path.split("/").pop().replace(/\.jsx$/, "");
  if (!module.default) {
    console.warn(`[islands] ${path} has no default export; skipping`);
    continue;
  }
  COMPONENTS[name] = module.default;
}

function readProps(el) {
  const props = {};

  // Structured props from a json_script element.
  const id = el.dataset.propsId;
  if (id) {
    const node = document.getElementById(id);
    if (node) {
      try {
        Object.assign(props, JSON.parse(node.textContent));
      } catch (e) {
        console.error(`[islands] bad props JSON in #${id}:`, e);
      }
    }
  }

  // Scalar props from data-* attributes (camelCased), excluding the control ones.
  for (const [key, value] of Object.entries(el.dataset)) {
    if (key !== "reactComponent" && key !== "propsId") props[key] = value;
  }

  return props;
}

function mountIslands() {
  document.querySelectorAll("[data-react-component]").forEach((el) => {
    const name = el.dataset.reactComponent;
    const Component = COMPONENTS[name];
    if (!Component) {
      console.warn(`[islands] unknown component: ${name}`);
      return;
    }
    createRoot(el).render(<Component {...readProps(el)} />);
  });
}

// Server-rendered fallback content inside each mount point keeps the page meaningful for
// SEO / no-JS until React takes over. Theming is CSS-variable driven (color_layout.css),
// so islands need no special mount timing.
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", mountIslands);
} else {
  mountIslands();
}
