import GlassCard from "./GlassCard.jsx";

const ORANGE = { borderColor: "#CC5500", backgroundColor: "#CC5500" };
const VENMO = { borderColor: "#008CFF", backgroundColor: "#008CFF" };

// Graduation announcement page (archival, May 2023). Static content composed as a React
// component; image URLs come from data-* props so Django's {% static %} resolves them.
export default function Graduation({ utSeal, dancingTilo, venmoLogo }) {
  const seal = (extraClass, style) => (
    <img src={utSeal} className={extraClass} style={style} alt="University of Texas official seal and logo" />
  );

  return (
    <GlassCard className="d-flex align-items-center">
      <div className="container text-center pt-2 px-md-4 pt-md-4 pb-md-3">
        <div className="row d-flex flex-wrap align-items-center">
          <div className="col d-none d-lg-block">{seal("img-fluid w-50")}</div>
          <div className="col d-lg-none">{seal("", { maxWidth: "15vw", height: "auto" })}</div>
          <div className="col-6">
            <div className="d-none d-lg-block">
              <div className="row">
                <div className="col">
                  <h1 className="display-6">
                    <u><b>Tilo's Graduation</b></u>
                  </h1>
                </div>
              </div>
              <div className="row">
                <div className="col">
                  <h2 className="display-6" style={{ fontSize: "2rem" }}>May 5-6th, 2023</h2>
                </div>
              </div>
            </div>
            <h2 className="display-5 d-lg-none">
              <u><b>Tilo's Graduation</b></u>
            </h2>
          </div>
          <div className="col d-none d-lg-block">{seal("img-fluid w-50")}</div>
          <div className="col d-lg-none">{seal("", { maxWidth: "15vw", height: "auto" })}</div>
        </div>

        <div className="row d-lg-none">
          <div className="col">
            <h3 className="display-6">May 5-6th, 2023</h3>
          </div>
        </div>

        <div className="row">
          <div className="col d-flex flex-wrap align-items-center">
            <h2 className="display-6" style={{ fontSize: "2rem" }}>
              I will be graduating from the University of Texas with a Bachelor of Science in
              Electrical Engineering.
            </h2>
          </div>
          <div className="col my-auto mx-2">
            <div className="row my-4 px-1 px-lg-5">
              <a className="btn btn-primary" href="https://www.youtube.com/watch?v=Z8m3L7OloCk" target="_blank" rel="noreferrer" role="button" style={ORANGE}>
                <p className="my-0">Cockrell School of Engineering Livestream<br />(May 5th, 5:30pm)</p>
              </a>
            </div>
            <div className="row my-4 px-1 px-lg-5">
              <a className="btn btn-primary" href="https://commencement.utexas.edu/content/webcasts" target="_blank" rel="noreferrer" role="button" style={ORANGE}>
                <p className="my-0">University Wide Commencement Livestream<br />(May 6th, 7:30pm)</p>
              </a>
            </div>
          </div>
        </div>

        <div className="row">
          <div className="col">
            <p className="lead m-0">
              Additionally, I will be graduating as President of the Alpha Tau Chapter of Kappa
              Kappa Psi, member of the Alpha Iota chapter of Phi Mu Alpha Sinfonia, Trombone
              Section Leader of the Longhorn Band, and member of THE Longhorn Pep Band.
            </p>
          </div>
        </div>

        <div className="row">
          <div className="col-2 my-auto d-none d-lg-block">
            <img src={dancingTilo} className="img-fluid w-75 rounded py-1" alt="Atilano Garcia celebrating graduation with a fun dance animation" />
          </div>
          <div className="col my-auto d-lg-none">
            <img src={dancingTilo} className="img-fluid rounded py-1" alt="Atilano Garcia celebrating graduation with a fun dance animation" />
          </div>
          <div className="col d-flex flex-wrap align-items-center">
            <p className="my-0">
              As I reflect on my college journey, I am truly grateful for the unwavering support
              and encouragement from each one of you. Your belief in me has made a significant
              impact on my personal and academic growth, and I am incredibly thankful for your
              presence in my life.{" "}
              <span className="d-none d-lg-flex">
                As I embark on the next chapter, I carry with me the lessons, experiences, and
                cherished memories that you have helped shape. From the bottom of my heart, thank
                you for being an integral part of my college career and for your continued support
                as I move forward.
              </span>
            </p>
          </div>
        </div>

        <div className="row d-lg-none">
          <div className="col">
            <p>
              As I embark on the next chapter, I carry with me the lessons, experiences, and
              cherished memories that you have helped shape. From the bottom of my heart, thank you
              for being an integral part of my college career and for your continued support as I
              move forward.
            </p>
          </div>
        </div>

        <div className="row">
          <div className="col">
            <p className="m-0">
              I am excited to celebrate this milestone with you all, and I hope you will join me in
              celebrating my graduation. In the spirit of gratitude, I would like to mention that
              should anyone wish to extend their generosity through a gift, my Venmo is available
              for your convenience. Once again, thank you all for the love and support you have
              shown me throughout this journey, and I eagerly anticipate what lies ahead in this
              exciting new chapter.
            </p>
          </div>
        </div>

        <div className="row my-3 my-lg-2">
          <div className="col">
            <a className="btn btn-primary" href="https://account.venmo.com/u/tilo_g_" target="_blank" rel="noreferrer" role="button" style={VENMO}>
              <div className="d-none d-lg-block">
                <img src={venmoLogo} style={{ maxWidth: "10vw", height: "auto" }} alt="Venmo payment logo for graduation gifts" />
              </div>
              <div className="d-lg-none">
                <img src={venmoLogo} style={{ maxWidth: "20vw", height: "auto" }} alt="Venmo payment logo for graduation gifts" />
              </div>
            </a>
          </div>
        </div>
      </div>
    </GlassCard>
  );
}
