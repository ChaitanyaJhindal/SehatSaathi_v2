import * as FileSystem from "expo-file-system/legacy";
import { Platform } from "react-native";

const WEB_STORAGE_KEY = "sehatsaathi_session_v1";
const NATIVE_SESSION_PATH = `${FileSystem.documentDirectory || ""}sehatsaathi_session.json`;

export async function loadSession() {
  try {
    if (Platform.OS === "web") {
      if (typeof window === "undefined" || !window.localStorage) {
        return null;
      }
      const raw = window.localStorage.getItem(WEB_STORAGE_KEY);
      return raw ? JSON.parse(raw) : null;
    }

    if (!FileSystem.documentDirectory) {
      return null;
    }

    const info = await FileSystem.getInfoAsync(NATIVE_SESSION_PATH);
    if (!info.exists) {
      return null;
    }
    const raw = await FileSystem.readAsStringAsync(NATIVE_SESSION_PATH);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export async function saveSession(session) {
  try {
    const serialized = JSON.stringify(session);
    if (Platform.OS === "web") {
      if (typeof window !== "undefined" && window.localStorage) {
        window.localStorage.setItem(WEB_STORAGE_KEY, serialized);
      }
      return;
    }

    if (FileSystem.documentDirectory) {
      await FileSystem.writeAsStringAsync(NATIVE_SESSION_PATH, serialized);
    }
  } catch {
    // Ignore storage write errors
  }
}

export async function clearSession() {
  try {
    if (Platform.OS === "web") {
      if (typeof window !== "undefined" && window.localStorage) {
        window.localStorage.removeItem(WEB_STORAGE_KEY);
      }
      return;
    }

    if (FileSystem.documentDirectory) {
      const info = await FileSystem.getInfoAsync(NATIVE_SESSION_PATH);
      if (info.exists) {
        await FileSystem.deleteAsync(NATIVE_SESSION_PATH, { idempotent: true });
      }
    }
  } catch {
    // Ignore storage clear errors
  }
}
