import type { IntakeData, JobStatusResponse, JobCreateResponse, Building, CostSummary, JobSummary } from "@/types";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${url}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!res.ok) {
    const detail = await res.text().catch(() => "");
    const messages: Record<number, string> = {
      400: "הנתונים שהוזנו אינם תקינים. אנא בדקו ונסו שנית.",
      401: "אין הרשאה. אנא התחברו מחדש.",
      403: "אין לכם גישה לפעולה זו.",
      404: "המשאב המבוקש לא נמצא.",
      409: "קיים קונפליקט — ייתכן שהמשימה כבר בביצוע.",
      422: "הנתונים שהוזנו אינם בפורמט הנכון.",
      500: "שגיאת שרת פנימית. אנא נסו שוב מאוחר יותר.",
      502: "השרת אינו זמין כרגע. אנא נסו שוב בעוד מספר דקות.",
      503: "השירות אינו זמין כרגע. אנא נסו שוב בעוד מספר דקות.",
    };
    throw new ApiError(
      messages[res.status] ?? `שגיאה בלתי צפויה (${res.status}): ${detail}`,
      res.status,
    );
  }

  if (res.status === 204 || res.headers.get("content-length") === "0") {
    return undefined as T;
  }

  return res.json() as Promise<T>;
}

/** POST /api/v1/jobs — submit intake data and create a new job */
export async function submitIntake(data: IntakeData): Promise<JobCreateResponse> {
  return request<JobCreateResponse>("/api/v1/jobs", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

/** POST /api/v1/jobs/{id}/files — upload files as multipart FormData */
export async function uploadFiles(
  jobId: string,
  files: Record<string, File>,
): Promise<void> {
  const formData = new FormData();
  for (const [_key, file] of Object.entries(files)) {
    // Backend expects all files under the "files" field name (FastAPI: list[UploadFile])
    formData.append("files", file);
  }

  const res = await fetch(`${BASE_URL}/api/v1/jobs/${jobId}/files`, {
    method: "POST",
    body: formData,
    // No Content-Type header — browser sets multipart boundary automatically
  });

  if (!res.ok) {
    throw new ApiError("שגיאה בהעלאת הקבצים. אנא נסו שנית.", res.status);
  }
}

/** POST /api/v1/jobs/{id}/files — upload with progress via XMLHttpRequest */
export function uploadFilesWithProgress(
  jobId: string,
  files: Record<string, File>,
  onProgress: (percent: number) => void,
): Promise<void> {
  return new Promise((resolve, reject) => {
    const formData = new FormData();
    for (const [_key, file] of Object.entries(files)) {
      formData.append("files", file);
    }

    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${BASE_URL}/api/v1/jobs/${jobId}/files`);

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    });

    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve();
      } else {
        reject(new ApiError("שגיאה בהעלאת הקבצים. אנא נסו שנית.", xhr.status));
      }
    });

    xhr.addEventListener("error", () => {
      reject(new ApiError("שגיאה בהעלאת הקבצים. אנא נסו שנית.", 0));
    });

    xhr.send(formData);
  });
}

/** GET /api/v1/jobs/{id}/status — poll job progress */
export async function fetchJobStatus(jobId: string): Promise<JobStatusResponse> {
  return request<JobStatusResponse>(`/api/v1/jobs/${jobId}/status`);
}

/** GET /api/v1/jobs/{id}/buildings — fetch building list for classification */
export async function fetchBuildings(jobId: string): Promise<Building[]> {
  const resp = await request<{ job_id: string; buildings: Building[]; count: number }>(
    `/api/v1/jobs/${jobId}/buildings`,
  );
  return resp.buildings;
}

/** POST /api/v1/jobs/{id}/classify/confirm — confirm building classification */
export async function confirmClassification(
  jobId: string,
  buildings: Building[],
): Promise<void> {
  await request<void>(`/api/v1/jobs/${jobId}/classify/confirm`, {
    method: "POST",
    body: JSON.stringify({ buildings }),
  });
}

/** GET /api/v1/jobs/{id}/results — fetch cost summary */
export async function fetchResults(jobId: string): Promise<CostSummary> {
  return request<CostSummary>(`/api/v1/jobs/${jobId}/results`);
}

/** Returns the download URL for a given file type (word, excel, pdf, audit_log) */
export function getDownloadUrl(jobId: string, fileType: string): string {
  return `${BASE_URL}/api/v1/jobs/${jobId}/download/${fileType}`;
}

/** Mock data fallback for development when backend doesn't have GET /api/v1/jobs yet */
const MOCK_JOBS: JobSummary[] = [
  {
    job_id: "demo-001",
    owner_name: "יוסי כהן",
    moshav_name: "נהלל",
    status: "checkpoint",
    phase: "classification_checkpoint",
    created_at: "2026-03-28T10:30:00Z",
  },
  {
    job_id: "demo-002",
    owner_name: "שרה לוי",
    moshav_name: "כפר ורבורג",
    status: "running",
    phase: "taba_analysis",
    created_at: "2026-04-01T08:15:00Z",
  },
  {
    job_id: "demo-003",
    owner_name: "דוד אברהם",
    moshav_name: "בית חרות",
    status: "complete",
    phase: "report",
    created_at: "2026-03-15T14:00:00Z",
    completed_at: "2026-03-18T16:45:00Z",
    total_cost: 287_450,
  },
  {
    job_id: "demo-004",
    owner_name: "רחל מזרחי",
    moshav_name: "גן יאשיה",
    status: "complete",
    phase: "report",
    created_at: "2026-02-20T09:00:00Z",
    completed_at: "2026-02-23T11:30:00Z",
    total_cost: 154_200,
  },
];

/** GET /api/v1/jobs — list all jobs (falls back to mock data in development only) */
export async function fetchJobs(): Promise<JobSummary[]> {
  try {
    return await request<JobSummary[]>("/api/v1/jobs");
  } catch (err) {
    if (import.meta.env.DEV) {
      return MOCK_JOBS;
    }
    throw err;
  }
}

/** DELETE /api/v1/jobs/{id} — delete a job */
export async function deleteJob(jobId: string): Promise<void> {
  return request<void>(`/api/v1/jobs/${jobId}`, { method: "DELETE" });
}

/** POST /api/v1/jobs/{id}/cloud-export/{target} — export reports to cloud storage */
export async function cloudExport(
  jobId: string,
  target: "gdrive" | "onedrive" | "all",
): Promise<{ status: string; message: string; files: { service: string; file: string; link: string }[] }> {
  return request(`/api/v1/jobs/${jobId}/cloud-export/${target}`, {
    method: "POST",
  });
}
