import { useInfiniteQuery } from "@tanstack/react-query";

import { getConversationTrace } from "@/features/dashboard/api";

export const CONVERSATION_TRACE_PAGE_SIZE = 50;

export function useConversationTrace(conversationId: string | null, enabled = true) {
  return useInfiniteQuery({
    queryKey: ["dashboard", "conversation-trace", conversationId],
    queryFn: ({ pageParam }) =>
      getConversationTrace(conversationId ?? "", { limit: CONVERSATION_TRACE_PAGE_SIZE, offset: pageParam }),
    initialPageParam: 0,
    getNextPageParam: (lastPage, pages) =>
      lastPage.hasMore ? pages.reduce((count, page) => count + page.requests.length, 0) : undefined,
    enabled: enabled && Boolean(conversationId),
    retry: false,
  });
}
