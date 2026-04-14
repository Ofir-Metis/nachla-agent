import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import type { IntakeData, Building, TabaData } from "@/types";

/* ────────────────────────────────────────────
   Types
   ──────────────────────────────────────────── */

export type WizardScreen =
  | "intake"
  | "upload"
  | "confirm"
  | "processing"
  | "checkpoint"
  | "results";

interface WizardState {
  formData: Partial<IntakeData>;
  files: Record<string, File | null>;
  jobId: string | null;
  currentScreen: WizardScreen;
  /** True when we hydrated a draft from localStorage on mount */
  hasDraft: boolean;
  /** Buildings extracted from uploaded documents by AI */
  extractedBuildings: Building[];
  /** Tabas extracted from uploaded documents by AI */
  extractedTabas: TabaData[];
  /** Warnings from extraction */
  extractionWarnings: string[];
  /** Whether user chose to skip taba input */
  tabaSkipped: boolean;
}

interface WizardActions {
  updateFormData: (partial: Partial<IntakeData>) => void;
  updateField: <K extends keyof IntakeData>(key: K, value: IntakeData[K]) => void;
  setFile: (slotId: string, file: File | null) => void;
  setJobId: (id: string) => void;
  setCurrentScreen: (screen: WizardScreen) => void;
  setExtractedData: (buildings: Building[], tabas: TabaData[], warnings: string[]) => void;
  updateExtractedBuilding: (id: number, updates: Partial<Building>) => void;
  setTabaData: (tabas: TabaData[]) => void;
  setTabaSkipped: (skipped: boolean) => void;
  reset: () => void;
  clearDraft: () => void;
  dismissDraft: () => void;
}

type WizardContextValue = WizardState & WizardActions;

/* ────────────────────────────────────────────
   Constants
   ──────────────────────────────────────────── */

const STORAGE_KEY = "nachla-draft";
const DEBOUNCE_MS = 500;

const INITIAL_FORM_DATA: Partial<IntakeData> = {
  owner_name: "",
  ownership_type: undefined,
  has_intergenerational_continuity: undefined,
  moshav_name: "",
  gush: undefined,
  helka: undefined,
  authorization_type: undefined,
  is_capitalized: undefined,
  capitalization_track: "none",
  num_existing_houses: 2,
  client_goals: [],
  has_demolition_orders: undefined,
};

/* ────────────────────────────────────────────
   Context
   ──────────────────────────────────────────── */

const WizardContext = createContext<WizardContextValue | null>(null);

/* ────────────────────────────────────────────
   Provider
   ──────────────────────────────────────────── */

function loadDraft(): Partial<IntakeData> | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as Partial<IntakeData>;
  } catch {
    return null;
  }
}

function saveDraft(data: Partial<IntakeData>) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch {
    // localStorage full or unavailable — silently ignore
  }
}

export function WizardProvider({ children }: { children: ReactNode }) {
  const draft = loadDraft();

  const [formData, setFormData] = useState<Partial<IntakeData>>(
    draft ?? { ...INITIAL_FORM_DATA },
  );
  const [files, setFiles] = useState<Record<string, File | null>>({});
  const [jobId, setJobIdState] = useState<string | null>(null);
  const [currentScreen, setCurrentScreen] = useState<WizardScreen>("intake");
  const [hasDraft, setHasDraft] = useState<boolean>(draft !== null);
  const [extractedBuildings, setExtractedBuildings] = useState<Building[]>([]);
  const [extractedTabas, setExtractedTabas] = useState<TabaData[]>([]);
  const [tabaSkipped, setTabaSkippedState] = useState(false);
  const [extractionWarnings, setExtractionWarnings] = useState<string[]>([]);

  // Debounced localStorage persistence
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      saveDraft(formData);
    }, DEBOUNCE_MS);
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [formData]);

  const updateFormData = useCallback((partial: Partial<IntakeData>) => {
    setFormData((prev) => ({ ...prev, ...partial }));
  }, []);

  const updateField = useCallback(
    <K extends keyof IntakeData>(key: K, value: IntakeData[K]) => {
      setFormData((prev) => ({ ...prev, [key]: value }));
    },
    [],
  );

  const setFile = useCallback((slotId: string, file: File | null) => {
    setFiles((prev) => {
      const next = { ...prev };
      if (file) {
        next[slotId] = file;
      } else {
        delete next[slotId];
      }
      return next;
    });
  }, []);

  const setJobId = useCallback((id: string) => {
    setJobIdState(id);
  }, []);

  const setTabaData = useCallback((tabas: TabaData[]) => {
    setExtractedTabas(tabas);
    setTabaSkippedState(false);
  }, []);

  const setTabaSkipped = useCallback((skipped: boolean) => {
    setTabaSkippedState(skipped);
  }, []);

  const setExtractedData = useCallback((buildings: Building[], tabas: TabaData[], warnings: string[]) => {
    setExtractedBuildings(buildings);
    setExtractedTabas(tabas);
    setExtractionWarnings(warnings);
  }, []);

  const updateExtractedBuilding = useCallback((id: number, updates: Partial<Building>) => {
    setExtractedBuildings((prev) =>
      prev.map((b) => (b.id === id ? { ...b, ...updates } : b))
    );
  }, []);

  const reset = useCallback(() => {
    setFormData({ ...INITIAL_FORM_DATA });
    setFiles({});
    setJobIdState(null);
    setCurrentScreen("intake");
    setHasDraft(false);
    setExtractedBuildings([]);
    setExtractedTabas([]);
    setExtractionWarnings([]);
    setTabaSkippedState(false);
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      // ignore
    }
  }, []);

  const clearDraft = useCallback(() => {
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      // ignore
    }
  }, []);

  const dismissDraft = useCallback(() => {
    setHasDraft(false);
  }, []);

  return (
    <WizardContext.Provider
      value={{
        formData,
        files,
        jobId,
        currentScreen,
        hasDraft,
        extractedBuildings,
        extractedTabas,
        extractionWarnings,
        tabaSkipped,
        updateFormData,
        updateField,
        setFile,
        setJobId,
        setCurrentScreen,
        setExtractedData,
        updateExtractedBuilding,
        setTabaData,
        setTabaSkipped,
        reset,
        clearDraft,
        dismissDraft,
      }}
    >
      {children}
    </WizardContext.Provider>
  );
}

/* ────────────────────────────────────────────
   Hook
   ──────────────────────────────────────────── */

export function useWizardContext(): WizardContextValue {
  const ctx = useContext(WizardContext);
  if (!ctx) {
    throw new Error("useWizardContext must be used inside <WizardProvider>");
  }
  return ctx;
}
