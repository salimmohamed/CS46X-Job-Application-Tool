// background.js - service worker for the job application tracker extension
// MV3 service workers can get killed at any time, so nothing is stored
// in global variables. Everything goes through chrome.storage instead.

// default structure for a fresh session
const DEFAULT_SESSION = {
  user: null,
  applications: [],
  settings: {
    autofillEnabled: true,
    notificationsEnabled: true,
  },
  lastInitialized: null,
};

// quick wrappers so I don't have to type chrome.storage._____ everywhere
function getLocal(keys) {
  return chrome.storage.local.get(keys);
}

function setLocal(data) {
  return chrome.storage.local.set(data);
}

function getSession(keys) {
  return chrome.storage.session.get(keys);
}

function setSession(data) {
  return chrome.storage.session.set(data);
}

// ============================================================
// URL-Based Pre-fetching (Issue #37)
// ============================================================

const JOB_BOARD_PATTERNS = [
  { name: 'linkedin',   pattern: /linkedin\.com\/jobs/i },
  { name: 'indeed',     pattern: /indeed\.com/i },
  { name: 'workday',    pattern: /myworkdayjobs\.com/i },
  { name: 'greenhouse', pattern: /greenhouse\.io/i },
  { name: 'lever',      pattern: /jobs\.lever\.co/i },
];

function detectJobBoard(url) {
  if (!url) return null;
  for (const board of JOB_BOARD_PATTERNS) {
    if (board.pattern.test(url)) return board.name;
  }
  return null;
}

async function prefetchProfileForJobBoard(tabId, url) {
  const board = detectJobBoard(url);
  if (!board) return;

  const { session } = await getLocal(['session']);
  const profile = session?.user ?? null;

  if (!profile) {
    console.log(`[background] Pre-fetch skipped for ${board} - no user profile stored`);
    return;
  }

  await setSession({
    prefetchedProfile: {
      board,
      profile,
      fetchedAt: new Date().toISOString(),
    },
  });

  console.log(`[background] Profile pre-fetched for ${board} (tab ${tabId})`);
}

// changeInfo.url is only present when the URL itself changes, which is exactly
// when we want to kick off a pre-fetch rather than on every load event.
chrome.tabs.onUpdated.addListener((tabId, changeInfo, _tab) => {
  const url = changeInfo.url;
  if (!url) return;
  prefetchProfileForJobBoard(tabId, url).catch((err) => {
    console.error('[background] prefetchProfileForJobBoard error:', err);
  });
});

// ============================================================
// Session Heartbeat (Issue #37)
// ============================================================

const HEARTBEAT_ALARM_NAME = 'SESSION_HEARTBEAT';
const HEARTBEAT_INTERVAL_MINUTES = 3;
// attempt a refresh if the token expires within this window
const SESSION_EXPIRY_BUFFER_MS = 5 * 60 * 1000;

async function initializeHeartbeatAlarm() {
  const existing = await chrome.alarms.get(HEARTBEAT_ALARM_NAME);
  if (existing) return;
  chrome.alarms.create(HEARTBEAT_ALARM_NAME, {
    delayInMinutes: HEARTBEAT_INTERVAL_MINUTES,
    periodInMinutes: HEARTBEAT_INTERVAL_MINUTES,
  });
  console.log(`[background] Heartbeat alarm registered - interval: ${HEARTBEAT_INTERVAL_MINUTES}min`);
}

async function attemptTokenRefresh(user) {
  try {
    // replace this block with a real fetch() to your auth refresh endpoint:
    // const res = await fetch('http://localhost:8000/api/auth/refresh', {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify({ refreshToken: user.refreshToken }),
    // });
    console.log('[background] Token refresh attempted for:', user.email ?? 'unknown');
    await logError({
      source: 'heartbeat',
      message: 'Token refresh triggered - session was near expiry',
      context: { email: user.email, tokenExpiresAt: user.tokenExpiresAt },
    });
  } catch (err) {
    console.error('[background] Token refresh failed:', err);
    await logError({ source: 'heartbeat', message: err.message, stack: err.stack });
  }
}

async function runHeartbeat() {
  console.log('[background] Heartbeat tick');

  const { session } = await getLocal(['session']);
  const user = session?.user ?? null;

  if (!user) {
    console.log('[background] Heartbeat - no authenticated user, skipping auth check');
    await setSession({ lastHeartbeat: new Date().toISOString() });
    return;
  }

  const tokenExpiry = user.tokenExpiresAt ? new Date(user.tokenExpiresAt).getTime() : null;
  const now = Date.now();

  if (tokenExpiry !== null && tokenExpiry - now < SESSION_EXPIRY_BUFFER_MS) {
    console.warn('[background] Heartbeat - session nearing expiry, attempting refresh');
    await attemptTokenRefresh(user);
  } else {
    console.log('[background] Heartbeat - session healthy');
  }

  await setSession({ lastHeartbeat: new Date().toISOString() });
}

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === HEARTBEAT_ALARM_NAME) {
    runHeartbeat().catch((err) => {
      console.error('[background] Heartbeat error:', err);
    });
  }
});

// ============================================================
// Centralized Error Logging (Issue #37)
// ============================================================

const MAX_ERROR_LOG_SIZE = 50;

async function logError({ source = 'unknown', message = '', stack = null, context = null }) {
  const { errorLog = [] } = await getLocal(['errorLog']);

  const entry = {
    id: crypto.randomUUID(),
    timestamp: new Date().toISOString(),
    source,
    message,
    stack,
    context,
  };

  // newest entries at the front; cap the log so storage doesn't grow unbounded
  const updated = [entry, ...errorLog].slice(0, MAX_ERROR_LOG_SIZE);
  await setLocal({ errorLog: updated });

  console.warn(`[background] Error logged from "${source}":`, message);
  return entry;
}

// ============================================================
// Core lifecycle
// ============================================================

// sets up storage with defaults if nothing exists yet.
// if there's already data saved, it keeps it and just fills in any missing fields.
async function initializeDefaultSession() {
  const existing = await getLocal(['session']);
  const session = existing.session || {};

  const merged = {
    user: session.user ?? DEFAULT_SESSION.user,
    applications: session.applications ?? DEFAULT_SESSION.applications,
    settings: {
      ...DEFAULT_SESSION.settings,
      ...(session.settings || {}),
    },
    lastInitialized: new Date().toISOString(),
  };

  await setLocal({ session: merged });

  // let the popup know the worker is running
  await setSession({ workerAlive: true });

  await initializeHeartbeatAlarm();

  console.log('[background] Session initialized:', merged);
  return merged;
}

// runs when the extension is first installed or updated
chrome.runtime.onInstalled.addListener(async (details) => {
  console.log(`[background] onInstalled - reason: ${details.reason}`);
  await initializeDefaultSession();
});

// runs every time the browser starts up
chrome.runtime.onStartup.addListener(async () => {
  console.log('[background] onStartup - browser launched');
  await initializeDefaultSession();
});

// main message listener - the popup and content scripts send messages here
// and this routes them to the right handler
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  const { action, payload } = message;

  console.log(`[background] Message received - action: ${action}`, payload);

  // need to return true here so the response channel stays open while
  // the async stuff finishes
  handleMessage(action, payload, sender)
    .then((result) => sendResponse({ success: true, data: result }))
    .catch((err) => {
      console.error(`[background] Error handling "${action}":`, err);
      sendResponse({ success: false, error: err.message });
    });

  return true;
});

// routes each action to the right logic. every case pulls fresh data
// from storage so we don't rely on stale globals.
async function handleMessage(action, payload, _sender) {
  switch (action) {

    case 'SAVE_SESSION': {
      const { session: current } = await getLocal(['session']);
      const updated = { ...current, ...payload };
      await setLocal({ session: updated });
      return updated;
    }

    case 'GET_SESSION': {
      const { session } = await getLocal(['session']);
      return session ?? DEFAULT_SESSION;
    }

    case 'GET_USER_DATA': {
      const { session } = await getLocal(['session']);
      return session?.user ?? null;
    }

    case 'SET_USER_DATA': {
      const { session } = await getLocal(['session']);
      session.user = { ...session.user, ...payload };
      await setLocal({ session });
      return session.user;
    }

    case 'ADD_APPLICATION': {
      const { session } = await getLocal(['session']);
      const app = {
        id: crypto.randomUUID(),
        ...payload,
        appliedAt: new Date().toISOString(),
      };
      session.applications = [...(session.applications || []), app];
      await setLocal({ session });
      return app;
    }

    case 'GET_APPLICATIONS': {
      const { session } = await getLocal(['session']);
      return session?.applications ?? [];
    }

    case 'UPDATE_APPLICATION': {
      const { session } = await getLocal(['session']);
      const idx = session.applications.findIndex((a) => a.id === payload.id);
      if (idx === -1) throw new Error(`Application ${payload.id} not found`);
      session.applications[idx] = { ...session.applications[idx], ...payload };
      await setLocal({ session });
      return session.applications[idx];
    }

    case 'DELETE_APPLICATION': {
      const { session } = await getLocal(['session']);
      session.applications = session.applications.filter(
        (a) => a.id !== payload.id,
      );
      await setLocal({ session });
      return { deleted: payload.id };
    }

    case 'GET_SETTINGS': {
      const { session } = await getLocal(['session']);
      return session?.settings ?? DEFAULT_SESSION.settings;
    }

    case 'UPDATE_SETTINGS': {
      const { session } = await getLocal(['session']);
      session.settings = { ...session.settings, ...payload };
      await setLocal({ session });
      return session.settings;
    }

    case 'LOG_ERROR': {
      const entry = await logError({
        source: payload?.source ?? _sender?.url ?? 'unknown',
        message: payload?.message ?? 'No message provided',
        stack: payload?.stack ?? null,
        context: payload?.context ?? null,
      });
      return entry;
    }

    case 'GET_ERROR_LOG': {
      const { errorLog = [] } = await getLocal(['errorLog']);
      return errorLog;
    }

    case 'CLEAR_ERROR_LOG': {
      await setLocal({ errorLog: [] });
      return { cleared: true };
    }

    default:
      throw new Error(`Unknown action: ${action}`);
  }
}

// logs any storage changes to the console - useful for debugging to make sure
// the popup and content scripts are staying in sync
chrome.storage.onChanged.addListener((changes, areaName) => {
  console.group(`[background] storage.onChanged - area: ${areaName}`);
  for (const [key, { oldValue, newValue }] of Object.entries(changes)) {
    console.log(`  key: "${key}"`);
    console.log('    old:', oldValue);
    console.log('    new:', newValue);
  }
  console.groupEnd();
});
