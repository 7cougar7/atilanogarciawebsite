import { useState } from "react";

function csrfToken() {
  const el = document.querySelector("[name=csrfmiddlewaretoken]");
  return el ? el.value : "";
}

// React version of the two-way translator-call form. The original jQuery fired the POST
// and showed no feedback at all; this adds a loading state and a success/error message.
// `submitUrl` comes from the mount point's data-submit-url attribute.
export default function Translator({ submitUrl }) {
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
              aria-label="Caller Phone Number"
              placeholder="Caller Phone Number"
              value={caller}
              onChange={(e) => setCaller(e.target.value)}
            />
            <input
              type="text"
              className="form-control"
              aria-label="Callee Phone Number"
              placeholder="Callee Phone Number"
              value={callee}
              onChange={(e) => setCallee(e.target.value)}
            />
            <input
              type="text"
              className="form-control"
              aria-label="Access Code"
              placeholder="Access Code"
              value={accessCode}
              onChange={(e) => setAccessCode(e.target.value)}
            />
            <button
              type="submit"
              className="btn light-fill"
              disabled={status === "loading"}
            >
              <span className="dark-color">
                {status === "loading" ? "Calling…" : "Initiate Call"}
              </span>
            </button>
          </div>
        </form>

        {status === "ok" && (
          <div className="row">
            <div className="col text-center">
              <span className="dark-color">Call initiated.</span>
            </div>
          </div>
        )}
        {status === "error" && (
          <div className="row">
            <div className="col text-center">
              <span className="dark-color">
                Could not initiate the call. Check the numbers and try again.
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
