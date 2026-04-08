/** Hebrew label constants — extracted from src/ui/components.py */

export const BUILDING_TYPE_LABELS: Record<string, string> = {
  residential: "בית מגורים",
  service: "מבנה שירות / מחסן",
  agricultural: "מבנה חקלאי / סככה",
  plach: 'מבנה פל"ח (עסקי)',
  pergola: "פרגולה",
  pool: "בריכת שחייה",
  basement_service: "מרתף שירות",
  basement_residential: "מרתף מגורים",
  attic: "עליית גג",
  ground_floor_open: "קומת עמודים פתוחה",
  ground_floor_closed: "קומת עמודים סגורה",
  temporary: "מבנה ארעי/קל/נייד",
  shed_open: "סככה פתוחה",
  pre_1965: "מבנה לפני 1965",
};

export const BUILDING_STATUS_LABELS: Record<string, string> = {
  compliant: "תקין - תואם היתר",
  deviation: "חריגה מהיתר",
  no_permit: "ללא היתר",
  marked_demolition: "סומן להריסה",
  building_line_violation: "חורג מקווי בניין",
};

export const AUTH_TYPE_LABELS: Record<string, string> = {
  bar_reshut: "בר רשות",
  chocher: "חוכר לדורות",
  choze_chachira_mehuvon: "חוזה חכירה מהוון",
};

export const AUTH_TYPE_DESCRIPTIONS: Record<string, string> = {
  bar_reshut:
    "הסטטוס הנפוץ ביותר. שימו לב: לא ניתן לפצל ללא הסדרת חוזה חכירה.",
  chocher: 'קיים חוזה חכירה עם רמ"י.',
  choze_chachira_mehuvon: 'בעלות מלאה עם תשלום מהוון לרמ"י.',
};

export const CLIENT_GOAL_LABELS: Record<string, string> = {
  regularization: "הסדרה",
  capitalization: "היוון",
  split: "פיצול",
  all: "בדיקה מקיפה",
};

export const CLIENT_GOAL_DESCRIPTIONS: Record<string, string> = {
  regularization: "עדכון היתרים קיימים",
  capitalization: "רכישת זכויות בנייה",
  split: "פיצול מגרש מהנחלה",
  all: "כל האפשרויות",
};

export const CLIENT_GOAL_ICONS: Record<string, string> = {
  regularization: "\u{1F4CB}",
  capitalization: "\u{1F4B0}",
  split: "\u2702",
  all: "\u{1F31F}",
};

export const OWNERSHIP_TYPE_LABELS: Record<string, string> = {
  single: "בעלים יחיד",
  partners: "שותפים",
  heirs: "יורשים",
};

export const OWNERSHIP_TYPE_DESCRIPTIONS: Record<string, string> = {
  single: "בעל נחלה אחד",
  partners: "מספר שותפים בנחלה",
  heirs: "בעלות שהועברה בירושה",
};

export const PRIORITY_AREA_LABELS: Record<string, string> = {
  none: "ללא אזור עדיפות",
  A: "אזור עדיפות א'",
  B: "אזור עדיפות ב'",
  frontline: "קו עימות",
};

export const MOSHAV_PRIORITY_MAP: Record<string, string> = {
  "נהלל": "none",
  "כפר ורבורג": "none",
  "בית חרות": "none",
  "גן יאשיה": "none",
  "כפר יהושע": "none",
  "נחלת יהודה": "none",
  "עין ורד": "none",
  "גבעת עדה": "none",
  "כפר הרואה": "none",
  "בניאמינה": "none",
  "פרדס חנה": "none",
  "זכרון יעקב": "none",
};

export const PHASE_LABELS: Record<string, string> = {
  intake: "קליטת לקוח",
  taba_analysis: 'ניתוח תב"ע',
  building_mapping: "מיפוי מבנים",
  classification_checkpoint: "אישור סיווג מבנים",
  calculations: "חישוב עלויות",
  report: "הפקת דוח",
};
