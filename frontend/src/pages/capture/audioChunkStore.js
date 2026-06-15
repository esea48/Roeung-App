// IndexedDB-backed storage for in-progress recording chunks.
//
// MediaRecorder emits Blob chunks every few seconds; we persist each one as
// it arrives so a recording survives a tab crash or accidental reload, then
// stitch them back together into a single Blob when the recording stops.

const DB_NAME = 'roeung-capture';
const STORE = 'recording-chunks';

function openDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1);
    req.onupgradeneeded = () => {
      req.result.createObjectStore(STORE);
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

export async function saveChunk(sessionId, index, blob) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, 'readwrite');
    tx.objectStore(STORE).put(blob, `${sessionId}:${index}`);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function getChunks(sessionId) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, 'readonly');
    const store = tx.objectStore(STORE);
    const chunks = [];
    const range = IDBKeyRange.bound(`${sessionId}:`, `${sessionId}:￿`);
    const cursorReq = store.openCursor(range);
    cursorReq.onsuccess = () => {
      const cursor = cursorReq.result;
      if (cursor) {
        chunks.push(cursor.value);
        cursor.continue();
      } else {
        resolve(chunks);
      }
    };
    cursorReq.onerror = () => reject(cursorReq.error);
  });
}

export async function clearChunks(sessionId) {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, 'readwrite');
    const store = tx.objectStore(STORE);
    const range = IDBKeyRange.bound(`${sessionId}:`, `${sessionId}:￿`);
    const cursorReq = store.openCursor(range);
    cursorReq.onsuccess = () => {
      const cursor = cursorReq.result;
      if (cursor) {
        cursor.delete();
        cursor.continue();
      } else {
        resolve();
      }
    };
    cursorReq.onerror = () => reject(cursorReq.error);
    tx.onerror = () => reject(tx.error);
  });
}
