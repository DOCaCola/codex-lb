import { Skeleton } from "@/components/ui/skeleton";

function SectionHeaderSkeleton({ titleWidth, control }: { titleWidth: string; control: string }) {
  return (
    <div className="flex min-h-[30px] items-center gap-2.5">
      <Skeleton className={`h-4 ${titleWidth}`} />
      <span className="flex-1" />
      <Skeleton className={`h-7 ${control} rounded-md`} />
    </div>
  );
}

/** Placeholder matching the loaded dashboard: quota, accounts and activity. */
export function DashboardSkeleton() {
  return (
    <div className="space-y-7">
      <section className="flex flex-col gap-2.5">
        <SectionHeaderSkeleton titleWidth="w-16" control="w-40" />
        <div className="@container/quota">
          <div className="grid gap-4 @min-[44rem]/quota:grid-cols-2 @min-[74rem]/quota:grid-cols-[minmax(0,1.55fr)_minmax(0,1fr)_minmax(0,1fr)]">
            {Array.from({ length: 3 }).map((_, card) => (
              <div key={card} className="flex min-h-56 flex-col gap-4 rounded-xl border bg-card p-4 shadow-xs">
                <div className="space-y-1.5">
                  <Skeleton className="h-4 w-32" />
                  <Skeleton className="h-3 w-44" />
                </div>
                <div className="flex items-center gap-4">
                  <Skeleton className="h-24 w-24 shrink-0 rounded-full" />
                  <div className="flex-1 space-y-2.5">
                    {Array.from({ length: 4 }).map((_, row) => (
                      <div key={row} className="flex items-center justify-between gap-3">
                        <Skeleton className="h-3 w-28" />
                        <Skeleton className="h-3 w-10" />
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="flex flex-col gap-2.5">
        <SectionHeaderSkeleton titleWidth="w-20" control="w-16" />
        <div className="grid grid-cols-[repeat(auto-fill,minmax(min(300px,100%),1fr))] gap-3">
          {Array.from({ length: 3 }).map((_, card) => (
            <div key={card} className="flex flex-col gap-[11px] rounded-xl border bg-card px-3.5 pt-[13px] pb-[11px] shadow-xs">
              <div className="flex items-center gap-2.5">
                <Skeleton className="h-8 w-8 rounded-lg" />
                <div className="flex-1 space-y-1.5">
                  <Skeleton className="h-3.5 w-32" />
                  <Skeleton className="h-3 w-24" />
                </div>
                <Skeleton className="h-6 w-12" />
              </div>
              {Array.from({ length: 2 }).map((_, row) => (
                <div key={row} className="flex items-center gap-2">
                  <Skeleton className="h-3 w-12" />
                  <Skeleton className="h-1.5 flex-1 rounded-full" />
                  <Skeleton className="h-3 w-16" />
                </div>
              ))}
              <div className="flex min-h-[34px] items-center border-t pt-[9px]">
                <Skeleton className="h-3 w-28" />
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="flex flex-col gap-2.5">
        <SectionHeaderSkeleton titleWidth="w-16" control="w-28" />
        <div className="@container/kpis overflow-hidden rounded-xl border bg-card shadow-xs">
          <div className="-mt-px -ml-px grid grid-cols-2 @min-[33rem]/kpis:grid-cols-3 @min-[54rem]/kpis:auto-cols-fr @min-[54rem]/kpis:grid-flow-col @min-[54rem]/kpis:grid-cols-none">
            {Array.from({ length: 5 }).map((_, stat) => (
              <div key={stat} className="flex flex-col gap-1.5 border-t border-l px-4 pt-[13px] pb-2.5">
                <Skeleton className="h-3 w-20" />
                <Skeleton className="h-6 w-16" />
                <Skeleton className="h-[26px] w-full" />
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
