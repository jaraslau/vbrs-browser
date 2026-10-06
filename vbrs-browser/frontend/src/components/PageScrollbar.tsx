import { useEffect, useRef, useState } from "react";
import type { CSSProperties } from "react";

const SCROLL_STEPS = 1000;
const MIN_THUMB_SIZE = 32;
const ARROW_SCROLL_DISTANCE = 40;

export function PageScrollbar() {
  const trackRef = useRef<HTMLInputElement>(null);
  const [scroll, setScroll] = useState({
    position: 0,
    thumbSize: MIN_THUMB_SIZE,
    available: false,
  });

  useEffect(() => {
    const update = () => {
      const height = document.documentElement.scrollHeight;
      const maxScroll = Math.max(0, height - window.innerHeight);
      const trackHeight = trackRef.current?.clientHeight ?? 0;
      const next = {
        position:
          maxScroll === 0
            ? 0
            : Math.round(
                Math.min(1, Math.max(0, window.scrollY / maxScroll)) *
                  SCROLL_STEPS,
              ),
        thumbSize: Math.max(
          MIN_THUMB_SIZE,
          (trackHeight * window.innerHeight) / Math.max(1, height),
        ),
        available: maxScroll > 0,
      };
      setScroll((previous) =>
        previous.position === next.position &&
        previous.thumbSize === next.thumbSize &&
        previous.available === next.available
          ? previous
          : next,
      );
    };

    const observer = new ResizeObserver(update);
    observer.observe(document.documentElement);
    observer.observe(document.body);
    if (trackRef.current) observer.observe(trackRef.current);
    window.addEventListener("scroll", update, { passive: true });
    window.addEventListener("resize", update);
    update();
    return () => {
      observer.disconnect();
      window.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
    };
  }, []);

  return (
    <input
      ref={trackRef}
      className="page-scrollbar"
      type="range"
      min={0}
      max={SCROLL_STEPS}
      step={1}
      value={scroll.position}
      hidden={!scroll.available}
      aria-label="Page scroll position"
      aria-orientation="vertical"
      aria-controls="main-content"
      aria-valuetext={`${Math.round((scroll.position / SCROLL_STEPS) * 100)}% of page`}
      style={{ "--thumb-size": `${scroll.thumbSize}px` } as CSSProperties}
      onChange={(event) => {
        const maxScroll =
          document.documentElement.scrollHeight - window.innerHeight;
        window.scrollTo({
          top: (Number(event.target.value) / SCROLL_STEPS) * maxScroll,
          behavior: "instant",
        });
      }}
      onKeyDown={(event) => {
        const maxScroll =
          document.documentElement.scrollHeight - window.innerHeight;
        const destinations: Record<string, number> = {
          Home: 0,
          End: maxScroll,
          ArrowUp: window.scrollY - ARROW_SCROLL_DISTANCE,
          ArrowDown: window.scrollY + ARROW_SCROLL_DISTANCE,
          PageUp: window.scrollY - window.innerHeight,
          PageDown: window.scrollY + window.innerHeight,
        };
        if (event.key in destinations) {
          event.preventDefault();
          window.scrollTo({
            top: Math.max(0, Math.min(maxScroll, destinations[event.key])),
            behavior: "instant",
          });
        }
      }}
    />
  );
}
