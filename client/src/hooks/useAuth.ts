import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as auth from "@/lib/api/auth";

export const useCurrentUser = () => useQuery({ queryKey: ["me"], queryFn: auth.getCurrentUser });

export const useRegister = () => useMutation({ mutationFn: auth.register });
export const useLogin = () => useMutation({ mutationFn: auth.login });
export const useSendOtp = () => useMutation({ mutationFn: auth.sendOtp });
export const useVerifyOtp = () => useMutation({ mutationFn: auth.verifyOtp });
export const useResetPassword = () => useMutation({ mutationFn: auth.resetPassword });
export const useRegisterDeviceToken = () => useMutation({ mutationFn: auth.registerDeviceToken });

export const useUpdateNotificationSettings = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: auth.updateNotificationSettings,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notification-settings"] }),
  });
};
