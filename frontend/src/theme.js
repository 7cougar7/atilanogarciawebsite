// The existing dark-mode system (new_base.html) swaps the `dark-color` class to
// `light-color` on every element when dark mode is active. React islands must render
// the post-swap class so they match their server-rendered siblings. We read the same
// localStorage key the inline script uses.
//
// This coupling is intentional and temporary: the planned CSS-variable theme rework
// removes the class swapping entirely, at which point islands can drop this helper.
export function colorClass() {
  return localStorage.getItem("dark_mode") === "true" ? "light-color" : "dark-color";
}
