import { Skeleton } from "@/components/ui/skeleton";

/** Placeholder of the keys table while the list loads. */
export function ApisSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-[22rem] w-full rounded-xl" />
      <div className="space-y-px overflow-hidden rounded-xl border bg-card">
        <div className="flex gap-2 border-b px-3 py-2.5">
          <Skeleton className="h-8 w-72 rounded-md" />
          <Skeleton className="h-8 w-80 rounded-md" />
        </div>
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="flex items-center gap-4 border-b px-4 py-3 last:border-b-0">
            <div className="flex-1 space-y-1.5">
              <Skeleton className="h-4 w-40" />
              <Skeleton className="h-3 w-56" />
            </div>
            <Skeleton className="h-5 w-16 rounded-full" />
            <Skeleton className="h-6 w-40" />
            <Skeleton className="h-6 w-28" />
          </div>
        ))}
      </div>
    </div>
  );
}
