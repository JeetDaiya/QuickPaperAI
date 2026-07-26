import { useEffect, useState, useCallback } from "react";
import { getToken, onMessage } from "firebase/messaging";
import { messaging, firebaseConfig } from "@/lib/firebase";
import { api } from "@/lib/api";
import { toast } from "sonner";

export function useFCMNotification(autoPromptOnVisit = true) {
  const [fcmToken, setFcmToken] = useState<string | null>(null);
  const [permissionStatus, setPermissionStatus] = useState<NotificationPermission>(
    typeof window !== "undefined" && "Notification" in window
      ? Notification.permission
      : "default"
  );
  const [notificationsEnabled, setNotificationsEnabled] = useState<boolean>(true);
  const [loading, setLoading] = useState<boolean>(false);

  // Fetch current notification settings on mount if logged in
  useEffect(() => {
    if (typeof window === "undefined") return;
    const token = localStorage.getItem("token");
    if (!token) return;

    api
      .getNotificationSettings()
      .then((data) => {
        if (data.fcm_token) {
          setFcmToken(data.fcm_token);
        }
        setNotificationsEnabled(data.notifications_enabled);
      })
      .catch((err) => {
        console.warn("Could not fetch notification settings:", err);
      });
  }, []);

  const requestPermission = useCallback(
    async (options?: { silent?: boolean }) => {
      if (typeof window === "undefined" || !("Notification" in window)) {
        if (!options?.silent) {
          toast.error("Push notifications are not supported in this browser.");
        }
        return null;
      }

      if (!messaging) {
        if (!options?.silent) {
          toast.error("Firebase Messaging service is not initialized.");
        }
        return null;
      }

      setLoading(true);
      try {
        const permission = await Notification.requestPermission();
        setPermissionStatus(permission);

        if (permission === "granted") {
          const vapidKey =
            (import.meta as any).env?.VITE_FIREBASE_VAPID_PUBLIC_KEY || undefined;

          // Register service worker dynamically passing environment configuration
          let serviceWorkerRegistration: ServiceWorkerRegistration | undefined = undefined;
          if ("serviceWorker" in navigator) {
            const swParams = new URLSearchParams({
              apiKey: firebaseConfig.apiKey || "",
              appId: firebaseConfig.appId || "",
              messagingSenderId: firebaseConfig.messagingSenderId || "",
              projectId: firebaseConfig.projectId || "",
              authDomain: firebaseConfig.authDomain || "",
              storageBucket: firebaseConfig.storageBucket || "",
            });
            const swUrl = `/firebase-messaging-sw.js?${swParams.toString()}`;
            serviceWorkerRegistration = await navigator.serviceWorker.register(swUrl);
          }

          const token = await getToken(messaging, {
            vapidKey: vapidKey || undefined,
            serviceWorkerRegistration,
          });

          if (token) {
            setFcmToken(token);
            await api.registerDeviceToken({ token });
            if (!options?.silent) {
              toast.success("📲 Push notifications enabled!", {
                description: "You will be notified when your question papers are ready.",
              });
            }
            return token;
          } else {
            if (!options?.silent) {
              toast.error("Could not obtain device token from Firebase.");
            }
          }
        } else if (permission === "denied") {
          if (!options?.silent) {
            toast.error("Notification permission blocked.", {
              description: "Please enable notifications in your browser settings.",
            });
          }
        }
      } catch (error: any) {
        console.error("⚠️ Failed to request FCM permission:", error);
        if (!options?.silent) {
          toast.error("Failed to enable notifications.", {
            description: error.message || "An unexpected error occurred.",
          });
        }
      } finally {
        setLoading(false);
      }
      return null;
    },
    []
  );

  // Automatically ask for permission when an authenticated user visits if permission is still "default"
  useEffect(() => {
    if (!autoPromptOnVisit || typeof window === "undefined" || !("Notification" in window)) {
      return;
    }
    const authToken = localStorage.getItem("token");
    if (authToken && Notification.permission === "default") {
      const timer = setTimeout(() => {
        requestPermission({ silent: true });
      }, 1200);
      return () => clearTimeout(timer);
    }
  }, [autoPromptOnVisit, requestPermission]);

  const toggleNotifications = useCallback(async (enabled: boolean) => {
    setLoading(true);
    try {
      await api.updateNotificationSettings({ notifications_enabled: enabled });
      setNotificationsEnabled(enabled);
      toast.success(enabled ? "Notifications enabled" : "Notifications disabled");
    } catch (error: any) {
      toast.error("Failed to update notification preferences.");
    } finally {
      setLoading(false);
    }
  }, []);

  // Listen for foreground notifications while the user is actively viewing the page
  useEffect(() => {
    if (!messaging) return;

    const unsubscribe = onMessage(messaging, (payload) => {
      console.log("💬 Foreground Notification received:", payload);
      const title = payload.notification?.title || "📝 QuickPaper AI";
      const body = payload.notification?.body || "Your generated paper is ready!";
      const threadId = payload.data?.thread_id;
      const targetUrl =
        payload.data?.url || (threadId ? `/papers/${threadId}/review` : undefined);

      toast(title, {
        description: body,
        action: targetUrl
          ? {
              label: "View Paper →",
              onClick: () => {
                window.location.href = targetUrl;
              },
            }
          : undefined,
      });
    });

    return () => unsubscribe();
  }, []);

  return {
    fcmToken,
    permissionStatus,
    notificationsEnabled,
    loading,
    requestPermission,
    toggleNotifications,
  };
}
