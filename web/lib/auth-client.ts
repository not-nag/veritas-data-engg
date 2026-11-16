import { initializeApp, getApps } from "@firebase/app";
import { getAuth, type Auth } from "@firebase/auth";
let auth: Auth | null = null;
export function configureAuth(config: {
  apiKey: string;
  projectId: string;
  authDomain: string;
  appId: string;
}) {
  auth = getAuth(getApps()[0] || initializeApp(config));
  return auth;
}
export async function writeHeaders(): Promise<Record<string, string>> {
  await auth?.authStateReady();
  const token = await auth?.currentUser?.getIdToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}
