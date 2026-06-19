import { createRoot } from "react-dom/client";
import ProjectList from "./components/ProjectList.jsx";
import SocialLinks from "./components/SocialLinks.jsx";
import ThemeToggle from "./components/ThemeToggle.jsx";

// Island registry. A DOM node opts in with data-react-component="<name>" and gets its
// props from a {% ... |json_script:"id" %} element referenced via data-props-id.
const COMPONENTS = {
  ProjectList,
  SocialLinks,
  ThemeToggle,
};

function readProps(el) {
  const id = el.dataset.propsId;
  if (!id) return {};
  const node = document.getElementById(id);
  if (!node) return {};
  try {
    return JSON.parse(node.textContent);
  } catch (e) {
    console.error(`[islands] bad props JSON in #${id}:`, e);
    return {};
  }
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
