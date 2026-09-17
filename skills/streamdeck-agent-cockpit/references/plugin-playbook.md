# Stream Deck plugin playbook

## When a plugin is justified

Build the plugin only for requirements the launcher path cannot satisfy:

- dynamic title or icon;
- semantic/coarse state display;
- long-press distinction;
- encoder rotation or press;
- Property Inspector configuration;
- visible daemon/auth/error state.

## Scaffold from the installed official SDK

SDK manifests, Node versions, CLI commands, encoder layouts, and TypeScript types can change. Create a fresh plugin with the **currently installed official Stream Deck SDK tooling**, then adapt the reference files under `templates/streamdeck-plugin/`. Do not blindly copy an old manifest or package lock.

Recommended plugin identity:

```text
plugin UUID: com.agentcockpit.streamdeck
action UUID: com.agentcockpit.streamdeck.control
```

Use another reverse-DNS namespace when publishing under an organization.

For this repository's ready-to-build implementation, use
`streamdeck-plugin/` and the owned UUID `com.cskwork.agent-cockpit`. The
`templates/streamdeck-plugin/` directory remains a portable adaptation
reference rather than the install target.

## One generic action

The action settings should stay small:

```json
{
  "controlId": "session.codex.main",
  "daemonUrl": "http://127.0.0.1:39393",
  "tokenFile": "~/.agent-cockpit/token"
}
```

The plugin:

1. reads the local token file in its Node process;
2. fetches the bound control state;
3. renders a compact title/image/encoder feedback;
4. converts SDK input events to canonical gestures;
5. invokes the named control with no raw command text;
6. shows an alert/error state on any non-success response.

Use `control.display.titleSuffix` from the daemon for the short key status. This
keeps configured labels such as `RUN` and `CHECK` authoritative instead of
rendering raw state names such as `RUNNING` or `NEEDS_ATTENTION`.

The Property Inspector edits the action settings. It does not hold the bearer token or execute commands.

## Event mapping

| SDK interaction | Canonical gesture |
|---|---|
| Key up after short press | `tap` |
| Key up after configured threshold | `longPress` |
| Dial press | `dialPress` |
| Negative rotation | `dialLeft` |
| Positive rotation | `dialRight` |

Do not fire both tap and long press for one interaction. Debounce dial events and pass only bounded step values.

## Polling

Start with 1–2 second polling while a key is visible. Stop polling on disappearance. Add WebSocket/SSE only when measured scale or latency justifies the additional lifecycle complexity.

Use one request per visible control per interval only for small decks. For larger layouts, add a batched state endpoint or plugin-side shared cache.

## Rendering

Prefer short stable labels. Render source/staleness as a small cue rather than pretending confidence. Keep full error details in logs or the Property Inspector, not on the key.

Avoid remote icon URLs. Bundle static SVG/PNG assets or generate local data-URI SVGs from sanitized text/state.

## Encoders

Encoder support must start from a current official encoder action scaffold because required layouts and feedback contracts vary by SDK release. Keep the same `controlId` and daemon gesture API; only the Stream Deck presentation layer changes.

## Third-party plugin boundary

One Stream Deck plugin should not pretend it can enumerate, configure, or invoke arbitrary unrelated plugin actions. For a third-party integration, choose one of these supported paths:

1. The user combines Agent Cockpit and the third-party action in a Stream Deck Multi Action.
2. Agent Cockpit calls the underlying application/service through its documented local API or CLI.
3. The third-party plugin exposes and documents an inter-plugin protocol.

Otherwise keep the actions separate. Do not read another plugin's private settings or patch its action data.

## Profile handling

Safe options:

- user manually places generic actions;
- ship a profile created through supported Stream Deck tooling and clearly owned by this plugin;
- provide a control map and icon set for manual placement.

Unsafe option:

- editing undocumented profile files/databases to insert or rewrite arbitrary actions.

If a user reviews that trade-off and still directs you to place keys for them,
say plainly that it is unsupported, back up the whole `.sdProfile` directory
first, and know what actually bites:

- **Quit the application before writing.** A running Stream Deck holds the
  profile in memory and overwrites the file on exit.
- **A page is only reachable if its id is in the top-level `Pages.Pages`
  array.** `Pages.Default` can point at a page that is not in that array;
  writing actions there renders nothing on the device and the application
  silently reverts `Pages.Current` on next launch. Append the id to the array to
  make it a real page.
- Verify after relaunch by reading the file back. Do not infer success from the
  write succeeding.

## Known drift and failure modes

`streamdeck create` is an interactive wizard with no flags, so it cannot be run
unattended. Hand-authoring the `.sdPlugin` directory is acceptable as long as
`streamdeck validate` still gates every build — it downloads current rules and
catches manifest drift that a hand-written file will otherwise carry silently.

Observed against `@elgato/streamdeck` 2.x, all of which the template predates:

- `LogLevel` is no longer re-exported from the package root, and `streamDeck` is
  a named export.
- Action settings interfaces must satisfy `JsonObject`, so they need an index
  signature.
- The action decorator is TC39 standard, not legacy. Keep `experimentalDecorators`
  off or the type checker reports that the decorator expects two arguments.
- `Actions[].States[].FontSize` must be a number; a string fails validation.

Bundling a CommonJS dependency into ESM output makes esbuild's `require` shim
throw `Dynamic require of "events" is not supported`. The application surfaces
only `Process stopped (unexpected): code=0x00000001` on a ten-second restart
loop, so **run the built bundle directly under `node` to see the real stack** —
the application log never shows it. Add a `createRequire` banner, or emit CJS.

### Verify that a reload actually happened

`streamdeck restart` and `streamdeck stop` report success even when the plugin
process is untouched. Continued daemon polling is *not* evidence of a reload;
the previous process is still running and still polling. Confirm reload by a
fresh `Plugin connected` entry in the application log with a newer timestamp,
and fall back to quitting and relaunching the Stream Deck application when the
timestamp does not move. Never tell a user to re-check the hardware without
confirming the new code is live.

### Text is drawn twice

If the action both renders text into its image and calls `setTitle`, the
application draws the title on top of the image and the key reads as doubled.
Pick one. When the image owns the text, clear the title explicitly — a title set
by an earlier build persists in the application's runtime state — and set
`ShowTitle` to false on the action's states.

Size the text to the key rather than truncating: shrink the font when a label
would overflow, and prefer the short status words already defined in the config's
`appearance.states[*].titleSuffix` over raw state identifiers. `NEEDS ATTENTION`
does not fit a 72 px key; `CHECK` does.

## Build gate

Before packaging:

- formatter/linter pass;
- TypeScript check pass;
- tests pass;
- production bundle pass;
- official SDK validation pass;
- install/uninstall tested;
- daemon-down, bad-token, and unknown-control states tested;
- actual key and encoder behavior tested on target hardware.
