"use client";

const set = (name, data) => {
  window.localStorage.setItem(
    window.btoa(name),
    window.btoa(JSON.stringify(data)),
  );
  return data;
};

const get = (name) => {
  name = window.btoa(name);
  const data = window.localStorage.getItem(name);
  if (!data) {
    return false;
  }
  let response = false;
  try {
    response = JSON.parse(window.atob(data));
  } catch (err) {
    window.localStorage.clear();
  }
  return response;
};

const clear = () => {
  return window.localStorage.clear();
};

/**
 * Add indexDB storage
 * https://developer.mozilla.org/en-US/docs/Web/API/IndexedDB_API
 * https://developer.mozilla.org/en-US/docs/Web/API/IndexedDB_API/Using_IndexedDB
 * https://www.npmjs.com/package/idb
 */

const dbPromise = async () => {
  if (!("indexedDB" in window)) {
    console.log("This browser doesn't support IndexedDB");
    return null;
  }
  return new Promise((resolve, reject) => {
    const request = window.indexedDB.open("app-storage", 1);
    request.onerror = (event) => {
      console.error("IndexedDB error:", event.target.errorCode);
      reject(event.target.errorCode);
    };
    request.onsuccess = (event) => {
      resolve(event.target.result);
    };
    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains("keyval")) {
        db.createObjectStore("keyval");
      }
    };
  });
};

const setIndexedDB = async (db, key, val) => {
  if (!db) return;
  return new Promise((resolve, reject) => {
    const tx = db.transaction("keyval", "readwrite");
    const store = tx.objectStore("keyval");
    const request = store.put(val, key);
    request.onsuccess = () => resolve(true);
    request.onerror = (event) => {
      console.error("IndexedDB set error:", event.target.errorCode);
      reject(event.target.errorCode);
    };
  });
};

const getIndexedDB = async (db, key) => {
  if (!db) return null;
  return new Promise((resolve, reject) => {
    const tx = db.transaction("keyval", "readonly");
    const store = tx.objectStore("keyval");
    const request = store.get(key);
    request.onsuccess = () => resolve(request.result);
    request.onerror = (event) => {
      console.error("IndexedDB get error:", event.target.errorCode);
      reject(event.target.errorCode);
    };
  });
};

const clearIndexedDB = async () => {
  if (!db) return;
  return new Promise((resolve, reject) => {
    const tx = db.transaction("keyval", "readwrite");
    const store = tx.objectStore("keyval");
    const request = store.clear();
    request.onsuccess = () => resolve(true);
    request.onerror = (event) => {
      console.error("IndexedDB clear error:", event.target.errorCode);
      reject(event.target.errorCode);
    };
  });
};

export const indexedDBStorage = {
  dbPromise: dbPromise,
  set: setIndexedDB,
  get: getIndexedDB,
  clear: clearIndexedDB,
};

export const storage = {
  set: set,
  get: get,
  clear: clear,
};
