"use client";
import { useEffect, useState } from "react";
import {
  GoogleAuthProvider,
  onAuthStateChanged,
  signInWithPopup,
  signOut,
  type Auth,
  type User,
} from "@firebase/auth";
import { configureAuth } from "@/lib/auth-client";
import { Button } from "./ui/button";
export function SignIn() {
  const [auth, setAuth] = useState<Auth | null>(null);
  const [required, setRequired] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    let unsubscribe: (() => void) | undefined;
    let active = true;
    fetch("/api/session", { cache: "no-store" })
      .then((r) => r.json())
      .then((data) => {
        if (!active) return;
        setRequired(data.required);
        if (data.firebase?.apiKey && data.firebase?.projectId) {
          const a = configureAuth(data.firebase);
          setAuth(a);
          unsubscribe = onAuthStateChanged(a, setUser);
        }
      })
      .catch(() => setError("Sign-in service is unavailable."));
    return () => {
      active = false;
      unsubscribe?.();
    };
  }, []);
  async function change() {
    if (!auth) return;
    setBusy(true);
    setError("");
    try {
      if (user) await signOut(auth);
      else
        await Promise.race([
          signInWithPopup(auth, new GoogleAuthProvider()),
          new Promise((_, reject) =>
            setTimeout(() => reject(new Error("Sign-in timed out")), 45000),
          ),
        ]);
    } catch {
      setError(
        "Could not sign in. Allow popups and check the authorised domain in Firebase.",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="sign-in-control">
      {user ? (
        <span className="text-xs">{user.displayName || user.email}</span>
      ) : required ? (
        <span className="text-xs">Public view</span>
      ) : null}
      {(auth || required) && (
        <Button
          size="sm"
          variant="outline"
          className="text-neutral-900"
          disabled={!auth || busy}
          onClick={change}
        >
          {busy ? "Signing in…" : user ? "Sign out" : "Sign in to edit"}
        </Button>
      )}
      {error && (
        <span role="alert" className="sign-in-error">
          {error}
        </span>
      )}
    </div>
  );
}
