import { useState } from "react";
import {
  b64urlToBytes,
  bytesToB64url,
  csrfToken,
  stripNulls,
} from "../webauthn.js";

// Passkey registration flow (WebAuthn navigator.credentials.create). Faithful port of
// the old inline script: fetch options, convert snake_case -> camelCase, decode the
// base64url buffers, create the credential, encode it, and POST it to complete.
// Endpoint URLs come from data-* props.
export default function PasskeyRegister({
  regBeginUrl,
  regCompleteUrl,
  homepageUrl,
}) {
  const [message, setMessage] = useState(null); // { text, error }
  const [busy, setBusy] = useState(false);

  async function register() {
    setBusy(true);
    setMessage({ text: "Starting passkey registration…", error: false });
    try {
      const resp = await fetch(regBeginUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken(),
        },
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.message || "Failed to start registration");
      }
      const opts = await resp.json();

      // The server returns snake_case; the WebAuthn API wants camelCase.
      if (opts.pub_key_cred_params) {
        opts.pubKeyCredParams = opts.pub_key_cred_params;
        delete opts.pub_key_cred_params;
      }
      if (opts.exclude_credentials) {
        opts.excludeCredentials = opts.exclude_credentials;
        delete opts.exclude_credentials;
      }
      if (opts.user && opts.user.display_name) {
        opts.user.displayName = opts.user.display_name;
        delete opts.user.display_name;
      }

      // Drop fido2's null optional fields (hints, transports, ...) before decoding.
      stripNulls(opts);

      // Decode base64url buffers for the browser.
      opts.challenge = b64urlToBytes(opts.challenge);
      opts.user.id = b64urlToBytes(opts.user.id);
      if (opts.excludeCredentials) {
        for (const cred of opts.excludeCredentials) {
          cred.id = b64urlToBytes(cred.id);
        }
      }

      setMessage({
        text: "Please use your device's authentication method…",
        error: false,
      });

      const credential = await navigator.credentials.create({ publicKey: opts });

      setMessage({ text: "Saving your passkey…", error: false });

      const encoded = {
        id: credential.id,
        rawId: bytesToB64url(credential.rawId),
        response: {
          clientDataJSON: bytesToB64url(credential.response.clientDataJSON),
          attestationObject: bytesToB64url(credential.response.attestationObject),
        },
        type: credential.type,
      };

      const verifyResp = await fetch(regCompleteUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken(),
        },
        body: JSON.stringify(encoded),
      });
      const verifyData = await verifyResp.json();

      if (verifyData.status === "OK") {
        setMessage({
          text: "Passkey created successfully! You can now use it to log in.",
          error: false,
        });
        setTimeout(() => {
          window.location.href = verifyData.redirect_url || homepageUrl;
        }, 2000);
      } else {
        throw new Error(verifyData.message || "Registration failed");
      }
    } catch (error) {
      setMessage({ text: error.message, error: true });
      setBusy(false);
    }
  }

  return (
    <div className="container mt-5">
      <div className="row justify-content-center">
        <div className="col-md-6">
          <div className="card">
            <div className="card-body">
              <h2 className="card-title text-center mb-4">Set Up Your Passkey</h2>
              <p className="text-center">
                Create a passkey for secure, passwordless authentication on future
                visits.
              </p>

              {message && (
                <div className="mb-3">
                  <div
                    className={`alert ${message.error ? "alert-danger" : "alert-success"}`}
                  >
                    {message.text}
                  </div>
                </div>
              )}

              <div className="d-grid gap-2">
                <button
                  className="btn btn-primary"
                  onClick={register}
                  disabled={busy}
                >
                  Create Passkey
                </button>
              </div>

              <div className="mt-3 text-center">
                <small className="text-muted">
                  Passkeys use your device's built-in security (Face ID, Touch ID, or
                  Windows Hello) to provide secure, convenient authentication without
                  passwords.
                </small>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
