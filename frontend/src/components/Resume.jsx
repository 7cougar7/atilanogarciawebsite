import GlassCard from "./GlassCard.jsx";

// Resume page: embeds the PDF with a download link. `pdfUrl` comes from the mount
// point's data-pdf-url attribute (resolved by Django's {% static %}).
export default function Resume({ pdfUrl }) {
  return (
    <GlassCard>
      <div className="card-body p-4">
        <div className="row mb-3">
          <div className="col text-center">
            <h1 className="dark-color">Resume</h1>
          </div>
        </div>
        <div className="row mb-3">
          <div className="col text-center">
            <a
              href={pdfUrl}
              target="_blank"
              rel="noreferrer"
              className="btn btn-primary me-2"
              onClick={() => window.trackResumeDownload?.()}
            >
              Download PDF
            </a>
          </div>
        </div>
        <div className="row">
          <div className="col">
            <iframe
              src={pdfUrl}
              style={{
                width: "100%",
                height: "80vh",
                border: "none",
                borderRadius: "10px",
              }}
              title="Atilano Garcia Resume"
            />
          </div>
        </div>
      </div>
    </GlassCard>
  );
}
