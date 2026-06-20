// Design-system primitive: an external link styled as a button, with an optional solid
// brand color. Used for call-to-action links (livestreams, Venmo, etc.).
export default function LinkButton({ href, color, className = "", children, ...rest }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      role="button"
      className={`btn btn-primary ${className}`.trim()}
      style={color ? { borderColor: color, backgroundColor: color } : undefined}
      {...rest}
    >
      {children}
    </a>
  );
}
