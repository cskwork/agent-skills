import assert from "node:assert/strict";
import test from "node:test";
import { statusFor } from "../src/render";
import type { ControlState } from "../src/types";

function control(state: string, titleSuffix?: string): ControlState {
	return {
		controlId: "session.test",
		kind: "session",
		title: "Test",
		state,
		semantic: state === "running" || state === "needs_attention",
		source: "test",
		gestures: ["tap"],
		...(titleSuffix ? { display: { titleSuffix } } : {}),
	};
}

test("uses configured short status from the daemon", () => {
	assert.equal(statusFor(control("needs_attention", "CHECK")), "CHECK");
});

test("falls back to safe compact labels", () => {
	assert.equal(statusFor(control("running")), "RUN");
	assert.equal(statusFor(control("offline")), "OFF");
});
