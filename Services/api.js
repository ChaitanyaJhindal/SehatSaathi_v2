import axios from "axios";
import * as FileSystem from "expo-file-system";

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

export async function generateReport(asset) {
  const file = normalizeFile(asset);
  const formData = new FormData();
  formData.append("file", file);

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
