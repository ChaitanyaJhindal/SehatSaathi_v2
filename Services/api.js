import axios from "axios";
import * as FileSystem from "expo-file-system/legacy";
import { Platform } from "react-native";

function resolveApiBaseUrl() {
  const envUrl = process.env.EXPO_PUBLIC_API_URL?.trim();
  if (envUrl) {
    return envUrl.replace(/\/+$/, "");
  }

  if (Platform.OS === "web" && typeof window !== "undefined" && window.location) {
    const { port, origin } = window.location;
    if (port === "8081" || port === "19006") {
      return "http://localhost:8000";
    }
    if (origin) {
      return origin.replace(/\/+$/, "");
    }
  }

  return "http://localhost:8000";
}

const API_BASE_URL = resolveApiBaseUrl();

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000,
});

let _authToken = null;

export function setAuthToken(token) {
  _authToken = token || null;
}

api.interceptors.request.use((config) => {
  if (_authToken) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${_authToken}`;
  }
  return config;
});

export function getApiBaseUrl() {
  return API_BASE_URL;
}

export function resolvePdfUrl(pathOrUrl) {
  if (!pathOrUrl) {
    return null;
  }
  if (pathOrUrl.startsWith("http://") || pathOrUrl.startsWith("https://")) {
    return pathOrUrl;
  }
  const normalized = pathOrUrl.startsWith("/") ? pathOrUrl : `/${pathOrUrl}`;
  return `${API_BASE_URL}${normalized}`;
}

function extensionFromMimeType(mimeType) {
  const lower = String(mimeType || "").toLowerCase();
  if (lower.includes("webm")) return "webm";
  if (lower.includes("ogg")) return "ogg";
  if (lower.includes("wav")) return "wav";
  if (lower.includes("mpeg") || lower.includes("mp3")) return "mp3";
  if (lower.includes("mp4") || lower.includes("m4a") || lower.includes("aac")) return "m4a";
  return "m4a";
}

function normalizeFile(asset) {
  const ext = extensionFromMimeType(asset?.mimeType);
  return {
    uri: asset.uri,
    name: asset.name || `consultation-${Date.now()}.${ext}`,
    type: asset.mimeType || "audio/m4a",
  };
}

export async function signupDoctor(payload) {
  const response = await api.post("/auth/signup", payload);
  return response.data;
}

export async function loginDoctor(payload) {
  const response = await api.post("/auth/login", payload);
  return response.data;
}

export async function fetchMe() {
  const response = await api.get("/auth/me", { timeout: 15000 });
  return response.data;
}

export async function fetchReports(limit = 50) {
  const response = await api.get("/reports", { params: { limit }, timeout: 30000 });
  return response.data?.reports || [];
}

export async function generateReport(asset, user, patientDetails = {}) {
  if (!asset || (!asset.uri && !asset.file)) {
    throw new Error("No audio file was provided.");
  }

  const formData = new FormData();

  if (Platform.OS === "web") {
    let fileBlob = asset?.file;
    if (!fileBlob && asset?.uri) {
      const fetchRes = await fetch(asset.uri);
      fileBlob = await fetchRes.blob();
    }
    const detectedMime = fileBlob?.type || asset?.mimeType || "audio/webm";
    const ext = extensionFromMimeType(detectedMime);
    const rawName = asset?.name || `consultation-${Date.now()}.${ext}`;
    const fileName = rawName.endsWith(".m4a") && ext !== "m4a"
      ? rawName.replace(/\.m4a$/i, `.${ext}`)
      : rawName;

    if (fileBlob) {
      formData.append("file", fileBlob, fileName);
    } else {
      formData.append("file", normalizeFile(asset));
    }
  } else {
    formData.append("file", normalizeFile(asset));
  }

  if (user?.id) {
    formData.append("doctor_id", String(user.id));
  }
  if (patientDetails.patientId) {
    formData.append("patient_id", String(patientDetails.patientId));
  }
  if (patientDetails.name) {
    formData.append("patient_name", patientDetails.name.trim());
  }
  if (patientDetails.age !== undefined && patientDetails.age !== null && String(patientDetails.age).trim() !== "") {
    formData.append("patient_age", String(patientDetails.age).trim());
  }
  if (patientDetails.gender) {
    formData.append("patient_gender", patientDetails.gender.trim());
  }
  if (patientDetails.phone) {
    formData.append("patient_phone", patientDetails.phone.trim());
  }
  if (patientDetails.notes) {
    formData.append("patient_notes", patientDetails.notes.trim());
  }

  const requestConfig = { timeout: 300000 };
  if (Platform.OS !== "web") {
    requestConfig.headers = { "Content-Type": "multipart/form-data" };
  }

  const response = await api.post("/generate-report", formData, requestConfig);
  const payload = response.data || {};
  const pdfUrl = resolvePdfUrl(payload.pdf_download_url);

  return {
    ...payload,
    pdf_url: pdfUrl,
  };
}

export async function updateReport(reportId, updates) {
  const response = await api.patch(`/reports/${reportId}`, updates, { timeout: 60000 });
  const data = response.data || {};
  return {
    ...data,
    pdf_url: resolvePdfUrl(data.pdf_download_url || data.report?.pdf_url),
  };
}

export async function downloadPdfToCache(pdfUrl) {
  if (Platform.OS === "web") {
    return pdfUrl;
  }
  const fileUri = `${FileSystem.cacheDirectory}sehatsaathi-report-${Date.now()}.pdf`;
  const downloadResult = await FileSystem.downloadAsync(pdfUrl, fileUri);
  return downloadResult.uri;
}

export async function getWhatsAppStatus() {
  const response = await api.get("/whatsapp/status", { timeout: 15000 });
  return response.data;
}

export async function connectWhatsApp() {
  const response = await api.post("/whatsapp/connect", {}, { timeout: 45000 });
  return response.data;
}

export async function requestWhatsAppPairingCode(phone) {
  const response = await api.post("/whatsapp/pairing-code", { phone }, { timeout: 45000 });
  return response.data;
}

export async function logoutWhatsApp() {
  const response = await api.post("/whatsapp/logout", {}, { timeout: 30000 });
  return response.data;
}

export async function sendReportOnWhatsApp(reportId, phone = null) {
  const body = phone && phone.trim() ? { phone: phone.trim() } : {};
  const response = await api.post(`/reports/${reportId}/send-whatsapp`, body, { timeout: 45000 });
  return response.data;
}

export function extractErrorMessage(error) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object") {
          const field = Array.isArray(item.loc) ? item.loc[item.loc.length - 1] : null;
          const msg = item.msg || JSON.stringify(item);
          return field && field !== "body" ? `${field}: ${msg}` : msg;
        }
        return String(item);
      })
      .filter(Boolean);
    if (messages.length > 0) {
      return messages.join("\n");
    }
  }
  if (detail && typeof detail === "object") {
    return detail.message || JSON.stringify(detail);
  }

  const messageField = error?.response?.data?.message;
  if (typeof messageField === "string" && messageField.trim()) {
    return messageField;
  }

  if (typeof error?.message === "string" && error.message.trim()) {
    return error.message;
  }

  return "Something went wrong while contacting SehatSaathi.";
}
