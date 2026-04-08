import { z } from "zod";

/* ────────────────────────────────────────────
   Full 12-field intake schema
   ──────────────────────────────────────────── */

export const intakeSchema = z
  .object({
    owner_name: z.string().min(1, "שדה חובה"),
    moshav_name: z.string().min(1, "שדה חובה"),
    gush: z.coerce.number().int().positive("מספר גוש חייב להיות חיובי"),
    helka: z.coerce.number().int().positive("מספר חלקה חייב להיות חיובי"),
    num_existing_houses: z.number().int().min(0).max(10),
    authorization_type: z.enum([
      "bar_reshut",
      "chocher",
      "choze_chachira_mehuvon",
    ]),
    is_capitalized: z.boolean(),
    capitalization_track: z.enum(["375", "33", "none"]),
    client_goals: z
      .array(z.enum(["regularization", "capitalization", "split", "all"]))
      .min(1, "יש לבחור לפחות מטרה אחת"),
    has_intergenerational_continuity: z.boolean(),
    ownership_type: z.enum(["single", "partners", "heirs"]),
    has_demolition_orders: z.boolean(),
    // Optional fields
    priority_area: z.enum(["none", "A", "B", "frontline"]).optional(),
    prior_permit_fees_purchased: z.number().nonnegative().optional(),
    prior_permit_fees_date: z.number().int().min(2000).max(2100).optional(),
  })
  .refine(
    (data) => {
      if (!data.is_capitalized && data.capitalization_track !== "none") {
        return false;
      }
      return true;
    },
    {
      message: 'כאשר המשק לא מהוון, מסלול ההיוון חייב להיות "ללא"',
      path: ["capitalization_track"],
    }
  )
  .refine(
    (data) => {
      if (data.is_capitalized && data.capitalization_track === "none") {
        return false;
      }
      return true;
    },
    {
      message: "כאשר המשק מהוון, יש לבחור מסלול היוון",
      path: ["capitalization_track"],
    }
  );

export type IntakeSchema = z.infer<typeof intakeSchema>;

/* ────────────────────────────────────────────
   Step-specific sub-schemas for per-step
   validation inside the wizard
   ──────────────────────────────────────────── */

/** Step 1 — Owner details */
export const step1Schema = z.object({
  owner_name: z.string().min(1, "שדה חובה"),
  ownership_type: z.enum(["single", "partners", "heirs"], {
    error: "נא לבחור סוג בעלות",
  }),
  has_intergenerational_continuity: z.boolean({
    error: "נא לבחור תשובה",
  }),
});

/** Step 2 — Location */
export const step2Schema = z.object({
  moshav_name: z.string().min(1, "שדה חובה"),
  gush: z.coerce.number().int().positive("מספר גוש חייב להיות חיובי"),
  helka: z.coerce.number().int().positive("מספר חלקה חייב להיות חיובי"),
});

/** Step 3 — Legal status */
export const step3Schema = z
  .object({
    authorization_type: z.enum([
      "bar_reshut",
      "chocher",
      "choze_chachira_mehuvon",
    ]),
    is_capitalized: z.boolean(),
    capitalization_track: z.enum(["375", "33", "none"]),
  })
  .refine(
    (data) => {
      if (!data.is_capitalized && data.capitalization_track !== "none") {
        return false;
      }
      return true;
    },
    {
      message: 'כאשר המשק לא מהוון, מסלול ההיוון חייב להיות "ללא"',
      path: ["capitalization_track"],
    }
  )
  .refine(
    (data) => {
      if (data.is_capitalized && data.capitalization_track === "none") {
        return false;
      }
      return true;
    },
    {
      message: "כאשר המשק מהוון, יש לבחור מסלול היוון",
      path: ["capitalization_track"],
    }
  );

/** Step 4 — Goals */
export const step4Schema = z.object({
  num_existing_houses: z.number().int().min(0).max(10),
  client_goals: z
    .array(z.enum(["regularization", "capitalization", "split", "all"]))
    .min(1, "יש לבחור לפחות מטרה אחת"),
  has_demolition_orders: z.boolean(),
});
