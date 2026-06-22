import { useState } from "react";

function csrfToken() {
  const el = document.querySelector("[name=csrfmiddlewaretoken]");
  return el ? el.value : "";
}

// v2-styled two-way translator-call form. Same backend behavior as the original
// Translator (POST to submitUrl with caller/callee/access code, loading + result
// states); restyled with the v2 design-system classes. `submitUrl` comes from the
// mount point's data-submit-url attribute.
export default function TranslatorV2({ submitUrl }) {
  const [caller, setCaller] = useState("");
  const [callee, setCallee] = useState("");
  const [accessCode, setAccessCode] = useState("");
  const [status, setStatus] = useState(null); // null | "loading" | "ok" | "error"

  async function submit(e) {
    e.preventDefault();
    setStatus("loading");
    try {
      const res = await fetch(submitUrl, {
        method: "POST",
        headers: { "X-CSRFToken": csrfToken() },
        body: new URLSearchParams({
          caller_phone_number: caller,
          callee_phone_number: callee,
          access_code: accessCode,
        }),
      });
      setStatus(res.ok ? "ok" : "error");
      if (res.ok) window.trackToolUsage?.("Language Translator");
    } catch {
      setStatus("error");
    }
  }

  return (
    <div className="v2-tool-panel">
      <form className="v2-tool-form" onSubmit={submit}>
        <div className="v2-field">
          <label className="v2-label" htmlFor="tr-caller">Caller phone number</label>
          <input
            id="tr-caller"
            type="tel"
            className="v2-input"
            placeholder="+1 555 123 4567"
            value={caller}
            onChange={(e) => setCaller(e.target.value)}
          />
        </div>
        <div className="v2-field">
          <label className="v2-label" htmlFor="tr-callee">Callee phone number</label>
          <input
            id="tr-callee"
            type="tel"
            className="v2-input"
            placeholder="+1 555 765 4321"
            value={callee}
            onChange={(e) => setCallee(e.target.value)}
          />
        </div>
        <div className="v2-field">
          <label className="v2-label" htmlFor="tr-code">Access code</label>
          <input
            id="tr-code"
            type="text"
            className="v2-input"
            placeholder="Access code"
            value={accessCode}
            onChange={(e) => setAccessCode(e.target.value)}
          />
        </div>
        <button type="submit" className="v2-btn" disabled={status === "loading"}>
          {status === "loading" ? "Calling…" : "Initiate call"}
        </button>

        {status === "ok" && (
          <p className="v2-tool-msg v2-tool-msg--ok">Call initiated.</p>
        )}
        {status === "error" && (
          <p className="v2-tool-msg v2-tool-msg--err">
            Could not initiate the call. Check the numbers and try again.
          </p>
        )}
      </form>
    </div>
  );
}
