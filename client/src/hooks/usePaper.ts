import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as db from "@/lib/api/db";
import * as paper from "@/lib/api/paper";
import * as auth from "@/lib/api/auth";

export const useChapters = () =>
  useQuery({ queryKey: ["chapters"], queryFn: () => db.getChapters().then((r) => r.chapters) });

export const useHistory = () =>
  useQuery({ queryKey: ["history"], queryFn: () => db.getHistory().then((r) => r.history) });

export const useNotificationSettings = () =>
  useQuery({ queryKey: ["notification-settings"], queryFn: auth.getNotificationSettings });

export const useGeneratePaper = () => useMutation({ mutationFn: paper.generatePaper });

export const useResumeGeneration = () =>
  useMutation({
    mutationFn: ({ threadId, selectedIndices }: { threadId: string; selectedIndices: number[] }) =>
      paper.resumeGeneration(threadId, selectedIndices),
  });

export const useCancelGeneration = () => useMutation({ mutationFn: paper.cancelGeneration });

export const useSaveToCloud = () => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: paper.saveToCloud,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["history"] }),
  });
};
