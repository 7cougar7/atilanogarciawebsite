import GlassCard from "./GlassCard.jsx";
// The two Office scripts contain hand-placed highlight spans (they spell "I accept"), so
// they're inlined verbatim from their source files rather than re-typed. Image URLs come
// from data-* props.
import officeScript from "../assets/kky-office.html?raw";
import millionScript from "../assets/kky-million.html?raw";

const TRAIL = [
  "Hendrickson High School",
  "UT Austin",
  "Longhorn Band",
  "Kappa Kappa Psi",
];

function ImageCard({ src, alt, style }) {
  return (
    <GlassCard>
      <div className="card-body text-center p-3">
        <img src={src} className="img-fluid rounded" style={style} alt={alt} />
      </div>
    </GlassCard>
  );
}

function ScriptCard({ title, html }) {
  return (
    <GlassCard>
      <div className="card-body p-3 p-md-4">
        <h2 className="dark-color">{title}</h2>
        <p className="dark-color" dangerouslySetInnerHTML={{ __html: html }} />
      </div>
    </GlassCard>
  );
}

export default function Kky({ crestImg, tromImg, sectionImg }) {
  return (
    <>
      <GlassCard className="mb-0">
        <div className="card-body p-3 p-md-4">
          <nav aria-label="breadcrumb">
            <ol className="breadcrumb mb-0">
              {TRAIL.map((step, i) => {
                const last = i === TRAIL.length - 1;
                return (
                  <li
                    key={step}
                    className={`breadcrumb-item dark-color${last ? " active fw-bold" : ""}`}
                    aria-current={last ? "page" : undefined}
                  >
                    {step}
                  </li>
                );
              })}
            </ol>
          </nav>
        </div>
      </GlassCard>

      <ImageCard
        src={crestImg}
        alt="Kappa Kappa Psi fraternity crest and official logo"
        style={{ maxHeight: "40vh", objectFit: "contain" }}
      />

      <ScriptCard title="The Office" html={officeScript} />

      <ImageCard
        src={tromImg}
        alt="Atilano Garcia playing trombone in the university band"
        style={{ maxHeight: "50vh", objectFit: "cover", width: "100%" }}
      />

      <ScriptCard title="Million Dollar Sale" html={millionScript} />

      <ImageCard
        src={sectionImg}
        alt="Kappa Kappa Psi fraternity section group photo with members"
        style={{ maxHeight: "50vh", objectFit: "cover", width: "100%" }}
      />

      <GlassCard>
        <div className="card-body p-3 p-md-4">
          <h2 className="dark-color">Hook 'em</h2>
          <p className="dark-color">I Accept :)</p>
        </div>
      </GlassCard>
    </>
  );
}
