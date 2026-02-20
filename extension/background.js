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
