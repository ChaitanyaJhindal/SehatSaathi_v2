import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

import * as baileysPkg from "@whiskeysockets/baileys";
import pino from "pino";
import QRCode from "qrcode";

const makeWASocket =
  typeof baileysPkg.default === "function"
    ? baileysPkg.default
    : typeof baileysPkg.makeWASocket === "function"
      ? baileysPkg.makeWASocket
      : baileysPkg.default?.default;

const {
  Browsers,
  DisconnectReason,
  fetchLatestBaileysVersion,
  useMultiFileAuthState,
} = baileysPkg;

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.env.WA_BRIDGE_PORT || 2785);
const SESSIONS_ROOT = process.env.WA_SESSIONS_DIR
  ? path.resolve(process.env.WA_SESSIONS_DIR)
  : path.resolve(__dirname, "..", "..", "output", "wa_sessions");

fs.mkdirSync(SESSIONS_ROOT, { recursive: true });

const logger = pino({ level: "silent" });
const sessions = new Map();

process.on("uncaughtException", (err) => {
  console.error("[wa-bridge] uncaughtException:", err?.message || err);
});
process.on("unhandledRejection", (err) => {
  console.error("[wa-bridge] unhandledRejection:", err?.message || err);
});

function sanitizeSessionName(raw) {
  const cleaned = String(raw || "sehatsaathi-main").replace(/[^a-zA-Z0-9_-]/g, "");
  return cleaned || "sehatsaathi-main";
}

function getSessionState(rawName) {
  const name = sanitizeSessionName(rawName);
  if (!sessions.has(name)) {
    sessions.set(name, {
      name,
      status: "not_created",
      phone: null,
      pushName: null,
      qrCode: null,
      lastError: null,
      sock: null,
      manualStop: false,
      reconnectAttempts: 0,
      startingPromise: null,
    });
  }
  return sessions.get(name);
}

function toPublicStatus(state) {
  return {
    gateway_reachable: true,
    configured: true,
    session_id: state.name,
    session_name: state.name,
    status: state.status,
    connected: state.status === "ready",
    phone: state.phone,
    push_name: state.pushName,
    qr_code: state.qrCode,
    last_error: state.lastError,
  };
}

function toBaileysJid(chatId) {
  const raw = String(chatId || "").trim();
  if (raw.endsWith("@c.us")) {
    return `${raw.slice(0, -5)}@s.whatsapp.net`;
  }
  return raw;
}

function authDirFor(name) {
  return path.join(SESSIONS_ROOT, sanitizeSessionName(name));
}

function cleanupAuthDir(name) {
  const dir = authDirFor(name);
  try {
    fs.rmSync(dir, { recursive: true, force: true });
  } catch {
    // ignore cleanup failures
  }
}

async function startSessionSocket(rawName) {
  const state = getSessionState(rawName);
  if (state.status === "ready" && state.sock) {
    return state;
  }
  if (state.startingPromise) {
    return state.startingPromise;
  }

  state.startingPromise = (async () => {
    state.manualStop = false;
    state.lastError = null;
    if (state.status !== "qr_ready") {
      state.status = "initializing";
    }

    const authDir = authDirFor(state.name);
    fs.mkdirSync(authDir, { recursive: true });
    const { state: authState, saveCreds } = await useMultiFileAuthState(authDir);

    let version;
    try {
      const latest = await fetchLatestBaileysVersion();
      version = latest?.version;
    } catch {
      version = undefined;
    }

    const sock = makeWASocket({
      ...(version ? { version } : {}),
      auth: authState,
      logger,
      printQRInTerminal: false,
      browser: Browsers.ubuntu("Chrome"),
      syncFullHistory: false,
      markOnlineOnConnect: false,
    });

    state.sock = sock;

    sock.ev.on("creds.update", saveCreds);

    sock.ev.on("connection.update", async (update) => {
      const { connection, lastDisconnect, qr } = update;

      if (qr) {
        try {
          state.qrCode = await QRCode.toDataURL(qr, { margin: 2, width: 320 });
          state.status = "qr_ready";
          state.lastError = null;
        } catch (err) {
          state.lastError = err?.message || "Failed to render QR code";
        }
      }

      if (connection === "open") {
        state.status = "ready";
        state.qrCode = null;
        state.lastError = null;
        state.reconnectAttempts = 0;
        state.phone = sock.user?.id ? sock.user.id.split(":")[0].split("@")[0] : null;
        state.pushName = sock.user?.name || null;
      }

      if (connection === "close") {
        const statusCode = lastDisconnect?.error?.output?.statusCode;
        const errMessage = lastDisconnect?.error?.message || "Connection closed";

        if (state.sock === sock) {
          state.sock = null;
        }

        if (state.manualStop || statusCode === DisconnectReason.loggedOut) {
          cleanupAuthDir(state.name);
          state.status = "disconnected";
          state.phone = null;
          state.pushName = null;
          state.qrCode = null;
          state.lastError = state.manualStop ? null : "WhatsApp device logged out. Scan QR again.";
          return;
        }

        const canReconnect =
          statusCode === DisconnectReason.restartRequired ||
          state.reconnectAttempts < 5;

        if (canReconnect) {
          state.reconnectAttempts += 1;
          state.status = "initializing";
          setTimeout(() => {
            if (!state.manualStop) {
              startSessionSocket(state.name).catch((e) => {
                state.status = "failed";
                state.lastError = e?.message || "Reconnect failed";
              });
            }
          }, 1200);
        } else {
          state.status = "disconnected";
          state.qrCode = null;
          state.lastError = errMessage;
        }
      }
    });

    return state;
  })();

  try {
    return await state.startingPromise;
  } finally {
    state.startingPromise = null;
  }
}

async function connectAndWait(rawName, timeoutMs = 12000) {
  const state = await startSessionSocket(rawName);
  const deadline = Date.now() + timeoutMs;

  while (Date.now() < deadline) {
    if (state.status === "ready" || (state.status === "qr_ready" && state.qrCode) || state.status === "failed") {
      break;
    }
    await new Promise((r) => setTimeout(r, 400));
  }
  return state;
}

async function logoutSession(rawName) {
  const state = getSessionState(rawName);
  state.manualStop = true;
  const sock = state.sock;
  state.sock = null;
  if (sock) {
    try {
      await sock.logout();
    } catch {
      try {
        sock.end(undefined);
      } catch {
        // ignore close error
      }
    }
  }
  cleanupAuthDir(state.name);
  state.status = "disconnected";
  state.phone = null;
  state.pushName = null;
  state.qrCode = null;
  state.lastError = null;
  state.reconnectAttempts = 0;
  return state;
}

function sendJson(res, statusCode, data) {
  res.writeHead(statusCode, { "Content-Type": "application/json" });
  res.end(JSON.stringify(data));
}

async function readJsonBody(req) {
  const chunks = [];
  for await (const chunk of req) {
    chunks.push(chunk);
  }
  const raw = Buffer.concat(chunks).toString("utf8").trim();
  if (!raw) return {};
  return JSON.parse(raw);
}

const server = http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url || "/", `http://${req.headers.host || "127.0.0.1"}`);
    const pathname = url.pathname;

    if (req.method === "GET" && pathname === "/health") {
      return sendJson(res, 200, { ok: true });
    }

    const match = pathname.match(/^\/sessions\/([^/]+)\/(status|connect|pairing-code|logout|send-document|send-text)$/);
    if (!match) {
      return sendJson(res, 404, { message: "Not found" });
    }

    const sessionName = decodeURIComponent(match[1]);
    const action = match[2];

    if (req.method === "GET" && action === "status") {
      const state = getSessionState(sessionName);
      // If persisted credentials exist on disk and socket isn't loaded yet, wake it in background
      const credsFile = path.join(authDirFor(sessionName), "creds.json");
      if (state.status === "not_created" && fs.existsSync(credsFile)) {
        startSessionSocket(sessionName).catch(() => {});
      }
      return sendJson(res, 200, toPublicStatus(state));
    }

    if (req.method === "POST" && action === "connect") {
      const state = await connectAndWait(sessionName);
      return sendJson(res, 200, toPublicStatus(state));
    }

    if (req.method === "POST" && action === "pairing-code") {
      const body = await readJsonBody(req);
      const digits = String(body.phoneNumber || "").replace(/\D/g, "");
      if (digits.length < 10 || digits.length > 15) {
        return sendJson(res, 400, { message: "Valid phone number with country code is required." });
      }
      const state = await startSessionSocket(sessionName);
      if (state.status === "ready") {
        return sendJson(res, 200, { ...toPublicStatus(state), pairing_code: null });
      }
      // Wait briefly for socket initialization before requesting pairing code
      for (let i = 0; i < 15; i += 1) {
        if (state.sock && (state.status === "qr_ready" || i >= 4)) break;
        await new Promise((r) => setTimeout(r, 400));
      }
      if (!state.sock) {
        return sendJson(res, 503, { message: "WhatsApp socket is not ready yet. Try again." });
      }
      const code = await state.sock.requestPairingCode(digits);
      return sendJson(res, 200, {
        ...toPublicStatus(state),
        pairing_code: code,
        phone_number: digits,
      });
    }

    if (req.method === "POST" && action === "logout") {
      const state = await logoutSession(sessionName);
      return sendJson(res, 200, toPublicStatus(state));
    }

    if (req.method === "POST" && action === "send-document") {
      const state = getSessionState(sessionName);
      if (state.status !== "ready" || !state.sock) {
        return sendJson(res, 409, {
          message: "WhatsApp is not connected. Scan the QR code first.",
        });
      }
      const body = await readJsonBody(req);
      const jid = toBaileysJid(body.chatId);
      if (!jid || !body.base64) {
        return sendJson(res, 400, { message: "chatId and base64 PDF content are required." });
      }
      const buffer = Buffer.from(body.base64, "base64");
      const sent = await state.sock.sendMessage(jid, {
        document: buffer,
        mimetype: body.mimetype || "application/pdf",
        fileName: body.filename || "clinical_report.pdf",
        caption: body.caption || "",
      });
      return sendJson(res, 201, {
        id: sent?.key?.id || null,
        to: jid,
      });
    }

    if (req.method === "POST" && action === "send-text") {
      const state = getSessionState(sessionName);
      if (state.status !== "ready" || !state.sock) {
        return sendJson(res, 409, {
          message: "WhatsApp is not connected. Scan the QR code first.",
        });
      }
      const body = await readJsonBody(req);
      const jid = toBaileysJid(body.chatId);
      if (!jid || !body.text) {
        return sendJson(res, 400, { message: "chatId and text are required." });
      }
      const sent = await state.sock.sendMessage(jid, { text: body.text });
      return sendJson(res, 201, {
        id: sent?.key?.id || null,
        to: jid,
      });
    }

    return sendJson(res, 405, { message: "Method not allowed" });
  } catch (err) {
    console.error("[wa-bridge] request error:", err);
    return sendJson(res, 500, { message: err?.message || "Internal WhatsApp bridge error" });
  }
});

// Auto-restore any saved sessions on boot
try {
  for (const entry of fs.readdirSync(SESSIONS_ROOT, { withFileTypes: true })) {
    if (entry.isDirectory()) {
      const credsFile = path.join(SESSIONS_ROOT, entry.name, "creds.json");
      if (fs.existsSync(credsFile)) {
        startSessionSocket(entry.name).catch(() => {});
      }
    }
  }
} catch {
  // ignore restore scan errors
}

server.listen(PORT, "127.0.0.1", () => {
  console.log(`[wa-bridge] listening on http://127.0.0.1:${PORT}`);
});
