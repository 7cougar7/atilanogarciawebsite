// WebAuthn helpers shared by the login and passkey-registration islands. The server
// speaks base64url; the browser's credential API speaks ArrayBuffers/typed arrays.

export function csrfToken() {
  const el = document.querySelector("[name=csrfmiddlewaretoken]");
  return el ? el.value : "";
}

// fido2 serializes unset optional fields (hints, transports, ...) as null, which the
// WebAuthn API rejects ("cannot be converted to a sequence"). Recursively drop them.
// Call this while the options are still plain JSON, before decoding any buffers.
export function stripNulls(value) {
  if (Array.isArray(value)) {
    value.forEach(stripNulls);
  } else if (value && typeof value === "object") {
    for (const key of Object.keys(value)) {
      if (value[key] === null) delete value[key];
      else stripNulls(value[key]);
    }
  }
  return value;
}

// base64url string -> Uint8Array (accepted anywhere the WebAuthn API wants a BufferSource).
export function b64urlToBytes(value) {
  const b64 = value.replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(b64);
  const bytes = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i);
  return bytes;
}

// ArrayBuffer/typed array -> base64url string.
export function bytesToB64url(buffer) {
  const bytes = new Uint8Array(buffer);
  let str = "";
  for (const b of bytes) str += String.fromCharCode(b);
  return btoa(str).replace(/\+/g, "-").replace(/\//g, "_").replace(/=/g, "");
}
