import { useState } from "react";

// Reads the CSRF token from the hidden input {% csrf_token %} renders in new_base.html
// (the cookie is HttpOnly, so it isn't JS-readable).
function csrfToken() {
  const el = document.querySelector("[name=csrfmiddlewaretoken]");
  return el ? el.value : "";
}

// React version of the URL shortener tool. Improves on the old jQuery form with a
// loading state, inline error handling, and copy feedback (instead of a blocking
// alert). `submitUrl` comes from the mount point's data-submit-url attribute.
export default function UrlShortener({ submitUrl }) {
  const [url, setUrl] = useState("");
  const [shortened, setShortened] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  async function submit(e) {
    e.preventDefault();
    if (!url.trim()) return;
    setLoading(true);
    setError("");
    try {
      const res = await fetch(submitUrl, {
        method: "POST",
        headers: { "X-CSRFToken": csrfToken() },
        body: new URLSearchParams({ url: url.trim() }),
      });
      const data = await res.json();
      if (res.ok && data.shortened_url) {
        setShortened(data.shortened_url);
        window.trackToolUsage?.("URL Shortener");
      } else {
        setShortened("");
        setError(data.error || "Something went wrong. Please try again.");
      }
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText(shortened);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard unavailable; ignore */
    }
  }

  return (
    <div
      className="glass-card"
      style={{
        minHeight: "45vh",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <div className="column w-100">
        <form className="row" onSubmit={submit}>
          <div className="input-group center-elements p-5">
            <input
              type="text"
              className="form-control"
              placeholder="URL To Shorten"
              aria-label="URL To Shorten"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
            />
            <button type="submit" className="btn light-fill" disabled={loading}>
              <span className="dark-color">
                {loading ? "Shortening…" : "Shorten URL"}
              </span>
            </button>
          </div>
        </form>

        {error && (
          <div className="row">
            <div className="col text-center">
              <span className="dark-color">{error}</span>
            </div>
          </div>
        )}

        {shortened && (
          <div
            className="row"
            style={{ justifyContent: "center", alignItems: "center" }}
          >
            <div className="input-group center-elements w-50 px-5">
              <input
                type="text"
                className="form-control"
                aria-label="Shortened URL"
                value={shortened}
                readOnly
              />
              <button
                type="button"
                className="btn light-fill"
                onClick={copy}
                aria-label="Copy shortened URL"
              >
                <i
                  className={`${copied ? "fas fa-check" : "far fa-clipboard"} dark-color`}
                ></i>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
