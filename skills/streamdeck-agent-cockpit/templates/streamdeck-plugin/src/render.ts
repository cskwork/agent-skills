import type { ControlState } from "./types.js";

function escapeXml(value: string): string {
  return value.replace(/[&<>"']/g, (character) => {
    const entities: Record<string, string> = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&apos;",
    };
    return entities[character];
  });
}

function compact(value: string, max = 14): string {
  return value.length <= max ? value : `${value.slice(0, max - 1)}…`;
}

export function titleFor(state: ControlState): string {
  const label = compact(state.title || state.controlId, 16);
  const status = compact(
    state.display?.titleSuffix || (state.session?.state || state.state || "unknown").toUpperCase(),
    12,
  );
  return `${label}\n${status}`;
}

export function imageFor(state: ControlState): string {
  const status = state.session?.state || state.state || "unknown";
  const source = state.session?.evidenceTier || (state.semantic ? "reported" : "coarse");
  const title = escapeXml(compact(state.title || state.controlId, 14));
  const statusText = escapeXml(compact(state.display?.titleSuffix || status.toUpperCase(), 12));
  const sourceText = escapeXml(compact(source, 10));
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 144 144">
      <rect width="144" height="144" rx="18" fill="#15171a"/>
      <text x="72" y="58" text-anchor="middle" font-family="system-ui, sans-serif" font-size="18" fill="white">${title}</text>
      <text x="72" y="88" text-anchor="middle" font-family="system-ui, sans-serif" font-size="16" font-weight="700" fill="white">${statusText}</text>
      <text x="72" y="114" text-anchor="middle" font-family="system-ui, sans-serif" font-size="11" fill="#b7bdc8">${sourceText}</text>
    </svg>`;
  return `data:image/svg+xml;charset=utf8,${encodeURIComponent(svg)}`;
}

export function errorImage(message: string): string {
  const text = escapeXml(compact(message, 18));
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 144 144">
    <rect width="144" height="144" rx="18" fill="#202226"/>
    <text x="72" y="62" text-anchor="middle" font-family="system-ui, sans-serif" font-size="18" font-weight="700" fill="white">NO LINK</text>
    <text x="72" y="91" text-anchor="middle" font-family="system-ui, sans-serif" font-size="11" fill="#c5cad3">${text}</text>
  </svg>`;
  return `data:image/svg+xml;charset=utf8,${encodeURIComponent(svg)}`;
}
