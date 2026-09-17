/*
 * Adapt exact imports/event signatures to the current official SDK scaffold.
 * Keep strict typing enabled; do not weaken types merely to copy this file.
 */
import streamDeck, {
  action,
  DidReceiveSettingsEvent,
  KeyDownEvent,
  KeyUpEvent,
  SingletonAction,
  WillAppearEvent,
  WillDisappearEvent,
} from "@elgato/streamdeck";
import { AgentCockpitApi } from "./api.js";
import { errorImage, imageFor } from "./render.js";
import type { AgentCockpitSettings } from "./types.js";

const DEFAULT_HOLD_MS = 650;
const DEFAULT_POLL_MS = 1500;

@action({ UUID: "com.agentcockpit.streamdeck.control" })
export class AgentCockpitAction extends SingletonAction<AgentCockpitSettings> {
  private readonly pollers = new Map<string, ReturnType<typeof setInterval>>();
  private readonly pressedAt = new Map<string, number>();

  override async onWillAppear(event: WillAppearEvent<AgentCockpitSettings>): Promise<void> {
    await this.refresh(event.action, event.payload.settings);
    this.startPolling(event.action.id, event.action, event.payload.settings);
  }

  override onWillDisappear(event: WillDisappearEvent<AgentCockpitSettings>): void {
    this.stopPolling(event.action.id);
    this.pressedAt.delete(event.action.id);
  }

  override async onDidReceiveSettings(event: DidReceiveSettingsEvent<AgentCockpitSettings>): Promise<void> {
    this.stopPolling(event.action.id);
    await this.refresh(event.action, event.payload.settings);
    this.startPolling(event.action.id, event.action, event.payload.settings);
  }

  override onKeyDown(event: KeyDownEvent<AgentCockpitSettings>): void {
    this.pressedAt.set(event.action.id, Date.now());
  }

  override async onKeyUp(event: KeyUpEvent<AgentCockpitSettings>): Promise<void> {
    const settings = event.payload.settings;
    const controlId = settings.controlId?.trim();
    if (!controlId) {
      await event.action.showAlert();
      return;
    }
    const started = this.pressedAt.get(event.action.id) ?? Date.now();
    this.pressedAt.delete(event.action.id);
    const holdMs = Math.max(350, Math.min(3000, Number(settings.holdMs || DEFAULT_HOLD_MS)));
    const isHold = Date.now() - started >= holdMs;
    try {
      await new AgentCockpitApi(settings).invoke(controlId, isHold ? "longPress" : "tap", {
        confirmed: isHold,
      });
      await this.refresh(event.action, settings);
    } catch (error) {
      streamDeck.logger.error("Agent Cockpit invocation failed", error);
      await event.action.showAlert();
      await event.action.setImage(errorImage(error instanceof Error ? error.message : "request failed"));
    }
  }

  private startPolling(
    context: string,
    actionInstance: WillAppearEvent<AgentCockpitSettings>["action"],
    settings: AgentCockpitSettings,
  ): void {
    this.stopPolling(context);
    const pollMs = Math.max(500, Math.min(10000, Number(settings.pollMs || DEFAULT_POLL_MS)));
    const poller = setInterval(() => {
      void this.refresh(actionInstance, settings);
    }, pollMs);
    this.pollers.set(context, poller);
  }

  private stopPolling(context: string): void {
    const poller = this.pollers.get(context);
    if (poller) clearInterval(poller);
    this.pollers.delete(context);
  }

  private async refresh(
    actionInstance: WillAppearEvent<AgentCockpitSettings>["action"],
    settings: AgentCockpitSettings,
  ): Promise<void> {
    const controlId = settings.controlId?.trim();
    if (!controlId) {
      await actionInstance.setTitle("");
      await actionInstance.setImage(errorImage("controlId missing"));
      return;
    }
    try {
      const state = await new AgentCockpitApi(settings).control(controlId);
      await actionInstance.setTitle("");
      await actionInstance.setImage(imageFor(state));
    } catch (error) {
      streamDeck.logger.warn("Agent Cockpit refresh failed", error);
      await actionInstance.setTitle("");
      await actionInstance.setImage(errorImage(error instanceof Error ? error.message : "request failed"));
    }
  }
}
