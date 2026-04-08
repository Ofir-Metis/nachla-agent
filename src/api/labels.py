"""Hebrew label dictionaries for the API and React frontend.

Extracted from the former Chainlit UI components for reuse.
"""

BUILDING_TYPE_LABELS: dict[str, str] = {
    "residential": "בית מגורים",
    "service": "מבנה שירות / מחסן",
    "agricultural": "מבנה חקלאי / סככה",
    "plach": 'מבנה פל"ח (עסקי)',
    "pergola": "פרגולה",
    "pool": "בריכת שחייה",
    "basement_service": "מרתף שירות",
    "basement_residential": "מרתף מגורים",
    "attic": "עליית גג",
    "ground_floor_open": "קומת עמודים פתוחה",
    "ground_floor_closed": "קומת עמודים סגורה",
    "temporary": "מבנה ארעי/קל/נייד",
    "shed_open": "סככה פתוחה",
    "pre_1965": "מבנה לפני 1965",
}

BUILDING_STATUS_LABELS: dict[str, str] = {
    "compliant": "תקין - תואם היתר",
    "deviation": "חריגה מהיתר",
    "no_permit": "ללא היתר",
    "marked_demolition": "סומן להריסה",
    "building_line_violation": "חורג מקווי בניין",
}

AUTH_TYPE_LABELS: dict[str, str] = {
    "bar_reshut": "בר רשות",
    "chocher": "חוכר לדורות",
    "choze_chachira_mehuvon": "חוזה חכירה מהוון",
}

CLIENT_GOAL_LABELS: dict[str, str] = {
    "regularization": "הסדרה",
    "capitalization": "היוון",
    "split": "פיצול",
    "all": "הכל",
}

OWNERSHIP_TYPE_LABELS: dict[str, str] = {
    "single": "בעלים יחיד",
    "partners": "שותפים",
    "heirs": "יורשים",
}
