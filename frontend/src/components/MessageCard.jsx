// Design-system component: a centered card with a title, message, and optional action
// link. Used for simple status pages (logged out, invalid link, etc.). All text and the
// action come from data-* props so each page stays declarative in its template.
export default function MessageCard({ title, message, actionLabel, actionHref }) {
  return (
    <div className="container mt-5">
      <div className="row justify-content-center">
        <div className="col-md-6">
          <div className="card">
            <div className="card-body text-center">
              <h2 className="card-title">{title}</h2>
              {message && <p>{message}</p>}
              {actionHref && (
                <a href={actionHref} className="btn btn-primary">
                  {actionLabel}
                </a>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
