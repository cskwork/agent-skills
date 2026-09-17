/* Standard Property Inspector WebSocket bridge; align with current SDK scaffold. */
let websocket;
let context;
let settings = {};

const fields = ["controlId", "daemonUrl", "tokenFile", "holdMs", "pollMs"];

function send(event, payload) {
  if (!websocket || websocket.readyState !== WebSocket.OPEN) return;
  websocket.send(JSON.stringify({ event, context, payload }));
}

function persist() {
  settings = {
    ...settings,
    controlId: document.getElementById("controlId").value.trim(),
    daemonUrl: document.getElementById("daemonUrl").value.trim(),
    tokenFile: document.getElementById("tokenFile").value.trim(),
    holdMs: Number(document.getElementById("holdMs").value || 650),
    pollMs: Number(document.getElementById("pollMs").value || 1500),
  };
  send("setSettings", settings);
}

function hydrate() {
  for (const id of fields) {
    if (settings[id] !== undefined && settings[id] !== null) {
      document.getElementById(id).value = settings[id];
    }
    document.getElementById(id).addEventListener("change", persist);
  }
}

window.connectElgatoStreamDeckSocket = function connectElgatoStreamDeckSocket(
  port,
  uuid,
  registerEvent,
  info,
  actionInfo,
) {
  context = uuid;
  try {
    settings = JSON.parse(actionInfo)?.payload?.settings || {};
  } catch {
    settings = {};
  }
  websocket = new WebSocket(`ws://127.0.0.1:${port}`);
  websocket.addEventListener("open", () => {
    websocket.send(JSON.stringify({ event: registerEvent, uuid }));
    hydrate();
  });
};
