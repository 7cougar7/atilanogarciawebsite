import { colorClass } from "../theme.js";

// Renders the social icon row. Mirrors the server-rendered fallback in
// templates/partials/_socials.html. Fires the global GA helper on click (defined as a
// stub in new_base.html, real implementation when analytics is configured).
export default function SocialLinks({ socials = [] }) {
  const cls = colorClass();
  return (
    <div className="row w-100">
      <div className="col text-center my-2">
        {socials.map((s) => (
          <a
            key={s.platform}
            href={s.url}
            aria-label={s.platform}
            onClick={() => window.trackSocialClick?.(s.platform)}
          >
            <i className={`${s.icon} ${cls} fa-2x mx-3`}></i>
          </a>
        ))}
      </div>
    </div>
  );
}
