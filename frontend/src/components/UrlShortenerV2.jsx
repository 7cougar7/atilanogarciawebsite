import { useState } from "react";

function csrfToken() {
  const el = document.querySelector("[name=csrfmiddlewaretoken]");
  return el ? el.value : "";
}

// v2-styled URL shortener. Same backend behavior as the original UrlShortener (POST
// to submitUrl, loading + error + copy states); restyled with the v2 design system.
// `submitUrl` comes from the mount point's data-submit-url attribute.
export default function UrlShortenerV2({ submitUrl }) {
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
    <div className="v2-tool-panel">
      <form className="v2-tool-form" onSubmit={submit}>
        <div className="v2-field">
          <label className="v2-label" htmlFor="us-url">URL to shorten</label>
          <input
            id="us-url"
            type="url"
            className="v2-input"
            placeholder="https://example.com/a-very-long-link"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
        </div>
        <button type="submit" className="v2-btn" disabled={loading}>
          {loading ? "Shortening…" : "Shorten URL"}
        </button>

        {error && <p className="v2-tool-msg v2-tool-msg--err">{error}</p>}

        {shortened && (
          <div className="v2-field">
            <label className="v2-label" htmlFor="us-result">Shortened URL</label>
            <div className="v2-tool-result">
              <input
                id="us-result"
                type="text"
                className="v2-input"
                value={shortened}
                readOnly
              />
              <button
                type="button"
                className="v2-btn v2-btn--ghost"
                onClick={copy}
                aria-label="Copy shortened URL"
              >
                {copied ? "Copied" : "Copy"}
              </button>
            </div>
          </div>
        )}
      </form>
    </div>
  );
}
