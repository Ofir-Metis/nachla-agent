import { useQuery } from "@tanstack/react-query";
import { fetchJobStatus } from "@/lib/api";
import type { JobStatusResponse, JobState } from "@/types";

/** The 6 user-visible phases and the backend phases that map to each. */
/** Maps the 16 backend WorkflowPhase values to 6 UI groups.
 *  Backend phases from src/agent/workflow.py lines 19-37. */
const PHASE_GROUPS: { id: string; backendPhases: string[] }[] = [
  {
    id: "intake",
    backendPhases: ["intake"],
  },
  {
    id: "taba_analysis",
    backendPhases: ["taba_analysis"],
  },
  {
    id: "building_mapping",
    backendPhases: ["building_mapping"],
  },
  {
    id: "classification_checkpoint",
    backendPhases: ["classification", "checkpoint"],
  },
  {
    id: "calculations",
    backendPhases: [
      "usage_fees",
      "sqm_equivalent",
      "hivun",
      "regularization",
      "split",
      "agricultural",
      "betterment",
    ],
  },
  {
    id: "report",
    backendPhases: ["report", "review", "export", "complete"],
  },
];

export type PhaseStatus = "completed" | "running" | "pending" | "checkpoint" | "failed";

export interface PhaseInfo {
  id: string;
  status: PhaseStatus;
  progressPercent?: number;
  timeEstimate?: string;
}

function resolvePhaseIndex(backendPhase: string): number {
  for (let i = 0; i < PHASE_GROUPS.length; i++) {
    if (PHASE_GROUPS[i].backendPhases.includes(backendPhase)) {
      return i;
    }
  }
  // Default: if unknown phase, assume it is in calculations
  return 4;
}

const TIME_ESTIMATES: Record<string, string> = {
  intake: "~ 10 שניות",
  taba_analysis: "~ 30 שניות",
  building_mapping: "~ דקה אחת",
  classification_checkpoint: "ממתין לאישור",
  calculations: "~ 20 שניות",
  report: "~ דקה אחת",
};

function derivePhases(data: JobStatusResponse | undefined): PhaseInfo[] {
  if (!data) {
    return PHASE_GROUPS.map((g) => ({
      id: g.id,
      status: "pending" as PhaseStatus,
    }));
  }

  const activeIndex = resolvePhaseIndex(data.phase);

  return PHASE_GROUPS.map((group, i) => {
    let status: PhaseStatus;
    let progressPercent: number | undefined;
    let timeEstimate: string | undefined;

    if (data.status === "failed" && i === activeIndex) {
      status = "failed";
    } else if (i < activeIndex) {
      status = "completed";
    } else if (i === activeIndex) {
      if (data.status === "checkpoint") {
        status = "checkpoint";
      } else if (data.status === "complete") {
        status = "completed";
      } else {
        status = "running";
        progressPercent = data.progress_percent;
        timeEstimate = TIME_ESTIMATES[group.id];
      }
    } else {
      status = "pending";
    }

    return { id: group.id, status, progressPercent, timeEstimate };
  });
}

export function useJobPolling(jobId: string | undefined) {
  const { data, isLoading, error } = useQuery<JobStatusResponse>({
    queryKey: ["job-status", jobId],
    queryFn: () => fetchJobStatus(jobId!),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "complete" || status === "failed") return false;
      return 2000;
    },
    enabled: !!jobId,
  });

  const status: JobState | undefined = data?.status;
  const phases = derivePhases(data);

  return {
    data,
    isLoading,
    error,
    phases,
    isCheckpoint: status === "checkpoint",
    isComplete: status === "complete",
    isFailed: status === "failed",
  };
}
