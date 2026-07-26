import { initializeApp } from "firebase/app";
import { getMessaging } from "firebase/messaging";

export const firebaseConfig = {
  apiKey: (import.meta as any).env?.VITE_FIREBASE_API_KEY || "",
  authDomain:
    (import.meta as any).env?.VITE_FIREBASE_AUTH_DOMAIN ||
    "quickpaperai-fc0db.firebaseapp.com",
  projectId:
    (import.meta as any).env?.VITE_FIREBASE_PROJECT_ID || "quickpaperai-fc0db",
  storageBucket:
    (import.meta as any).env?.VITE_FIREBASE_STORAGE_BUCKET ||
    "quickpaperai-fc0db.firebasestorage.app",
  messagingSenderId:
    (import.meta as any).env?.VITE_FIREBASE_MESSAGING_SENDER_ID ||
    "286258662494",
  appId: (import.meta as any).env?.VITE_FIREBASE_APP_ID || "",
};

const app = initializeApp(firebaseConfig);

export const messaging =
  typeof window !== "undefined" && "Notification" in window
    ? getMessaging(app)
    : null;
