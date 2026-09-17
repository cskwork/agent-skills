import { readFile } from "node:fs/promises";
import { homedir } from "node:os";
import { resolve } from "node:path";
import type { AgentCockpitSettings, ApiEnvelope, ControlState } from "./types.js";

const DEFAULT_URL = "http://127.0.0.1:39393";
const DEFAULT_TOKEN_FILE = "~/.agent-cockpit/token";

function expandHome(path: string): string {
  if (path === "~") return homedir();
  if (path.startsWith("~/")) return resolve(homedir(), path.slice(2));
  return path;
}

export class AgentCockpitApi {
  private readonly baseUrl: string;
  private readonly tokenFile: string;

  constructor(settings: AgentCockpitSettings) {
    this.baseUrl = (settings.daemonUrl || DEFAULT_URL).replace(/\/$/, "");
    this.tokenFile = expandHome(settings.tokenFile || DEFAULT_TOKEN_FILE);
  }

  private async token(): Promise<string> {
    const token = (await readFile(this.tokenFile, "utf8")).trim();
    if (token.length < 24) throw new Error("Agent Cockpit token file is empty or invalid");
    return token;
  }

  private async request<T>(path: string, init?: RequestInit): Promise<T> {
    const token = await this.token();
    const response = await fetch(`${this.baseUrl}${path}`, {
      ...init,
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${token}`,
        ...(init?.body ? { "Content-Type": "application/json" } : {}),
        ...(init?.headers || {}),
      },
      signal: AbortSignal.timeout(4000),
    });
    const body = (await response.json()) as ApiEnvelope<T>;
    if (!response.ok || !body.ok) {
      throw new Error(body.error?.message || `Agent Cockpit request failed (${response.status})`);
    }
    return (body.control ?? body) as T;
  }

  async control(controlId: string): Promise<ControlState> {
    return this.request<ControlState>(`/v1/controls/${encodeURIComponent(controlId)}`);
  }

  async invoke(
    controlId: string,
    gesture: "tap" | "longPress" | "dialPress" | "dialLeft" | "dialRight",
    options: { confirmed?: boolean; value?: number } = {},
  ): Promise<void> {
    await this.request(`/v1/controls/${encodeURIComponent(controlId)}/invoke`, {
      method: "POST",
      body: JSON.stringify({
        gesture,
        confirmed: Boolean(options.confirmed),
        value: Math.max(-100, Math.min(100, Math.trunc(options.value || 0))),
      }),
    });
  }
}
