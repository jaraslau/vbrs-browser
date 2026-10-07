import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";

import { ArticlePage } from "../pages/ArticlePage";

export function ArticleModal() {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const backdropPressed = useRef(false);
  const navigate = useNavigate();

  useEffect(() => {
    const dialog = dialogRef.current;
    const previousFocus = document.activeElement;
    dialog?.showModal();
    return () => {
      dialog?.close();
      if (previousFocus instanceof HTMLElement) {
        // Returning focus after the modal closes is a navigation gesture,
        // not a keyboard traversal, so suppress the focus-visible ring that
        // would otherwise frame the full-width result row while focus rests
        // on it. Focus is still returned for keyboard and screen-reader
        // continuity; the marker is cleared on blur so real keyboard
        // traversal from there on shows normal focus rings.
        previousFocus.setAttribute("data-focus-restored", "");
        previousFocus.addEventListener(
          "blur",
          () => {
            previousFocus.removeAttribute("data-focus-restored");
          },
          { once: true },
        );
        previousFocus.focus({ preventScroll: true });
      }
    };
  }, []);

  const dismiss = () => navigate(-1);

  return (
    <dialog
      ref={dialogRef}
      className="article-modal"
      aria-label="Dictionary article"
      onCancel={(event) => {
        event.preventDefault();
        dismiss();
      }}
      onPointerDown={(event) => {
        backdropPressed.current = event.target === event.currentTarget;
      }}
      onClick={(event) => {
        if (backdropPressed.current && event.target === event.currentTarget) {
          dismiss();
        }
      }}
    >
      <div className="article-modal-panel">
        <button
          className="article-modal-close"
          type="button"
          onClick={dismiss}
          aria-label="Close article"
        >
          <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="m6 6 12 12M6 18 18 6" />
          </svg>
        </button>
        <div className="article-modal-content">
          <ArticlePage embedded />
        </div>
      </div>
    </dialog>
  );
}
