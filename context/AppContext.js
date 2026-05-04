import React, { createContext, useCallback, useContext, useMemo, useState } from "react";

const AppContext = createContext(null);

export function AppProvider({ children }) {
  const [user, setUser] = useState(null);
  const [reports, setReports] = useState([]);

  const login = useCallback((payload) => setUser(payload), []);
  const logout = useCallback(() => {
    setUser(null);
    setReports([]);
  }, []);
  const addReport = useCallback((reportEntry) => {
    setReports((current) => [reportEntry, ...current]);
  }, []);

  const value = useMemo(
    () => ({
      user,
      reports,
      login,
      logout,
      addReport,
    }),
    [user, reports, login, logout, addReport]
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
