"""Nachla Agent calculation tools.

All public functions for RMI fee calculations, priority areas,
and reference table lookups.
"""

from tools.calc_dmei_heter import (
    calculate_building_permit_fees,
    calculate_dmei_heter,
    check_permit_fee_cap,
)
from tools.calc_dmei_shimush import calculate_dmei_shimush
from tools.calc_hetel_hashbacha import (
    calculate_betterment_levy,
    calculate_partial_betterment,
    estimate_split_betterment,
)
from tools.calc_hivun import (
    calculate_hivun_33,
    calculate_hivun_375,
    compare_tracks,
)
from tools.calc_pitzul import (
    calculate_remaining_rights,
    calculate_split_cost,
    check_split_eligibility,
)
from tools.calc_sqm_equivalent import (
    calculate_hivun_375_sqm,
    calculate_nachla_sqm_equivalent,
    calculate_potential_sqm,
    calculate_sqm_equivalent,
)
from tools.lookup_tables import (
    lookup_development_costs,
    lookup_plach_rate,
    lookup_settlement_shovi,
)
from tools.priority_areas import (
    get_discount,
    get_hivun_33_rate,
    get_priority_area,
    get_usage_rate,
)

__all__ = [
    # Permit fees
    "calculate_dmei_heter",
    "calculate_building_permit_fees",
    "check_permit_fee_cap",
    # Usage fees
    "calculate_dmei_shimush",
    # Capitalization
    "calculate_hivun_375",
    "calculate_hivun_33",
    "compare_tracks",
    # Plot splitting
    "check_split_eligibility",
    "calculate_split_cost",
    "calculate_remaining_rights",
    # Equivalent sqm
    "calculate_sqm_equivalent",
    "calculate_nachla_sqm_equivalent",
    "calculate_potential_sqm",
    "calculate_hivun_375_sqm",
    # Betterment levy
    "calculate_betterment_levy",
    "calculate_partial_betterment",
    "estimate_split_betterment",
    # Lookup tables
    "lookup_settlement_shovi",
    "lookup_plach_rate",
    "lookup_development_costs",
    # Priority areas
    "get_priority_area",
    "get_discount",
    "get_usage_rate",
    "get_hivun_33_rate",
]
