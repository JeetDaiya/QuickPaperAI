import { jsonFetch, formFetch } from "./http";
import type {
  UserResponse,
  LoginResponse,
  VerifyOtpResponse,
  NotificationSettings,
  OtpPurpose,
} from "./types";

export function register(payload: { email: string; password: string; name: string }) {
  return jsonFetch<UserResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function login(payload: { email: string; password: string }) {
  return formFetch<LoginResponse>("/auth/login", {
    username: payload.email,
    password: payload.password,
  });
}

export function sendOtp(payload: { email: string; purpose: OtpPurpose }) {
  return jsonFetch<{ message: string }>("/auth/send-email", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function verifyOtp(payload: { email: string; otp: string; purpose: OtpPurpose }) {
  return jsonFetch<VerifyOtpResponse>("/auth/verify-otp", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function resetPassword(payload: { email: string; token: string; new_password: string }) {
  return jsonFetch<{ message: string }>("/auth/reset-password", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function registerDeviceToken(payload: { token: string }) {
  return jsonFetch<{ message: string }>("/auth/device-token", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateNotificationSettings(payload: { notifications_enabled: boolean }) {
  return jsonFetch<{ message: string }>("/auth/notification-settings", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getNotificationSettings() {
  return jsonFetch<NotificationSettings>("/auth/notification-settings");
}
