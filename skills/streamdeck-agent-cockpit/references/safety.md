# Safety and privacy

## Local API

- Default bind: `127.0.0.1`.
- Non-loopback binding is rejected by validation unless explicitly overridden for a reviewed use case.
- Bearer token is random, file-backed, and permissioned to the local user.
- Health may be unauthenticated; control/state/report endpoints require authentication.
- Requests have a bounded JSON body size.

## Command execution

- Config stores argv arrays, never untrusted shell strings.
- Runtime uses `shell=False`.
- HTTP requests select only a predeclared control and gesture.
- Requests cannot supply executable paths, argv, cwd, env, or shell fragments.
- Command stdout/stderr is not returned by default.
- Timeouts are bounded.
- Detached execution is explicit.

Avoid `bash -c`, `sh -c`, `cmd /c`, and PowerShell command strings. When a complex workflow is needed, put reviewed logic in a version-controlled script and configure its path plus fixed arguments.

## Secrets

Never store credentials in:

- cockpit JSON;
- Stream Deck action settings;
- launchers;
- icon/title text;
- daemon logs;
- state labels/details;
- test fixtures.

Commands should refer to environment variables, OS keychains, existing authenticated CLIs, or credential files with appropriate permissions.

## Destructive actions

Classify an operation as destructive when accidental invocation can interrupt work, mutate production, publish, merge, deploy, delete, send, charge, or expose data.

Controls invoking such operations require `confirmation: hold` or `confirmation: explicit`. A launcher cannot supply a physical hold event, so do not generate launcher-only destructive controls unless the user consciously chooses an explicit confirmation flow outside Stream Deck.

## Terminal data

Do not scrape pane output for state by default. Terminal output can contain source code, prompts, tokens, customer data, secrets, and misleading text. Use typed event/report adapters.

If the user explicitly approves terminal capture for debugging, make it temporary, minimize the captured range, redact before persistence, and do not reuse it as a production progress signal.

## Profile integrity

Do not edit undocumented Stream Deck profile stores by default. When a user
explicitly requests a change to a user-owned macOS v3 page, use only
`scripts/streamdeck_profile.py`: it verifies the named profile, creates a full
timestamped backup, refuses occupied keys, and changes only the explicit page
manifest. `--replace` is allowed only for an existing built-in **Open** action
or this skill's own `com.cskwork.agent-cockpit.control` action; unrelated and
third-party actions remain protected. Never edit the root profile registry or
unrelated pages/actions.
On uninstall, remove only owned plugin/runtime/profile data.

## Supply chain

Use the official Stream Deck SDK/toolchain and pin resolved dependencies in the generated plugin lockfile. Review any third-party adapter before installation. The core Python runtime intentionally has no external package dependency.
