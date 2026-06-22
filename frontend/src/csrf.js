// Reads Django's CSRF token from the hidden input that {% csrf_token %} renders
// (the cookie is HttpOnly, so it isn't JS-readable). Shared by the island forms
// that POST back to Django.
export function csrfToken() {
  const el = document.querySelector("[name=csrfmiddlewaretoken]");
  return el ? el.value : "";
}
