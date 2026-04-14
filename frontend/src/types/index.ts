/** TypeScript interfaces mirroring Python Pydantic models */

export type AuthorizationType =
  | "bar_reshut"
  | "chocher"
  | "choze_chachira_mehuvon";
export type CapitalizationTrack = "375" | "33" | "none";
export type ClientGoal = "regularization" | "capitalization" | "split" | "all";
export type OwnershipType = "single" | "partners" | "heirs";

export type PriorityArea = "none" | "A" | "B" | "frontline";

export interface IntakeData {
  owner_name: string;
  moshav_name: string;
  gush: number;
  helka: number;
  num_existing_houses: number;
  authorization_type: AuthorizationType;
  is_capitalized: boolean;
  capitalization_track: CapitalizationTrack;
  client_goals: ClientGoal[];
  has_intergenerational_continuity: boolean;
  ownership_type: OwnershipType;
  has_demolition_orders: boolean;
  priority_area?: PriorityArea;
  prior_permit_fees_purchased?: number;
  prior_permit_fees_date?: number;
}

export type BuildingType =
  | "residential"
  | "service"
  | "agricultural"
  | "plach"
  | "pergola"
  | "pool"
  | "basement_service"
  | "basement_residential"
  | "attic"
  | "ground_floor_open"
  | "ground_floor_closed"
  | "temporary"
  | "shed_open"
  | "pre_1965";

export type BuildingStatus =
  | "compliant"
  | "deviation"
  | "no_permit"
  | "marked_demolition"
  | "building_line_violation";

export interface Building {
  id: number;
  name: string;
  building_type: BuildingType;
  status: BuildingStatus;
  main_area_sqm: number;
  total_area_sqm: number;
  deviation_sqm?: number;
  user_confirmed: boolean;
}

export interface DocumentClassification {
  filename: string;
  detected_type: string;
  is_relevant: boolean;
  confidence: string;
  note: string;
}

export type TabaStatus = "approved" | "in_process" | "deposited";

export interface TabaData {
  taba_number: string;
  taba_name: string;
  status: TabaStatus;
  approval_date?: string;
  plot_id?: string;
  plot_size_sqm: number;
  num_units_allowed: number;
  main_area_sqm: number;
  service_area_sqm: number;
  plach_area_sqm?: number;
  split_allowed: boolean;
  split_min_plot_sqm?: number;
  pool_allowed?: boolean;
  attached_unit_allowed?: boolean;
  source: "govmap" | "pdf_extraction" | "manual";
  is_primary: boolean;
}

export interface ExtractionResponse {
  buildings: Building[];
  tabas: Record<string, unknown>[];
  building_count: number;
  taba_count: number;
  warnings: string[];
  document_classifications: DocumentClassification[];
}

export type JobState =
  | "pending"
  | "running"
  | "checkpoint"
  | "generating"
  | "complete"
  | "failed";

export interface JobStatusResponse {
  job_id: string;
  status: JobState;
  phase: string;
  progress_percent: number;
  message: string;
  sub_steps?: { name: string; status: string }[];
}

export interface JobCreateResponse {
  job_id: string;
  status: string;
  message: string;
}

export interface BuildingCostCard {
  building_id: number;
  building_name: string;
  status_description: string;
  action: string;
  permit_fees: number;
  usage_fees: number;
  betterment_levy: number;
  total_cost: number;
}

export interface CostSummary {
  total_regularization_cost: number;
  total_usage_fees: number;
  total_permit_fees: number;
  betterment_levy: number;
  hivun_375_total?: number;
  hivun_33_total?: number;
  building_cards?: BuildingCostCard[];
}

export interface JobSummary {
  job_id: string;
  owner_name: string;
  moshav_name: string;
  status: JobState;
  phase: string;
  created_at: string;
  completed_at?: string;
  total_cost?: number;
}
