import type { JobSummary } from "@/types";
import JobCard from "./JobCard";

interface JobSectionProps {
  title: string;
  jobs: JobSummary[];
  emptyText: string;
  type: "progress" | "completed";
  selectedIds: Set<string>;
  onSelect: (jobId: string) => void;
  onAction: (job: JobSummary) => void;
}

export default function JobSection({
  title,
  jobs,
  emptyText,
  type,
  selectedIds,
  onSelect,
  onAction,
}: JobSectionProps) {
  return (
    <section className="mb-8">
      <div className="flex items-center gap-2 mb-3">
        <h2 className="font-heading text-[1.1rem] font-semibold text-olive-800">
          {title}
        </h2>
        {jobs.length > 0 && (
          <span className="text-[0.8rem] text-soil-500">
            ({jobs.length})
          </span>
        )}
      </div>

      {jobs.length === 0 ? (
        <div className="bg-white/60 border border-dashed border-[#D8D0C4] rounded-[--radius-md] py-8 text-center text-soil-500 text-[0.9rem]">
          {emptyText}
        </div>
      ) : (
        <div className="flex flex-col gap-2.5">
          {jobs.map((job) => (
            <JobCard
              key={job.job_id}
              job={job}
              selected={selectedIds.has(job.job_id)}
              onSelect={onSelect}
              onAction={onAction}
              type={type}
            />
          ))}
        </div>
      )}
    </section>
  );
}
