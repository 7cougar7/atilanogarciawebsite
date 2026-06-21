import { createRoot } from "react-dom/client";
import Graduation from "./components/Graduation.jsx";
import Kky from "./components/Kky.jsx";
import MessageCard from "./components/MessageCard.jsx";
import NotFound from "./components/NotFound.jsx";
import PasskeyRegister from "./components/PasskeyRegister.jsx";
import PersonalAi from "./components/PersonalAi.jsx";
import ProjectList from "./components/ProjectList.jsx";
import Resume from "./components/Resume.jsx";
import SocialLinks from "./components/SocialLinks.jsx";
import ThemeToggle from "./components/ThemeToggle.jsx";
import Translator from "./components/Translator.jsx";
import UnifiedLogin from "./components/UnifiedLogin.jsx";
import UrlShortener from "./components/UrlShortener.jsx";

// Island registry. A DOM node opts in with data-react-component="<name>". Props come
// from a {% ... |json_script:"id" %} element referenced via data-props-id (for
// structured data) and/or plain data-* attributes (for simple scalar values).
const COMPONENTS = {
  Graduation,
  Kky,
  MessageCard,
  NotFound,
  PasskeyRegister,
  PersonalAi,
  ProjectList,
  Resume,
  SocialLinks,
  ThemeToggle,
  Translator,
  UnifiedLogin,
  UrlShortener,
};

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
