"use client";

/** Mouse-tracked glow effect (pair with the `.spotlight` CSS class). */
export function useSpotlight() {
  return (e: React.MouseEvent<HTMLElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    e.currentTarget.style.setProperty("--mx", `${e.clientX - rect.left}px`);
    e.currentTarget.style.setProperty("--my", `${e.clientY - rect.top}px`);
  };
}
