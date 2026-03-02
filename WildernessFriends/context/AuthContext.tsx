import React, { createContext, useContext, useState, useEffect } from "react";
import {
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut,
  onAuthStateChanged,
  User as FirebaseUser,
} from "firebase/auth";
import { auth } from "../config/firebase";
import * as tokenManager from "../services/tokenManager";

interface User {
  uid: string;
  email: string | null;
}

interface UserPermissions {
  role: string;
  is_premium: boolean;
  permissions: Record<string, boolean>;
  subscription: { tier: string; status: string };
}

type AuthContextType = {
  user: User | null;
  loading: boolean;
  error: string | null;
  apiReady: boolean;
  permissions: UserPermissions | null;
  setError: (error: string | null) => void;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;
};

const AuthContext = createContext<AuthContextType>({} as AuthContextType);

export const useAuth = () => useContext(AuthContext);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [apiReady, setApiReady] = useState(false);
  const [permissions, setPermissions] = useState<UserPermissions | null>(null);

  const exchangeAndSetToken = async () => {
    try {
      const data = await tokenManager.exchangeToken();
      setPermissions({
        role: data.user.role,
        is_premium: data.user.is_premium,
        permissions: data.user.permissions,
        subscription: data.user.subscription,
      });
      setApiReady(true);
    } catch (err) {
      console.warn("[Auth] Token exchange failed:", err);
      setApiReady(false);
    }
  };

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(
      auth,
      async (firebaseUser: FirebaseUser | null) => {
        if (firebaseUser) {
          setUser({
            uid: firebaseUser.uid,
            email: firebaseUser.email,
          });
          // Exchange Firebase token for internal JWT
          await exchangeAndSetToken();
        } else {
          setUser(null);
          setApiReady(false);
          setPermissions(null);
          tokenManager.clearToken();
        }
        setLoading(false);
      }
    );

    return unsubscribe;
  }, []);

  const login = async (email: string, password: string) => {
    try {
      setLoading(true);
      setError(null);
      await signInWithEmailAndPassword(auth, email, password);
    } catch (err: any) {
      const message = getFirebaseErrorMessage(err.code);
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const register = async (email: string, password: string) => {
    try {
      setLoading(true);
      setError(null);
      await createUserWithEmailAndPassword(auth, email, password);
    } catch (err: any) {
      const message = getFirebaseErrorMessage(err.code);
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    try {
      setLoading(true);
      tokenManager.clearToken();
      setApiReady(false);
      setPermissions(null);
      await signOut(auth);
    } catch (err: any) {
      setError(err.message || "Logout failed");
    } finally {
      setLoading(false);
    }
  };

  const refreshToken = async () => {
    await exchangeAndSetToken();
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        error,
        apiReady,
        permissions,
        setError,
        login,
        register,
        logout,
        refreshToken,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

function getFirebaseErrorMessage(code: string): string {
  switch (code) {
    case "auth/invalid-email":
      return "Invalid email address.";
    case "auth/user-disabled":
      return "This account has been disabled.";
    case "auth/user-not-found":
      return "No account found with this email.";
    case "auth/wrong-password":
      return "Incorrect password.";
    case "auth/email-already-in-use":
      return "An account with this email already exists.";
    case "auth/weak-password":
      return "Password should be at least 6 characters.";
    case "auth/too-many-requests":
      return "Too many attempts. Please try again later.";
    case "auth/invalid-credential":
      return "Invalid email or password.";
    default:
      return "An unexpected error occurred. Please try again.";
  }
}
