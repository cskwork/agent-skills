import streamDeck from "@elgato/streamdeck";

import { AgentCockpitAction } from "./actions/agent-cockpit-action";

streamDeck.actions.registerAction(new AgentCockpitAction());

streamDeck.connect();
