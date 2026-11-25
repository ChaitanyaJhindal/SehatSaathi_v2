import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import {
  fetchMe,
  fetchReports,
  getWhatsAppStatus,
  resolvePdfUrl,
  setAuthToken,
} from "../Services/api";
import { clearSession, loadSession, saveSession } from "../Services/storage";

const AppContext = createContext(null);

export function normalizeStoredReport(doc) {
  if (!doc) return null;
  const ageVal = doc.patient_age ?? doc.age ?? null;
  const createdRaw = doc.created_at || doc.createdAt;
  const createdDate = createdRaw ? new Date(createdRaw) : null;
  const createdDisplay =
    createdDate && !Number.isNaN(createdDate.getTime())
      ? createdDate.toLocaleString()
      : String(createdRaw || "Saved report");

  return {
    id: doc.report_id || doc.id,
    filename: doc.filename || doc.patient_name || "Consultation Report",
    transcript: doc.transcript || "",
    report: doc,
    pdfUrl: resolvePdfUrl(doc.pdf_url || doc.pdf_download_url),
    reportId: doc.report_id || doc.id,
    reportRecordId: doc.id,
    patientId: doc.patient_id,
    patientName: doc.patient_name,
    patientAge: ageVal,
    patientGender: doc.patient_gender ?? doc.gender,
    patientPhone: doc.patient_phone ?? doc.patient_mobile,
    patientNotes: doc.patient_notes,
    doctorName: doc.doctor_name,
    createdAtIso: createdRaw || null,
    createdAt: createdDisplay,
  };
}

export function AppProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [hydrated, setHydrated] = useState(false);
  const [reports, setReports] = useState([]);
  const [whatsappStatus, setWhatsappStatus] = useState(null);

  useEffect(() => {
    let active = true;
    const hydrate = async () => {
      try {
        const stored = await loadSession();
        if (stored?.token && stored?.user) {
          setAuthToken(stored.token);
          try {
            const freshUser = await fetchMe();
            if (!active) return;
            setUser(freshUser);
            setToken(stored.token);
            await saveSession({ user: freshUser, token: stored.token });
          } catch (err) {
            if (!active) return;
            const status = err?.response?.status;
            if (status === 401 || status === 403) {
              setAuthToken(null);
              await clearSession();
            } else {
              setUser(stored.user);
              setToken(stored.token);
            }
          }
        }
      } finally {
        if (active) {
          setHydrated(true);
        }
      }
    };
    hydrate();
    return () => {
      active = false;
    };
  }, []);

  const login = useCallback(async (authResponse) => {
    const accessToken = authResponse?.access_token || null;
    const doctorProfile = {
      id: authResponse?.id,
      name: authResponse?.name,
      email: authResponse?.email,
      specialization: authResponse?.specialization,
      organization_name: authResponse?.organization_name,
    };
    setAuthToken(accessToken);
    setToken(accessToken);
    setUser(doctorProfile);
    await saveSession({ user: doctorProfile, token: accessToken });
  }, []);

  const logout = useCallback(async () => {
    setAuthToken(null);
    setToken(null);
    setUser(null);
    setReports([]);
    setWhatsappStatus(null);
    await clearSession();
  }, []);

  const addReport = useCallback((reportEntry) => {
    setReports((current) => {
      const filtered = current.filter(
        (item) => (item.reportId || item.id) !== (reportEntry.reportId || reportEntry.id)
      );
      return [reportEntry, ...filtered];
    });
  }, []);

  const updateReportEntry = useCallback((reportId, updatedPayload) => {
    setReports((current) =>
      current.map((item) =>
        item.reportId === reportId || item.id === reportId
          ? { ...item, ...updatedPayload }
          : item
      )
    );
  }, []);

  const refreshReports = useCallback(async () => {
    if (!token) return [];
    try {
      const docs = await fetchReports(50);
      const normalized = docs.map(normalizeStoredReport).filter(Boolean);
      setReports(normalized);
      return normalized;
    } catch {
      return [];
    }
  }, [token]);

  const refreshWhatsAppStatus = useCallback(async () => {
    if (!token) return null;
    try {
      const status = await getWhatsAppStatus();
      setWhatsappStatus(status);
      return status;
    } catch {
      return null;
    }
  }, [token]);

  const value = useMemo(
    () => ({
      user,
      token,
      hydrated,
      reports,
      whatsappStatus,
      setWhatsappStatus,
      login,
      logout,
      addReport,
      updateReportEntry,
      refreshReports,
      refreshWhatsAppStatus,
    }),
    [
      user,
      token,
      hydrated,
      reports,
      whatsappStatus,
      login,
      logout,
      addReport,
      updateReportEntry,
      refreshReports,
      refreshWhatsAppStatus,
    ]
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useAppContext() {
  const context = useContext(AppContext);

  if (!context) {
    throw new Error("useAppContext must be used within an AppProvider");
  }

  return context;
}
