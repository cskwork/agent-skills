import type { ControlState } from "./types";

const SHORT_STATUS: Record<string, string> = {
	idle: "IDLE",
	running: "RUN",
	needs_attention: "CHECK",
	blocked: "BLOCKED",
	succeeded: "DONE",
	failed: "FAILED",
	present: "PRESENT",
	offline: "OFF",
	unavailable: "NO LINK",
	unknown: "UNKNOWN",
	available: "READY",
};

const STATE_COLOR: Record<string, string> = {
	idle: "#334155",
	running: "#1565c0",
	needs_attention: "#d97706",
	blocked: "#c2410c",
	succeeded: "#15803d",
	failed: "#b91c1c",
	present: "#0f766e",
	offline: "#374151",
	unavailable: "#4b5563",
	unknown: "#374151",
	available: "#1d4ed8",
};

function escapeXml(value: string): string {
	return value.replace(/[&<>"']/g, (character) => ({
		"&": "&amp;",
		"<": "&lt;",
		">": "&gt;",
		'"': "&quot;",
		"'": "&apos;",
	})[character] || character);
}

function compact(value: string, max: number): string {
	return value.length <= max ? value : `${value.slice(0, max - 1)}…`;
}

function stateValue(control: ControlState): string {
	return control.session?.state || control.state || "unknown";
}

export function statusFor(control: ControlState): string {
	const configured = control.display?.titleSuffix?.trim();
	return compact(configured || SHORT_STATUS[stateValue(control)] || stateValue(control).toUpperCase(), 10);
}

function sourceFor(control: ControlState): string {
	if (control.session?.evidenceTier === "reported") return "HOOK";
	return compact((control.source || "LOCAL").toUpperCase(), 9);
}

export function imageFor(control: ControlState): string {
	const state = stateValue(control);
	const title = escapeXml(compact(control.title || control.controlId, 15));
	const status = escapeXml(statusFor(control));
	const source = escapeXml(sourceFor(control));
	const color = STATE_COLOR[state] || STATE_COLOR.unknown;
	const statusSize = status.length > 7 ? 22 : 30;
	const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 144 144">
		<rect width="144" height="144" rx="18" fill="${color}"/>
		<text x="72" y="42" text-anchor="middle" font-family="-apple-system,system-ui,sans-serif" font-size="15" font-weight="600" fill="#ffffff">${title}</text>
		<text x="72" y="88" text-anchor="middle" font-family="-apple-system,system-ui,sans-serif" font-size="${statusSize}" font-weight="800" fill="#ffffff">${status}</text>
		<text x="72" y="119" text-anchor="middle" font-family="-apple-system,system-ui,sans-serif" font-size="10" font-weight="600" fill="#ffffff" opacity="0.78">${source}</text>
	</svg>`;
	return `data:image/svg+xml;charset=utf8,${encodeURIComponent(svg)}`;
}

export function errorImage(message: string): string {
	const detail = escapeXml(compact(message, 17));
	const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 144 144">
		<rect width="144" height="144" rx="18" fill="#4b5563"/>
		<text x="72" y="64" text-anchor="middle" font-family="-apple-system,system-ui,sans-serif" font-size="24" font-weight="800" fill="#ffffff">NO LINK</text>
		<text x="72" y="91" text-anchor="middle" font-family="-apple-system,system-ui,sans-serif" font-size="10" fill="#ffffff" opacity="0.78">${detail}</text>
	</svg>`;
	return `data:image/svg+xml;charset=utf8,${encodeURIComponent(svg)}`;
}
