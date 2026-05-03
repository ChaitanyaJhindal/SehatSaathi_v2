import axios from "axios";
import * as FileSystem from "expo-file-system/legacy";

const API_BASE_URL = "https://sehatsaathi-v2.onrender.com";

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000,
});

function normalizeFile(asset) {
  return {
    uri: asset.uri,
    name: asset.name || `consultation-${Date.now()}.m4a`,
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

export async function generateReport(asset, user, patientDetails = {}) {
  const file = normalizeFile(asset);
  const formData = new FormData();
  formData.append("file", file);
  if (user?.id) {
    formData.append("doctor_id", user.id);
  }
  if (patientDetails.patientId) {
    formData.append("patient_id", patientDetails.patientId);
  }
  if (patientDetails.name) {
    formData.append("patient_name", patientDetails.name);
  }
  if (patientDetails.age) {
    formData.append("patient_age", patientDetails.age);
  }
  if (patientDetails.gender) {
    formData.append("patient_gender", patientDetails.gender);
  }
  if (patientDetails.phone) {
    formData.append("patient_phone", patientDetails.phone);
  }
  if (patientDetails.notes) {
    formData.append("patient_notes", patientDetails.notes);
  }

  const response = await api.post("/generate-report", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });

  const payload = response.data;
  const pdfUrl = payload?.pdf_download_url?.startsWith("http")
    ? payload.pdf_download_url
    : `${API_BASE_URL}${payload.pdf_download_url}`;

  return {
    ...payload,
    pdf_url: pdfUrl,
  };
}

export async function downloadPdfToCache(pdfUrl) {
  const fileUri = `${FileSystem.cacheDirectory}sehatsaathi-report-${Date.now()}.pdf`;
  const downloadResult = await FileSystem.downloadAsync(pdfUrl, fileUri);
  return downloadResult.uri;
}

export function extractErrorMessage(error) {
  if (error?.response?.data?.detail) {
    return error.response.data.detail;
  }

  if (error?.response?.data?.message) {
    return error.response.data.message;
  }

  if (error?.message) {
    return error.message;
  }

  return "Something went wrong while contacting SehatSaathi.";
}
