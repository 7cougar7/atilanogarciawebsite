function csrfToken() {
  const el = document.querySelector("[name=csrfmiddlewaretoken]");
  return el ? el.value : "";
}

// Personal AI landing page (shown to authenticated users). `username` and `logoutUrl`
// come from data-* props. The logout form posts with the CSRF token from the hidden
// input {% csrf_token %} renders in new_base.html.
export default function PersonalAi({ username, logoutUrl }) {
  return (
    <div className="container mt-5">
      <div className="row justify-content-center">
        <div className="col-md-8">
          <div className="card">
            <div className="card-body text-center">
              <h2 className="card-title">Welcome to Your Personal AI Page</h2>
              <p>This is your personal space. More features will be added soon!</p>
              <p>
                You are logged in as: <strong>{username}</strong>
              </p>
              <form action={logoutUrl} method="post" className="d-inline">
                <input
                  type="hidden"
                  name="csrfmiddlewaretoken"
                  value={csrfToken()}
                />
                <button type="submit" className="btn btn-danger">
                  Log Out
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
