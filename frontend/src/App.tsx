import { Link, Outlet, Route, Routes } from "react-router-dom";

import { ArticlePage } from "./pages/ArticlePage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { SearchPage } from "./pages/SearchPage";

/** Shared chrome rendered on every page. */
function Layout() {
  return (
    <div className="app">
      <header className="app-header">
        <h1>
          <Link to="/">vbrs-browser</Link>
        </h1>
        <p className="app-tagline">Read-only dictionary browser.</p>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}

function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<SearchPage />} />
        <Route path="articles/:articleId" element={<ArticlePage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}

export default App;