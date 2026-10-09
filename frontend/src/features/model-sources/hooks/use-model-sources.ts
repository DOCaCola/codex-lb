import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import {
  createModelSource,
  deleteModelSource,
  listModelSources,
  updateModelSource,
} from "@/features/model-sources/api";
import type {
  ModelSourceCreateRequest,
  ModelSourceUpdateRequest,
} from "@/features/model-sources/schemas";

export function useModelSourcesList() {
  return useQuery({
    queryKey: ["model-sources", "list"],
    queryFn: listModelSources,
  });
}

export function useModelSources() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const { data, error, isFetching, isLoading, isPending, isSuccess, refetch } = useModelSourcesList();
  const modelSourcesQuery = { data, error, isFetching, isLoading, isPending, isSuccess, refetch };
  // Sources are provider accounts too: their colours and API-key scopes follow them.
  const invalidate = () => {
    for (const key of [["model-sources", "list"], ["api-keys", "list"], ["models"], ["account-colors"]]) {
      void queryClient.invalidateQueries({ queryKey: key });
    }
  };

  const createMutation = useMutation({
    mutationFn: (payload: ModelSourceCreateRequest) => createModelSource(payload),
    onSuccess: () => {
      toast.success(t("modelSources.toasts.created"));
      invalidate();
    },
    onError: (error: Error) => {
      toast.error(error.message || t("modelSources.toasts.createFailed"));
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ sourceId, payload }: { sourceId: string; payload: ModelSourceUpdateRequest }) =>
      updateModelSource(sourceId, payload),
    onSuccess: () => {
      toast.success(t("modelSources.toasts.updated"));
      invalidate();
    },
    onError: (error: Error) => {
      toast.error(error.message || t("modelSources.toasts.updateFailed"));
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (sourceId: string) => deleteModelSource(sourceId),
    onSuccess: () => {
      toast.success(t("modelSources.toasts.deleted"));
      invalidate();
    },
    onError: (error: Error) => {
      toast.error(error.message || t("modelSources.toasts.deleteFailed"));
    },
  });

  return {
    modelSourcesQuery,
    createMutation,
    updateMutation,
    deleteMutation,
  };
}
