export const COMPACT_VIEWPORT_QUERY = '(max-width: 1199px)'

export function observeCompactViewport(onChange, windowRef = window) {
  const mediaQuery = windowRef.matchMedia(COMPACT_VIEWPORT_QUERY)
  const listener = (event) => onChange(event.matches)

  onChange(mediaQuery.matches)
  mediaQuery.addEventListener('change', listener)

  return () => mediaQuery.removeEventListener('change', listener)
}
