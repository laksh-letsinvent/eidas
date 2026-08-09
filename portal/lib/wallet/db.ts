// IndexedDB wrapper — plain `indexedDB` API, no library, consistent with
// this lab's "no dependency where the mechanism is the point" pattern.
//
// The `keys` store holds the actual `CryptoKeyPair` object by reference.
// Non-extractable `CryptoKey` objects are structured-clonable and
// IndexedDB-storable directly: the key handle persists across reloads
// without the raw key material ever touching a byte array a script could
// read or exfiltrate — that's the whole point of `extractable: false`.

const DB_NAME = "eidas-wallet";
const DB_VERSION = 1;
const KEYS_STORE = "keys";
const CREDENTIAL_STORE = "credential";
const KEYS_RECORD_ID = "holder";
const CREDENTIAL_RECORD_ID = "current";

export interface StoredCredential {
  credentialCompact: string;
  vct: string;
  webauthnCredentialId?: string;
}

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(KEYS_STORE)) db.createObjectStore(KEYS_STORE);
      if (!db.objectStoreNames.contains(CREDENTIAL_STORE)) db.createObjectStore(CREDENTIAL_STORE);
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function putRecord(storeName: string, key: string, value: unknown): Promise<void> {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, "readwrite");
    tx.objectStore(storeName).put(value, key);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

async function getRecord<T>(storeName: string, key: string): Promise<T | undefined> {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, "readonly");
    const request = tx.objectStore(storeName).get(key);
    request.onsuccess = () => resolve(request.result as T | undefined);
    request.onerror = () => reject(request.error);
  });
}

export async function saveHolderKeyPair(pair: CryptoKeyPair): Promise<void> {
  await putRecord(KEYS_STORE, KEYS_RECORD_ID, pair);
}

export async function loadHolderKeyPair(): Promise<CryptoKeyPair | undefined> {
  return getRecord<CryptoKeyPair>(KEYS_STORE, KEYS_RECORD_ID);
}

export async function saveCredential(record: StoredCredential): Promise<void> {
  await putRecord(CREDENTIAL_STORE, CREDENTIAL_RECORD_ID, record);
}

export async function loadCredential(): Promise<StoredCredential | undefined> {
  return getRecord<StoredCredential>(CREDENTIAL_STORE, CREDENTIAL_RECORD_ID);
}

export async function clearWallet(): Promise<void> {
  const db = await openDb();
  await new Promise<void>((resolve, reject) => {
    const tx = db.transaction([KEYS_STORE, CREDENTIAL_STORE], "readwrite");
    tx.objectStore(KEYS_STORE).clear();
    tx.objectStore(CREDENTIAL_STORE).clear();
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}
