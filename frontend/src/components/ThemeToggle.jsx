import { useState } from "react";

// Toggles the site theme by flipping the data-theme attribute on <html> (which the CSS
// variables in color_layout.css key off) and persisting the choice. The no-flicker
// inline script in new_base.html applies the saved value before paint on each load.
export default function ThemeToggle() {
  const [dark, setDark] = useState(
    () => localStorage.getItem("dark_mode") === "true",
  );

  function toggle() {
    const next = !dark;
    setDark(next);
    localStorage.setItem("dark_mode", String(next));
    document.documentElement.setAttribute(
      "data-theme",
      next ? "dark" : "light",
    );
  }

  return (
    <button
      type="button"
      className="btn switch-button"
      aria-label="Toggle dark mode"
      aria-pressed={dark}
      onClick={toggle}
    >
      <i className={dark ? "fas fa-moon" : "fas fa-sun"}></i>
    </button>
  );
}
