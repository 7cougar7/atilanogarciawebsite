import { createRoot } from "react-dom/client";
import ProjectList from "./components/ProjectList.jsx";
import SocialLinks from "./components/SocialLinks.jsx";

// Island registry. A DOM node opts in with data-react-component="<name>" and gets its
// props from a {% ... |json_script:"id" %} element referenced via data-props-id.
const COMPONENTS = {
  ProjectList,
  SocialLinks,
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

// Mount one tick after DOMContentLoaded so the inline jQuery dark-mode load-swap has
// already run; React then renders the final theme-correct class (see theme.js) and is
// not double-swapped. Server-rendered fallback content inside each mount point keeps
// the page meaningful for SEO / no-JS until React takes over.
function start() {
  setTimeout(mountIslands, 0);
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", start);
} else {
  start();
}
