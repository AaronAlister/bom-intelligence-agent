export type BOMComponent = {
  /*
   * component_id is the database primary key of the persisted component.
   * It is NOT returned by the ingestion API; it is populated after the
   * component is saved to the database. Use it when calling the
   * component-specific endpoints (e.g., /components/{id}/alternatives).
   */
  component_id: number;
  mpn: string;
  manufacturer: string | null;
  description: string | null;
  category: string | null;
  package: string | null;
  quantity: number;
  reference_designators: string[];
};

export type ValidationIssue = {
  row_number: number;
  field: string;
  message: string;
  severity: string;
};

export type IngestionResult = {
  bom_id: string;

  /*
   * Database primary key used by component/risk APIs.
   *
   * This is different from bom_id, which is the public
   * UUID assigned to the uploaded BOM.
   */
  bom_database_id: number;

  source_file: string;
  source_format: string;

  metadata: {
    bom_id: string;
    bom_database_id: number;
    product: string | null;
    revision: string | null;
    source_file: string;
    source_format: string;
    ingested_at: string;
  };

  total_rows: number;
  valid_rows: number;
  invalid_rows: number;

  components: BOMComponent[];

  validation_issues: ValidationIssue[];
};

export type RiskSeverity = "UNKNOWN" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type BOMRiskComponent = {
  component_id: number;
  mpn: string;
  quantity: number;
  score: number;
  severity: RiskSeverity;
  lifecycle_risk: boolean;
  availability_risk: boolean;
};

export type BOMRiskDriver = {
  component_id: number;
  mpn: string;
  score: number;
  severity: RiskSeverity;
  reason: string;
};

export type BOMRiskRecommendation = {
  priority: RiskSeverity;
  component_id: number | null;
  mpn: string | null;
  action: string;
  reason: string;
};

export type BOMRisk = {
  bom_id: number;

  overall_score: number;
  severity: RiskSeverity;

  component_count: number;
  high_risk_count: number;
  critical_count: number;

  lifecycle_risk_count: number;
  availability_risk_count: number;

  top_risk_components: BOMRiskComponent[];

  summary: string;

  risk_drivers: BOMRiskDriver[];

  recommendations: BOMRiskRecommendation[];
};

/* ============================================================
   BOM REPORT
   ============================================================ */

export type BOMReportComponent = {
  component_id: number;
  mpn: string;
  manufacturer: string | null;
  quantity: number;
  score: number;
  severity: RiskSeverity;
  lifecycle_risk: boolean;
  availability_risk: boolean;
};

export type BOMReportRiskDriver = {
  component_id: number;
  mpn: string;
  score: number;
  severity: RiskSeverity;
  reason: string;
};

export type BOMReportRecommendation = {
  priority: RiskSeverity;
  component_id: number | null;
  mpn: string | null;
  action: string;
  reason: string;
};

export type BOMReportLifecycle = {
  active_count: number;
  nrnd_count: number;
  eol_count: number;
  obsolete_count: number;
  unknown_count: number;
  lifecycle_risk_count: number;
};

export type BOMReportAvailability = {
  availability_risk_count: number;
  components_with_availability: number;
  components_without_availability: number;
};

export type BOMReport = {
  bom_id: number;

  generated_at: string;

  product: string | null;
  revision: string | null;
  source_file: string | null;
  source_format: string | null;

  component_count: number;
  total_quantity: number;

  overall_score: number;
  severity: RiskSeverity;

  high_risk_count: number;
  critical_count: number;
  lifecycle_risk_count: number;
  availability_risk_count: number;

  summary: string;

  lifecycle: BOMReportLifecycle;

  availability: BOMReportAvailability;

  top_risk_components: BOMReportComponent[];

  risk_drivers: BOMReportRiskDriver[];

  recommendations: BOMReportRecommendation[];
};
