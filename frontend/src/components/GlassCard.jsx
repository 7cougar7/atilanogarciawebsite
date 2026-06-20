// Design-system primitive: the frosted "glass" card used across the site. Wraps the
// existing .glass-card CSS so pages compose a component instead of repeating markup.
export default function GlassCard({ className = "", children, ...rest }) {
  return (
    <div className={`glass-card ${className}`.trim()} {...rest}>
      {children}
    </div>
  );
}
