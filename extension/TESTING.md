# Testing the Service Worker

To test, go to `chrome://extensions`, turn on Developer mode, load the unpacked
extension folder, and click "Inspect views: service worker" to open DevTools.

Paste these into the Console tab one at a time.

---

## Test 1 - Write and read back from storage

```js
await chrome.storage.local.set({
  session: {
    user: { name: 'Jane Doe', email: 'jane@example.com', resumeUrl: 'https://example.com/resume.pdf' },
    applications: [],
    settings: { autofillEnabled: true, notificationsEnabled: true },
    lastInitialized: new Date().toISOString()
  }
});
const result = await chrome.storage.local.get('session');
console.log('READ-BACK:', result.session);
// should print back the object with user.name = 'Jane Doe'
```

---

## Test 2 - GET_USER_DATA message

```js
const response = await chrome.runtime.sendMessage({
  action: 'GET_USER_DATA',
  payload: {}
});
console.log('GET_USER_DATA response:', response);
// should return { success: true, data: { name: 'Jane Doe', ... } }
```

---

## Test 3 - SAVE_SESSION message

```js
const response = await chrome.runtime.sendMessage({
  action: 'SAVE_SESSION',
  payload: { user: { name: 'John Smith', email: 'john@example.com' } }
});
console.log('SAVE_SESSION response:', response);
// should return { success: true, data: { user: { name: 'John Smith', ... }, ... } }
```

---

## Test 4 - Add an application and list them

```js
const addResp = await chrome.runtime.sendMessage({
  action: 'ADD_APPLICATION',
  payload: { company: 'Acme Corp', role: 'Frontend Engineer', status: 'applied' }
});
console.log('ADD_APPLICATION:', addResp);

const listResp = await chrome.runtime.sendMessage({
  action: 'GET_APPLICATIONS',
  payload: {}
});
console.log('GET_APPLICATIONS:', listResp);
// the added app should have an auto-generated id, and the list should have at least 1 entry
```

---

## Test 5 - Check that storage.onChanged fires

```js
await chrome.storage.local.set({ debugPing: Date.now() });
// look in the console for the "[background] storage.onChanged" log group
```

---

## Test 6 - Worker re-init after Terminate

1. Go to `chrome://extensions` and click "Terminate" under the service worker
2. Run the command below - Chrome will restart the worker automatically
3. Check the console for the `[background] onInstalled` log to confirm it came back up
4. Data from before should still be there since initializeDefaultSession doesn't overwrite existing stuff

```js
const response = await chrome.runtime.sendMessage({
  action: 'GET_SESSION',
  payload: {}
});
console.log('POST-TERMINATE GET_SESSION:', response);
// should still have all the data from earlier tests
```

---

## Test 7 - Bad action returns an error

```js
const response = await chrome.runtime.sendMessage({
  action: 'DOES_NOT_EXIST',
  payload: {}
});
console.log('UNKNOWN ACTION:', response);
// should return { success: false, error: 'Unknown action: DOES_NOT_EXIST' }
```
