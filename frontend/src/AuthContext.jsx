import { createContext, useContext, useMemo, useState } from "react";

const TOKEN_KEY = "grocery_bill_token";
const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => sessionStorage.getItem(TOKEN_KEY));

  const value = useMemo(
    () => ({
      token,
      isAuthenticated: Boolean(token),
      login: (nextToken) => {
        sessionStorage.setItem(TOKEN_KEY, nextToken);
        setToken(nextToken);
      },
      logout: () => {
        sessionStorage.removeItem(TOKEN_KEY);
        setToken(null);
      },
    }),
    [token]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return ctx;
}
