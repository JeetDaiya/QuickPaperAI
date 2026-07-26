importScripts("https://www.gstatic.com/firebasejs/10.8.0/firebase-app-compat.js");
importScripts("https://www.gstatic.com/firebasejs/10.8.0/firebase-messaging-compat.js");

// Parse Firebase config dynamically from Service Worker registration URL parameters
const params = new URLSearchParams(self.location.search);

const firebaseConfig = {
  apiKey: params.get("apiKey") || "",
  authDomain: params.get("authDomain") || "quickpaperai-fc0db.firebaseapp.com",
  projectId: params.get("projectId") || "quickpaperai-fc0db",
  storageBucket: params.get("storageBucket") || "quickpaperai-fc0db.firebasestorage.app",
  messagingSenderId: params.get("messagingSenderId") || "286258662494",
  appId: params.get("appId") || ""
};

firebase.initializeApp(firebaseConfig);

const messaging = firebase.messaging();

// 1. Background notification handler
messaging.onBackgroundMessage((payload) => {
  console.log("[firebase-messaging-sw.js] Received background message: ", payload);

  // Firebase automatically renders payload.notification for Web Push.
  // Only call showNotification manually if payload.notification is missing (data-only push).
  if (!payload.notification) {
    const notificationTitle = payload.data?.title || "QuickPaper AI";
    const notificationOptions = {
      body: payload.data?.body || "Your generated paper status has updated.",
      icon: "/icon-192x192.png",
      data: payload.data || {}
    };

    self.registration.showNotification(notificationTitle, notificationOptions);
  }
});

// 2. Notification Click Handler (Redirects to Preview / Review Page)
self.addEventListener("notificationclick", (event) => {
  event.notification.close();

  const previewUrl =
    event.notification.data?.url ||
    (event.notification.data?.thread_id
      ? `/papers/${event.notification.data.thread_id}/review`
      : "/");

  event.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then((windowClients) => {
      for (const client of windowClients) {
        if (client.url.includes(previewUrl) && "focus" in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(previewUrl);
      }
    })
  );
});
