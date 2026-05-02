import React, { createContext, useContext, useMemo, useState } from "react";

const AppContext = createContext(null);

export function AppProvider({ children }) {
  const [user, setUser] = useState(null);
  const [reports, setReports] = useState([]);

  const login = (payload) => setUser(payload);
  const logout = () => {
    setUser(null);
    setReports([]);
  };
  const addReport = (reportEntry) => {
    setReports((current) => [reportEntry, ...current]);
  };

  const value = useMemo(
    () => ({ user, reports, login, logout, addReport }),
    [user, reports]
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
