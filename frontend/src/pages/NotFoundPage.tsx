import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <section className="not-found">
      <h2>Page not found</h2>
      <p>The page you requested does not exist.</p>
      <Link to="/">Back to search</Link>
    </section>
  );
}