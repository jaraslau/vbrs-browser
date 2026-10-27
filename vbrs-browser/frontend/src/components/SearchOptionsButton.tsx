import { useEffect, useRef, useState } from "react";

import type { SearchOptions } from "../lib/searchOptions";

const SPELLING_RULES = [
  {
    key: "latinI",
    label: "i (English) → і",
    hint: "After a Cyrillic character: сi → сі, СI → СІ.",
  },
  {
    key: "cyrillicI",
    label: "и → і",
    hint: "Replace Cyrillic и and И with і and І.",
  },
  {
    key: "shortU",
    label: "[аоуеюё]у → [аоуеюё]ў",
    hint: "After these vowels: ау → аў, АУ → АЎ.",
  },
] satisfies { key: keyof SearchOptions; label: string; hint: string }[];

interface SearchOptionsProps {
  options: SearchOptions;
  onChange: (options: SearchOptions) => void;
}

function SearchOptionsModal({
  options,
  onChange,
  onClose,
}: SearchOptionsProps & { onClose: () => void }) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const backdropPressed = useRef(false);

  useEffect(() => {
    const dialog = dialogRef.current;
    const previousFocus = document.activeElement;
    dialog?.showModal();
    return () => {
      dialog?.close();
      if (previousFocus instanceof HTMLElement) {
        previousFocus.focus({ preventScroll: true });
      }
    };
  }, []);

  return (
    <dialog
      id="search-options-dialog"
      ref={dialogRef}
      className="search-options-modal"
      aria-labelledby="search-options-title"
      aria-describedby="search-options-description"
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onPointerDown={(event) => {
        backdropPressed.current = event.target === event.currentTarget;
      }}
      onClick={(event) => {
        if (backdropPressed.current && event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <div className="search-options-panel">
        <button
          className="search-options-close"
          type="button"
          onClick={onClose}
          aria-label="Close search options"
        >
          <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="m6 6 12 12M6 18 18 6" />
          </svg>
        </button>
        <h2 id="search-options-title">Search options</h2>
        <p id="search-options-description">
          Adjust spelling for searches and live suggestions. Your typed text
          stays as entered. Changes apply immediately and are saved in this
          browser.
        </p>
        <fieldset className="search-options-rules">
          <legend className="sr-only">Spelling rules</legend>
          {SPELLING_RULES.map((rule) => (
            <label className="search-option" key={rule.key}>
              <input
                type="checkbox"
                checked={options[rule.key]}
                aria-labelledby={`search-option-${rule.key}-label`}
                aria-describedby={`search-option-${rule.key}-hint`}
                onChange={(event) =>
                  onChange({
                    ...options,
                    [rule.key]: event.currentTarget.checked,
                  })
                }
              />
              <span>
                <span
                  className="search-option-label"
                  id={`search-option-${rule.key}-label`}
                >
                  {rule.label}
                </span>
                <small id={`search-option-${rule.key}-hint`}>{rule.hint}</small>
              </span>
            </label>
          ))}
        </fieldset>
      </div>
    </dialog>
  );
}

export function SearchOptionsButton(props: SearchOptionsProps) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button
        className="header-icon"
        type="button"
        aria-label="Search options"
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-controls={open ? "search-options-dialog" : undefined}
        onClick={() => setOpen(true)}
      >
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <circle cx="12" cy="12" r="10" />
          <circle cx="12" cy="7" r="1.4" fill="currentColor" stroke="none" />
          <path d="m6.5 10 5.5 1 5.5-1M12 11v4m0 0-3 4m3-4 3 4" />
        </svg>
      </button>
      {open && <SearchOptionsModal {...props} onClose={() => setOpen(false)} />}
    </>
  );
}
