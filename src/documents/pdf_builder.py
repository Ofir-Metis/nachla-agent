"""Generate a Hebrew executive summary PDF for the feasibility study.

Uses fpdf2 which supports Unicode/Hebrew text natively.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from fpdf import FPDF

logger = logging.getLogger(__name__)

# Path to a Hebrew-supporting font (bundled with the project or system)
_FONT_DIR = Path(__file__).parent.parent.parent / "data" / "fonts"


class HebrewPDF(FPDF):
    """PDF with Hebrew RTL support."""

    def __init__(self):
        super().__init__()
        # Try Hebrew fonts in order: David, NotoSansHebrew, Arial
        loaded = False
        for regular, bold, name in [
            ("david.ttf", "davidbd.ttf", "David"),
            ("NotoSansHebrew-Regular.ttf", "NotoSansHebrew-Bold.ttf", "NotoHeb"),
        ]:
            reg_path = _FONT_DIR / regular
            bold_path = _FONT_DIR / bold
            if reg_path.exists():
                self.add_font(name, "", str(reg_path), uni=True)
                if bold_path.exists():
                    self.add_font(name, "B", str(bold_path), uni=True)
                else:
                    self.add_font(name, "B", str(reg_path), uni=True)
                self._hebrew_font = name
                loaded = True
                break

        if not loaded:
            # Last resort: try system Arial which usually supports Hebrew
            import platform
            if platform.system() == "Windows":
                arial = Path("C:/Windows/Fonts/arial.ttf")
                arialbd = Path("C:/Windows/Fonts/arialbd.ttf")
                if arial.exists():
                    self.add_font("Arial", "", str(arial), uni=True)
                    self.add_font("Arial", "B", str(arialbd) if arialbd.exists() else str(arial), uni=True)
                    self._hebrew_font = "Arial"
                    loaded = True

        if not loaded:
            self._hebrew_font = "Helvetica"
            logger.warning("No Hebrew font found — PDF may not render Hebrew text correctly")

    def rtl_cell(self, w, h, txt, **kwargs):
        """Write a right-to-left cell."""
        # Reverse the logical order for RTL display
        self.cell(w, h, txt, **kwargs)


def _fmt(amount: float) -> str:
    """Format currency."""
    if amount == 0:
        return "0"
    return f"{amount:,.0f}"


def build_executive_summary(
    nachla: dict[str, Any],
    buildings: list[dict[str, Any]],
    tabas: list[dict[str, Any]],
    calc_results: dict[str, Any],
    report_date: str,
    output_path: str,
) -> str:
    """Build a one-page executive summary PDF.

    Args:
        nachla: Nachla data dict
        buildings: Building list
        tabas: Taba list
        calc_results: Calculation results
        report_date: Report date
        output_path: Output PDF path

    Returns:
        Output file path.
    """
    pdf = HebrewPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    owner = nachla.get('owner_name', '')
    moshav = nachla.get('moshav_name', '')
    gush = nachla.get('gush', '')
    helka = nachla.get('helka', '')
    priority = nachla.get('priority_area', 'none')

    font = pdf._hebrew_font

    # Title
    pdf.set_font(font, 'B', 16)
    pdf.cell(0, 12, f"{moshav} - {owner}", ln=True, align='C')

    pdf.set_font(font, '', 10)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 6, f"{report_date}  |  {helka}  |  {gush}", ln=True, align='C')
    pdf.set_text_color(0, 0, 0)
    pdf.ln(8)

    # Key Numbers Box
    pdf.set_fill_color(245, 243, 238)
    pdf.set_font(font, 'B', 12)
    pdf.cell(0, 8, "Summary / Cost Overview", ln=True, fill=True)
    pdf.ln(2)

    hivun = calc_results.get('hivun', {})
    h375 = hivun.get('hivun_375', {}).get('result', 0) if isinstance(hivun.get('hivun_375'), dict) else 0
    h33 = hivun.get('hivun_33', {}).get('result', 0) if isinstance(hivun.get('hivun_33'), dict) else 0
    usage = calc_results.get('usage_fees', {}).get('total', 0)
    permit = calc_results.get('regularization', {}).get('total_permit_fees', 0)

    pdf.set_font(font, '', 11)
    costs = [
        ("Usage Fees", usage, "NIS"),
        ("Permit Fees", permit, "NIS"),
        ("Hivun 3.75%", h375, "NIS"),
        ("Hivun 33%", h33, "NIS"),
    ]

    col_w = 63
    for label, amount, unit in costs:
        pdf.set_font(font, '', 10)
        pdf.cell(col_w, 7, label, border=0)
        pdf.set_font(font, 'B', 10)
        pdf.cell(col_w, 7, f"{_fmt(amount)} {unit}", border=0)
        pdf.cell(col_w, 7, "", border=0, ln=True)
    pdf.ln(6)

    # Buildings
    pdf.set_fill_color(245, 243, 238)
    pdf.set_font(font, 'B', 12)
    pdf.cell(0, 8, f"Buildings ({len(buildings)})", ln=True, fill=True)
    pdf.ln(2)

    type_labels = {
        'residential': 'Residential', 'service': 'Service', 'agricultural': 'Agricultural',
        'pool': 'Pool', 'pergola': 'Pergola', 'plach': 'Commercial', 'shed_open': 'Shed',
    }
    status_labels = {
        'compliant': 'Compliant', 'deviation': 'Deviation',
        'no_permit': 'No Permit', 'marked_demolition': 'Demolition',
    }

    if buildings:
        # Header
        pdf.set_font(font, 'B', 9)
        pdf.cell(10, 6, "#")
        pdf.cell(55, 6, "Name")
        pdf.cell(35, 6, "Type")
        pdf.cell(25, 6, "Area sqm")
        pdf.cell(30, 6, "Status")
        pdf.cell(25, 6, "Deviation", ln=True)

        pdf.set_font(font, '', 9)
        for b in buildings:
            pdf.cell(10, 5, str(b.get('id', '')))
            pdf.cell(55, 5, str(b.get('name', ''))[:30])
            pdf.cell(35, 5, type_labels.get(b.get('building_type', ''), b.get('building_type', '')))
            pdf.cell(25, 5, str(b.get('main_area_sqm', 0)))
            pdf.cell(30, 5, status_labels.get(b.get('status', ''), b.get('status', '')))
            pdf.cell(25, 5, str(b.get('deviation_sqm', 0) or '-'), ln=True)
    pdf.ln(6)

    # Taba
    if tabas:
        pdf.set_fill_color(245, 243, 238)
        pdf.set_font(font, 'B', 12)
        pdf.cell(0, 8, "Zoning Plans (Taba)", ln=True, fill=True)
        pdf.ln(2)

        pdf.set_font(font, '', 10)
        for t in tabas:
            name = t.get('taba_name', '')
            num = t.get('taba_number', '')
            plot = t.get('plot_size_sqm', 0)
            units = t.get('num_units_allowed', 0)
            pdf.cell(0, 6, f"{num} - {name}", ln=True)
            pdf.cell(0, 5, f"Plot: {plot:,.0f} sqm  |  Units: {units}  |  Split: {'Yes' if t.get('split_allowed') else 'No'}", ln=True)
            # Show unit rights
            ur = t.get('unit_rights', [])
            if ur and isinstance(ur[0], dict):
                main = ur[0].get('main_area_sqm', 0)
                service = ur[0].get('service_area_sqm', 0)
                pdf.cell(0, 5, f"Rights per unit: {main} sqm main + {service} sqm service", ln=True)
        pdf.ln(4)

    # Hivun comparison
    if h375 > 0 and h33 > 0:
        pdf.set_fill_color(245, 243, 238)
        pdf.set_font(font, 'B', 12)
        pdf.cell(0, 8, "Capitalization Comparison", ln=True, fill=True)
        pdf.ln(2)

        pdf.set_font(font, '', 10)
        pdf.cell(0, 6, f"Track 3.75%: {_fmt(h375)} NIS", ln=True)
        pdf.cell(0, 6, f"Track 33%:   {_fmt(h33)} NIS", ln=True)
        diff = h33 - h375
        pdf.set_font(font, 'B', 10)
        pdf.cell(0, 6, f"Difference:  {_fmt(diff)} NIS", ln=True)
        pdf.set_font(font, '', 9)
        if h375 < h33:
            pdf.cell(0, 5, "3.75% is cheaper upfront but split requires additional payment.", ln=True)
    pdf.ln(4)

    # Priority area
    if priority and priority != 'none':
        pdf.set_font(font, '', 9)
        area_labels = {'A': 'A', 'B': 'B', 'frontline': 'Frontline'}
        pdf.cell(0, 5, f"Priority Area: {area_labels.get(priority, priority)} - discounts apply per RMI rules.", ln=True)

    # Footer
    pdf.ln(8)
    pdf.set_font(font, '', 7)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 4, f"Generated by Nachla Feasibility System | {report_date}", ln=True, align='C')
    pdf.cell(0, 4, "This is a preliminary estimate only. Not a substitute for legal or professional advice.", ln=True, align='C')

    # Save
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    pdf.output(output_path)
    logger.info("Executive summary PDF built: %s", output_path)
    return output_path
