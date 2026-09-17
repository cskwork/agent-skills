export type EvidenceTier = "reported" | "coarse" | "unknown";

export interface AgentCockpitSettings {
	[key: string]: string | number | undefined;
	controlId?: string;
	daemonUrl?: string;
	tokenFile?: string;
	holdMs?: number;
	pollMs?: number;
}

export interface SessionState {
	state: string;
	semantic: boolean;
	evidenceTier: EvidenceTier;
	source: string;
	label?: string;
	detail?: string;
	progress?: number;
	reportedAt?: number;
	expiresAt?: number;
	lastReportStale?: boolean;
}

export interface ControlState {
	controlId: string;
	kind: "session" | "command";
	title: string;
	state: string;
	semantic: boolean;
	source: string;
	gestures: string[];
	session?: SessionState;
	display?: {
		titleSuffix?: string;
	};
}

export interface ApiEnvelope<T> {
	ok: boolean;
	control?: T;
	error?: { code: string; message: string };
}
