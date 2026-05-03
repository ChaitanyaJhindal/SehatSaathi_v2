import React, { createContext, useContext, useEffect, useMemo, useState } from "react";

const AppContext = createContext(null);
const MAX_LOGS = 40;

function serializeError(error) {
  if (!error) {
    return "Unknown error";
  }

  if (typeof error === "string") {
    return error;
  }

  return error.stack || error.message || JSON.stringify(error);
}

export function AppProvider({ children }) {
  const [user, setUser] = useState(null);
  const [reports, setReports] = useState([]);
  const [logs, setLogs] = useState([]);

  const login = (payload) => setUser(payload);
  const logout = () => {
    setUser(null);
    setReports([]);
  };
  const addReport = (reportEntry) => {
    setReports((current) => [reportEntry, ...current]);
  };
  const addLog = (level, message, details = "") => {
    const entry = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      level,
      message,
      details,
      createdAt: new Date().toLocaleTimeString(),
    };

    setLogs((current) => [entry, ...current].slice(0, MAX_LOGS));
  };
  const logInfo = (message, details = "") => {
    addLog("info", message, details);
  };
  const logError = (message, error) => {
    addLog("error", message, serializeError(error));
  };
  const clearLogs = () => {
    setLogs([]);
  };

  useEffect(() => {
    const errorUtils = global.ErrorUtils;
    const previousHandler = errorUtils?.getGlobalHandler?.();

    if (!errorUtils?.setGlobalHandler) {
      return undefined;
    }

    errorUtils.setGlobalHandler((error, isFatal) => {
      addLog(
        "error",
        isFatal ? "Fatal app error" : "Unhandled app error",
        serializeError(error)
      );

      if (previousHandler) {
        previousHandler(error, isFatal);
      }
    });

    return () => {
      if (previousHandler) {
        errorUtils.setGlobalHandler(previousHandler);
      }
    };
  }, []);

  const value = useMemo(
    () => ({
      user,
      reports,
      logs,
      login,
      logout,
      addReport,
      addLog,
      logInfo,
      logError,
      clearLogs,
    }),
    [user, reports, logs]
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
