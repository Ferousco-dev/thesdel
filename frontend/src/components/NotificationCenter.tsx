import { useEffect, useState } from "react";
import { registerDeviceToken, unregisterDeviceToken } from "../lib/api/endpoints";
import { isApiError } from "../lib/api/errors";

interface Props {
  userId: string;
}

export function NotificationCenter({ userId }: Props) {
  const [notificationCount] = useState(0);
  const [isPanelOpen, setIsPanelOpen] = useState(false);
  const [isRegistered, setIsRegistered] = useState(false);
  const [registrationError, setRegistrationError] = useState<string | null>(null);

  // Register device token for push notifications on mount
  useEffect(() => {
    const registerDevice = async () => {
      try {
        // Check if push notifications are supported and user has granted permission
        if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
          console.log("Push notifications not supported on this browser");
          return;
        }

        // Try to get the service worker registration
        const registration = await navigator.serviceWorker.getRegistration();
        if (!registration) {
          console.log("Service worker not registered yet");
          return;
        }

        // Request permission if not already granted
        if (Notification.permission === "default") {
          const permission = await Notification.requestPermission();
          if (permission !== "granted") {
            console.log("Notification permission denied");
            return;
          }
        } else if (Notification.permission !== "granted") {
          console.log("Notification permission not granted");
          return;
        }

        // Try to get push subscription
        let subscription = await registration.pushManager.getSubscription();
        if (!subscription) {
          // No subscription exists, would need VAPID public key to create one
          // For now, use a device identifier stored in localStorage
          const storedToken = localStorage.getItem("thesdel-device-token");
          if (storedToken) {
            await registerDeviceToken(storedToken, "web");
            setIsRegistered(true);
            return;
          }
        } else {
          // Use the subscription endpoint as the token
          const token = subscription.endpoint.split("/").pop() || "web-" + Date.now();
          await registerDeviceToken(token, "web");
          setIsRegistered(true);
        }
      } catch (err) {
        const message = isApiError(err) ? err.message : "Failed to register device";
        console.error("Device registration error:", message);
        setRegistrationError(message);
      }
    };

    registerDevice();
  }, [userId]);

  // Handle unregistration on unmount
  useEffect(() => {
    return () => {
      const storedToken = localStorage.getItem("thesdel-device-token");
      if (storedToken && isRegistered) {
        unregisterDeviceToken(storedToken).catch((err) => {
          console.error("Failed to unregister device:", err);
        });
      }
    };
  }, [isRegistered]);

  return (
    <div style={{ position: "relative" }}>
      {/* Notification Bell Button */}
      <button
        type="button"
        onClick={() => setIsPanelOpen(!isPanelOpen)}
        style={{
          background: "none",
          border: "none",
          fontSize: "1.25rem",
          cursor: "pointer",
          padding: "0.5rem",
          borderRadius: "var(--radius-md)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          position: "relative",
          color: "var(--color-text-primary)",
        }}
        title="Notifications"
      >
        🔔
        {notificationCount > 0 && (
          <span
            style={{
              position: "absolute",
              top: "-2px",
              right: "-2px",
              background: "var(--color-primary)",
              color: "white",
              borderRadius: "50%",
              width: "20px",
              height: "20px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "0.7rem",
              fontWeight: 700,
            }}
          >
            {notificationCount > 9 ? "9+" : notificationCount}
          </span>
        )}
      </button>

      {/* Notification Panel */}
      {isPanelOpen && (
        <div
          style={{
            position: "absolute",
            top: "100%",
            right: 0,
            marginTop: "0.5rem",
            background: "var(--color-bg)",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-md)",
            boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
            width: "300px",
            maxHeight: "400px",
            overflow: "auto",
            zIndex: 1000,
          }}
        >
          <div
            style={{
              padding: "1rem",
              borderBottom: "1px solid var(--color-border)",
              fontWeight: 600,
            }}
          >
            Notifications
          </div>

          {registrationError && (
            <div
              style={{
                padding: "0.75rem 1rem",
                background: "rgba(214, 69, 69, 0.05)",
                borderBottom: "1px solid var(--color-border)",
                fontSize: "0.85rem",
                color: "var(--color-error)",
              }}
            >
              {registrationError}
            </div>
          )}

          {isRegistered && (
            <div
              style={{
                padding: "0.75rem 1rem",
                background: "rgba(77, 171, 120, 0.05)",
                borderBottom: "1px solid var(--color-border)",
                fontSize: "0.85rem",
                color: "var(--color-success)",
              }}
            >
              ✓ Notifications enabled
            </div>
          )}

          <div style={{ padding: "1rem", textAlign: "center", color: "var(--color-text-secondary)", fontSize: "0.85rem" }}>
            {notificationCount === 0 ? (
              <p>No new notifications</p>
            ) : (
              <p>{notificationCount} unread notification{notificationCount !== 1 ? "s" : ""}</p>
            )}
          </div>

          {/* TODO: Add notification list when GET /v1/notifications is implemented */}
          <div style={{ padding: "1rem", fontSize: "0.8rem", color: "var(--color-text-secondary)", borderTop: "1px solid var(--color-border)" }}>
            <p style={{ margin: 0 }}>📋 Notification history coming soon</p>
          </div>
        </div>
      )}
    </div>
  );
}
