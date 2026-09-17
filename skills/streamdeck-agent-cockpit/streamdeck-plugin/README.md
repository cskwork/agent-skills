# Agent Cockpit Stream Deck plugin

Buildable official SDK project for the generic
`com.cskwork.agent-cockpit.control` action. Each action instance stores only a
`controlId` plus local daemon connection settings. It polls `cockpitd`, renders
the configured short state (`RUN`, `CHECK`, `OFF`, and so on), and invokes only
the predeclared gesture for that control.

Requires Node.js 24 or newer and Stream Deck 7.1 or newer.

```bash
npm ci
npm test
npm run typecheck
npm run build
npm run validate
python3 ../scripts/install_streamdeck_plugin.py --force
```

The validator may download current Elgato rules. Review its network behavior
before running it in an environment where plugin artifacts must not leave the
machine.
