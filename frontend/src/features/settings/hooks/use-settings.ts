import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { ApiError } from "@/lib/api-client";
import {
  addUpstreamProxyPoolMember,
  createUpstreamProxyEndpoint,
  createUpstreamProxyPool,
  deleteModelCompactionRoute,
  deleteModelContextWindowOverride,
  getModelCompactionRoutes,
  getModelContextWindowOverrides,
  getSettings,
  getUpstreamProxyAdmin,
  putAccountProxyBinding,
  putModelCompactionRoute,
  putModelContextWindowOverride,
  testUpstreamProxyEndpoint,
  updateSettings,
} from "@/features/settings/api";
import type { CompactionRouteUpsertRequest, SettingsUpdateRequest } from "@/features/settings/schemas";
import type {
  AccountProxyBindingRequest,
  UpstreamProxyEndpointCreateRequest,
  UpstreamProxyPoolCreateRequest,
  UpstreamProxyPoolMemberRequest,
} from "@/features/settings/schemas";

export function useSettings() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const { data, error, isFetching, isLoading, isPending, isSuccess, refetch } = useQuery({
    queryKey: ["settings", "detail"],
    queryFn: getSettings,
  });
  const settingsQuery = { data, error, isFetching, isLoading, isPending, isSuccess, refetch };

  const updateSettingsMutation = useMutation({
    mutationFn: (payload: SettingsUpdateRequest) => updateSettings(payload),
    onSuccess: () => {
      toast.success(t("settings.toasts.saved"));
      void queryClient.invalidateQueries({ queryKey: ["settings", "detail"] });
      void queryClient.invalidateQueries({ queryKey: ["settings", "upstream-proxy"] });
    },
    onError: (error: Error) => {
      toast.error(error.message || t("settings.toasts.saveFailed"));
      if (error instanceof ApiError && error.code === "settings_conflict") {
        // Another writer committed since this form was loaded; refetch so the
        // next save carries the fresh expectedVersion.
        void queryClient.invalidateQueries({ queryKey: ["settings", "detail"] });
      }
    },
  });

  return {
    settingsQuery,
    updateSettingsMutation,
  };
}

// `enabled: false` keeps the admin query idle for principals the backend would
// answer with 403 (read-only guests).
export function useUpstreamProxyAdmin(options?: { enabled?: boolean }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const {
    data: upstreamProxyData,
    error: upstreamProxyError,
    isFetching: upstreamProxyIsFetching,
    isLoading: upstreamProxyIsLoading,
    isPending: upstreamProxyIsPending,
    isSuccess: upstreamProxyIsSuccess,
    refetch: refetchUpstreamProxy,
  } = useQuery({
    queryKey: ["settings", "upstream-proxy"],
    queryFn: getUpstreamProxyAdmin,
    enabled: options?.enabled ?? true,
  });
  const upstreamProxyQuery = {
    data: upstreamProxyData,
    error: upstreamProxyError,
    isFetching: upstreamProxyIsFetching,
    isLoading: upstreamProxyIsLoading,
    isPending: upstreamProxyIsPending,
    isSuccess: upstreamProxyIsSuccess,
    refetch: refetchUpstreamProxy,
  };

  const createEndpointMutation = useMutation({
    mutationFn: (payload: UpstreamProxyEndpointCreateRequest) => createUpstreamProxyEndpoint(payload),
    onSuccess: () => {
      toast.success(t("upstreamProxy.toasts.endpointCreated"));
      void queryClient.invalidateQueries({ queryKey: ["settings", "upstream-proxy"] });
      void queryClient.invalidateQueries({ queryKey: ["settings", "detail"] });
    },
    onError: (error: Error) => {
      toast.error(error.message || t("upstreamProxy.toasts.endpointCreateFailed"));
    },
  });

  const createPoolMutation = useMutation({
    mutationFn: (payload: UpstreamProxyPoolCreateRequest) => createUpstreamProxyPool(payload),
    onSuccess: () => {
      toast.success(t("upstreamProxy.toasts.poolCreated"));
      void queryClient.invalidateQueries({ queryKey: ["settings", "upstream-proxy"] });
      void queryClient.invalidateQueries({ queryKey: ["settings", "detail"] });
    },
    onError: (error: Error) => {
      toast.error(error.message || t("upstreamProxy.toasts.poolCreateFailed"));
    },
  });

  const addPoolMemberMutation = useMutation({
    mutationFn: ({ poolId, payload }: { poolId: string; payload: UpstreamProxyPoolMemberRequest }) =>
      addUpstreamProxyPoolMember(poolId, payload),
    onSuccess: () => {
      toast.success(t("upstreamProxy.toasts.memberAdded"));
      void queryClient.invalidateQueries({ queryKey: ["settings", "upstream-proxy"] });
      void queryClient.invalidateQueries({ queryKey: ["settings", "detail"] });
    },
    onError: (error: Error) => {
      toast.error(error.message || t("upstreamProxy.toasts.poolUpdateFailed"));
    },
  });

  const testEndpointMutation = useMutation({
    mutationFn: (endpointId: string) => testUpstreamProxyEndpoint(endpointId),
    onSuccess: (result) => {
      if (result.ok) {
        toast.success(t("upstreamProxy.toasts.endpointReachable"));
      } else {
        toast.error(result.error || t("upstreamProxy.toasts.endpointTestFailed"));
      }
    },
    onError: (error: Error) => {
      toast.error(error.message || t("upstreamProxy.toasts.endpointTestFailed"));
    },
  });

  const accountBindingMutation = useMutation({
    mutationFn: ({ accountId, payload }: { accountId: string; payload: AccountProxyBindingRequest }) =>
      putAccountProxyBinding(accountId, payload),
    onSuccess: () => {
      toast.success(t("upstreamProxy.toasts.accountBindingSaved"));
      void queryClient.invalidateQueries({ queryKey: ["settings", "upstream-proxy"] });
      void queryClient.invalidateQueries({ queryKey: ["settings", "detail"] });
    },
    onError: (error: Error) => {
      toast.error(error.message || t("upstreamProxy.toasts.accountBindingFailed"));
    },
  });

  return {
    upstreamProxyQuery,
    createEndpointMutation,
    createPoolMutation,
    addPoolMemberMutation,
    testEndpointMutation,
    accountBindingMutation,
  };
}

// M4 model catalogue: per-model context window overrides. The list merges
// dashboard rows with the environment fallback per slug; writes go to one slug.
export function useModelContextWindowOverrides() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const queryKey = ["settings", "model-context-window-overrides"] as const;

  const { data, error, isFetching, isLoading, isPending, isSuccess, refetch } = useQuery({
    queryKey,
    queryFn: getModelContextWindowOverrides,
  });
  const overridesQuery = { data, error, isFetching, isLoading, isPending, isSuccess, refetch };

  const upsertMutation = useMutation({
    mutationFn: ({ slug, contextWindow }: { slug: string; contextWindow: number }) =>
      putModelContextWindowOverride(slug, { contextWindow }),
    onSuccess: () => {
      toast.success(t("settings.modelCatalogue.toasts.saved"));
      void queryClient.invalidateQueries({ queryKey });
    },
    onError: (error: Error) => {
      toast.error(error.message || t("settings.modelCatalogue.toasts.saveFailed"));
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (slug: string) => deleteModelContextWindowOverride(slug),
    onSuccess: () => {
      toast.success(t("settings.modelCatalogue.toasts.removed"));
      void queryClient.invalidateQueries({ queryKey });
    },
    onError: (error: Error) => {
      toast.error(error.message || t("settings.modelCatalogue.toasts.removeFailed"));
    },
  });

  return { overridesQuery, upsertMutation, deleteMutation };
}

// Native compaction model routes. The backend validates every write against
// the live catalog and reports each stored route as active or inactive.
export function useModelCompactionRoutes() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const queryKey = ["settings", "model-compaction-routes"] as const;

  const { data, error, isLoading } = useQuery({ queryKey, queryFn: getModelCompactionRoutes });
  const routesQuery = { data, error, isLoading };

  const upsertMutation = useMutation({
    mutationFn: ({ slug, ...payload }: { slug: string } & CompactionRouteUpsertRequest) =>
      putModelCompactionRoute(slug, payload),
    onSuccess: (routes) => {
      toast.success(t("settings.compactionRoutes.toasts.saved"));
      queryClient.setQueryData(queryKey, routes);
    },
    onError: (error: Error) => {
      toast.error(error.message || t("settings.compactionRoutes.toasts.saveFailed"));
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (slug: string) => deleteModelCompactionRoute(slug),
    onSuccess: (routes) => {
      toast.success(t("settings.compactionRoutes.toasts.removed"));
      queryClient.setQueryData(queryKey, routes);
    },
    onError: (error: Error) => {
      toast.error(error.message || t("settings.compactionRoutes.toasts.removeFailed"));
    },
  });

  return { routesQuery, upsertMutation, deleteMutation };
}
