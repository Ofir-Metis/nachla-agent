import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import type { JobSummary } from "@/types";
import { fetchJobs, deleteJob } from "@/lib/api";
import FocusManager from "@/components/ui/FocusManager";
import JobSection from "@/components/dashboard/JobSection";
import DeleteBar from "@/components/dashboard/DeleteBar";
import DeleteConfirmModal from "@/components/dashboard/DeleteConfirmModal";

/** Map phase to the route the user should land on when clicking "continue" */
function getPhaseRoute(job: JobSummary): string {
  const id = job.job_id;
  switch (job.phase) {
    case "intake":
      return "/intake";
    case "taba_analysis":
    case "building_mapping":
    case "calculations":
    case "report":
      return `/jobs/${id}/processing`;
    case "classification_checkpoint":
      return `/jobs/${id}/checkpoint`;
    default:
      return `/jobs/${id}/processing`;
  }
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [showDeleteModal, setShowDeleteModal] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchJobs()
      .then((data) => {
        if (!cancelled) setJobs(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message ?? "שגיאה בטעינת הבדיקות");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  const inProgress = jobs.filter((j) => j.status !== "complete");
  const completed = jobs.filter((j) => j.status === "complete");
  const hasAnyJobs = jobs.length > 0;

  const toggleSelect = useCallback((jobId: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(jobId)) next.delete(jobId);
      else next.add(jobId);
      return next;
    });
  }, []);

  const clearSelection = useCallback(() => {
    setSelectedIds(new Set());
  }, []);

  const handleAction = useCallback(
    (job: JobSummary) => {
      if (job.status === "complete") {
        navigate(`/jobs/${job.job_id}/results`);
      } else {
        navigate(getPhaseRoute(job));
      }
    },
    [navigate],
  );

  const handleDeleteConfirm = useCallback(async () => {
    const idsToDelete = Array.from(selectedIds);
    setShowDeleteModal(false);

    // Delete all selected jobs (best effort)
    const results = await Promise.allSettled(
      idsToDelete.map((id) => deleteJob(id)),
    );

    // Remove successfully deleted jobs from state
    const deletedIds = new Set<string>();
    results.forEach((r, i) => {
      if (r.status === "fulfilled") deletedIds.add(idsToDelete[i]);
    });

    setJobs((prev) => prev.filter((j) => !deletedIds.has(j.job_id)));
    setSelectedIds(new Set());
  }, [selectedIds]);

  return (
    <FocusManager focusKey="dashboard">
      <div className="pb-20">
        <h1
          tabIndex={-1}
          className="font-heading text-[1.5rem] font-bold text-olive-800 mb-6 outline-none"
        >
          הבדיקות שלי
        </h1>

        {/* Hero start button */}
        <div className="flex justify-center mb-6 sm:mb-8">
          <button
            type="button"
            onClick={() => navigate("/intake")}
            className="
              w-full max-w-md py-3.5 sm:py-4 text-base sm:text-lg font-bold
              bg-olive-700 text-white rounded-[--radius-md]
              shadow-[--shadow-md] transition-all duration-200
              hover:bg-olive-800 hover:shadow-[--shadow-lg] hover:-translate-y-0.5
              active:translate-y-0 cursor-pointer
            "
          >
            התחל בדיקה חדשה
          </button>
        </div>

        {/* Loading state */}
        {loading && (
          <div className="text-center py-12 text-soil-500 text-[0.9rem] animate-[shimmer-pulse_1.5s_ease-in-out_infinite]">
            טוען בדיקות...
          </div>
        )}

        {/* Error state */}
        {error && !loading && (
          <div className="bg-error/10 border border-error/20 rounded-[--radius-md] p-4 text-error text-[0.9rem] text-center mb-6">
            {error}
          </div>
        )}

        {/* Empty welcome state */}
        {!loading && !error && !hasAnyJobs && (
          <div className="text-center py-16">
            <div className="text-soil-500 text-[1.05rem] leading-relaxed">
              ברוכים הבאים! התחילו בדיקת התכנות חדשה
            </div>
          </div>
        )}

        {/* Job lists */}
        {!loading && !error && hasAnyJobs && (
          <>
            <JobSection
              title="בדיקות בתהליך"
              jobs={inProgress}
              emptyText="אין בדיקות בתהליך"
              type="progress"
              selectedIds={selectedIds}
              onSelect={toggleSelect}
              onAction={handleAction}
            />

            <JobSection
              title="בדיקות שהושלמו"
              jobs={completed}
              emptyText="אין בדיקות שהושלמו"
              type="completed"
              selectedIds={selectedIds}
              onSelect={toggleSelect}
              onAction={handleAction}
            />
          </>
        )}

        {/* Delete action bar */}
        <DeleteBar
          count={selectedIds.size}
          onDelete={() => setShowDeleteModal(true)}
          onCancel={clearSelection}
        />

        {/* Delete confirmation modal */}
        {showDeleteModal && (
          <DeleteConfirmModal
            count={selectedIds.size}
            onConfirm={handleDeleteConfirm}
            onCancel={() => setShowDeleteModal(false)}
          />
        )}
      </div>
    </FocusManager>
  );
}
