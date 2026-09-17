# Stream Deck plugin adaptation template

This directory is a **source adaptation template**, not a prebuilt plugin and not a frozen SDK scaffold. Stream Deck SDK manifests, Node runtimes, CLI commands, encoder layouts, and event types can change. Generate a fresh project with the official SDK tooling installed on the target machine, then apply these files to that scaffold.

## Goal

Create one generic local action:

```text
com.agentcockpit.streamdeck.control
```

Each action instance stores:

```json
{
  "controlId": "session.codex.main",
  "daemonUrl": "http://127.0.0.1:39393",
  "tokenFile": "~/.agent-cockpit/token",
  "holdMs": 650,
  "pollMs": 1500
}
```

The action reads the token in the Node plugin process, not in the Property Inspector. It polls one named control and sends canonical gestures to the local daemon. It does not execute terminal commands itself.

## Apply to a current SDK scaffold

1. Install/update the official Stream Deck SDK CLI according to Elgato's current documentation.
2. Generate a TypeScript plugin project and a keypad action.
3. Use the plugin/action UUIDs from `manifest.action.fragment.json`, adjusted to your organization namespace if needed.
4. Copy/adapt:
   - `src/api.ts`
   - `src/render.ts`
   - `src/agent-cockpit-action.ts`
   - `src/types.ts`
   - `ui/property-inspector.html`
   - `ui/property-inspector.js`
5. Register `AgentCockpitAction` from the scaffold's plugin entry point, then call `streamDeck.connect()`.
6. Format, lint, type-check, test, build, and validate with the installed official SDK.
7. Install locally and verify daemon-down, bad-token, unknown-control, short press, and long press behavior.

The TypeScript uses the modern `@elgato/streamdeck` action-class shape as a reference. Align exact event imports and action APIs with the newly generated scaffold rather than weakening type checks.

## Encoder support

Create an encoder action from the current official scaffold because encoder layouts/feedback contracts are SDK-version-sensitive. Reuse `AgentCockpitApi` and map:

```text
dial down/up -> dialPress or a press-duration policy
dial rotate < 0 -> dialLeft
dial rotate > 0 -> dialRight
```

Send a bounded integer `value`; the daemon exposes it as `AGENT_COCKPIT_VALUE` only to the configured command. Do not convert it into raw argv.

## Property Inspector

The included inspector edits only non-secret settings. It deliberately does not read the token file or call the daemon. The Node action owns authenticated daemon communication.

## Profile placement

Place the action manually through the Stream Deck application or ship a profile created through supported tooling and owned by this plugin. Never patch internal profile databases.
