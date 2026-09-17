# Sources and design provenance

Primary implementation references:

- Matt Pocock, `writing-great-skills`: https://github.com/mattpocock/skills/tree/main/skills/productivity/writing-great-skills
- Elgato Stream Deck SDK documentation: https://docs.elgato.com/en/sdk/
- Official Stream Deck SDK repository/tooling: https://github.com/elgatosf/streamdeck
- Pi coding-agent RPC documentation: https://github.com/badlogic/pi-mono/blob/main/packages/coding-agent/docs/rpc.md
- JCode documentation: https://jcode.sh/docs

Prior-art references supplied for the original brief:

- `streamdeck-mcp`: https://github.com/verygoodplugins/streamdeck-mcp
- AgentDeck: https://github.com/cskwork/AgentDeck

The last two are inspiration and comparison points only. They are not runtime dependencies, optional Python imports, plugin dependencies, daemon services, or installation prerequisites for this skill.

Always verify current SDK manifests, CLI commands, and agent flags against the versions installed in the target environment before implementation.
