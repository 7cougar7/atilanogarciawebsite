import { useState } from "react";
import {
  b64urlToBytes,
  bytesToB64url,
  csrfToken,
  stripNulls,
} from "../webauthn.js";

// Unified login: submit a username, the server replies whether the user has a passkey
// (prompt WebAuthn navigator.credentials.get) or gets a magic link emailed. Faithful
// port of the old inline script. Endpoint URLs + `next` come from data-* props.
export default function UnifiedLogin({
  loginUrl,
  authBeginUrl,
  authCompleteUrl,
  next = "",
}) {
  const [username, setUsername] = useState("");
  const [message, setMessage] = useState(null); // { text, error }

  async function handlePasskeyLogin(user) {
    try {
      const challengeResp = await fetch(authBeginUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
          "X-CSRFToken": csrfToken(),
        },
        body: new URLSearchParams({ username: user }),
      });
      const data = await challengeResp.json();
      const publicKey = data.public_key;
      // Drop fido2's null optional fields (hints, transports, ...) before decoding.
      stripNulls(publicKey);
      // The server sends snake_case; the WebAuthn API wants camelCase. Converting
      // allow_credentials is essential — without it get() has no credential to target
      // and fails with NotAllowedError.
      if (publicKey.allow_credentials) {
        publicKey.allowCredentials = publicKey.allow_credentials;
        delete publicKey.allow_credentials;
      }
      if (publicKey.rp_id) {
        publicKey.rpId = publicKey.rp_id;
        delete publicKey.rp_id;
      }
      if (publicKey.user_verification) {
        publicKey.userVerification = publicKey.user_verification;
        delete publicKey.user_verification;
      }
      if (publicKey.challenge) {
        publicKey.challenge = b64urlToBytes(publicKey.challenge);
      }
      if (publicKey.allowCredentials) {
        for (const cred of publicKey.allowCredentials) {
          if (cred.id) cred.id = b64urlToBytes(cred.id);
        }
      }

      const credential = await navigator.credentials.get({ publicKey });
      const encoded = {
        id: credential.id,
        rawId: bytesToB64url(credential.rawId),
        response: {
          clientDataJSON: bytesToB64url(credential.response.clientDataJSON),
          authenticatorData: bytesToB64url(credential.response.authenticatorData),
          signature: bytesToB64url(credential.response.signature),
          userHandle: credential.response.userHandle
            ? bytesToB64url(credential.response.userHandle)
            : null,
        },
        type: credential.type,
      };

      const verifyResp = await fetch(authCompleteUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken(),
        },
        body: JSON.stringify(encoded),
      });
      const verifyData = await verifyResp.json();
      if (verifyData.status === "OK") {
        window.location.href = verifyData.redirect_url;
      } else {
        setMessage({ text: "Login failed. Please try again.", error: true });
      }
    } catch {
      setMessage({
        text: "Passkey authentication failed. Please try again.",
        error: true,
      });
    }
  }

  async function submit(e) {
    e.preventDefault();
    setMessage(null);
    try {
      const resp = await fetch(loginUrl, {
        method: "POST",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
          "X-CSRFToken": csrfToken(),
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: new URLSearchParams({ username, next }),
      });
      if (resp.status === 403) {
        setMessage({
          text: "Security error. Please refresh the page and try again.",
          error: true,
        });
        return;
      }
      const data = await resp.json();
      if (resp.ok) {
        if (data.action === "prompt_passkey") {
          await handlePasskeyLogin(username);
        } else if (data.action === "magic_link_sent") {
          setMessage({ text: data.message, error: false });
        }
      } else {
        setMessage({ text: data.message, error: true });
      }
    } catch {
      setMessage({ text: "An error occurred. Please try again.", error: true });
    }
  }

  return (
    <div className="container mt-5">
      <div className="row justify-content-center">
        <div className="col-md-6">
          <div className="card">
            <div className="card-body">
              <h2 className="card-title text-center">Login</h2>
              {message && (
                <div
                  className={`alert ${message.error ? "alert-danger" : "alert-success"}`}
                >
                  {message.text}
                </div>
              )}
              <form onSubmit={submit}>
                <div className="mb-3">
                  <label htmlFor="id_username" className="form-label">
                    Username
                  </label>
                  <input
                    type="text"
                    className="form-control"
                    id="id_username"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    required
                  />
                </div>
                <button type="submit" className="btn btn-primary w-100">
                  Continue
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
