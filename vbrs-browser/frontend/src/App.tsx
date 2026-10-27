import { Link, Outlet, Route, Routes, useLocation } from "react-router-dom";
import type { Location } from "react-router-dom";

import favicon from "./assets/favicon.webp";
import { ArticleModal } from "./components/ArticleModal";
import { PageScrollbar } from "./components/PageScrollbar";
import { GITHUB_REPOSITORY_URL } from "./config";
import { ArticlePage } from "./pages/ArticlePage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { SearchPage } from "./pages/SearchPage";

function Layout() {
  const { pathname } = useLocation();

  return (
    <div className={`app${pathname === "/" ? "" : " app--reading"}`}>
      <div className="polar-backdrop" aria-hidden="true" />
      <PageScrollbar />
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <header className="app-header">
        <h1 className="app-brand">
          <Link to="/" aria-label="vbrs-browser">
            <img
              className="brand-icon"
              src={favicon}
              alt=""
              width={34}
              height={34}
            />
            <span aria-hidden="true">
              vbrs<span className="brand-dot">.</span>
            </span>
          </Link>
        </h1>
        <span className="app-tagline">Dictionary</span>
        <a
          className="github-link"
          href={GITHUB_REPOSITORY_URL}
          target="_blank"
          rel="noopener noreferrer"
          aria-label="View vbrs-browser on GitHub"
        >
          <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <path d="M12 .297C5.37.297 0 5.67 0 12.297c0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.043-1.61-4.043-1.61-.546-1.387-1.333-1.756-1.333-1.756-1.09-.745.083-.729.083-.729 1.205.084 1.838 1.237 1.838 1.237 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23a11.5 11.5 0 0 1 3-.404c1.02.005 2.045.138 3 .404 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12" />
          </svg>
        </a>
      </header>
      <main className="app-main" id="main-content" tabIndex={-1}>
        <Outlet />
      </main>
      <footer className="app-footer">
        <span className="footer-brand">
          vbrs. <span>Belarusian-Russian dictionary</span>
        </span>
        <a href="#main-content">
          Back to top <span aria-hidden="true">↑</span>
        </a>
      </footer>
    </div>
  );
}

function App() {
  const location = useLocation();
  const backgroundLocation = (
    location.state as { backgroundLocation?: Location } | null
  )?.backgroundLocation;

  return (
    <>
      <Routes location={backgroundLocation ?? location}>
        <Route element={<Layout />}>
          <Route index element={<SearchPage />} />
          <Route path="articles/:articleId" element={<ArticlePage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
      {backgroundLocation && (
        <Routes>
          <Route path="articles/:articleId" element={<ArticleModal />} />
        </Routes>
      )}
    </>
  );
}

export default App;
