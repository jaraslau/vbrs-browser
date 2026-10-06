import { Link, Outlet, Route, Routes, useLocation } from "react-router-dom";
import type { Location } from "react-router-dom";

import favicon from "./assets/favicon.webp";
import { ArticleModal } from "./components/ArticleModal";
import { ArticlePage } from "./pages/ArticlePage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { SearchPage } from "./pages/SearchPage";

function Layout() {
  const { pathname } = useLocation();

  return (
    <div className={`app${pathname === "/" ? "" : " app--reading"}`}>
      <div className="polar-backdrop" aria-hidden="true" />
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
        <span className="language-pair" aria-label="Belarusian to Russian">
          BE <span aria-hidden="true">—</span> RU
        </span>
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
