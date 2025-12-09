"""
PDF Generator Service

Generates PDF reports for automation summaries using reportlab.
"""

from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable
)

from models.automation_result import AutomationSummary, VendorResult
from utils.logger import get_logger

logger = get_logger(__name__)


class PDFGenerator:
    """Generates PDF reports for automation summaries"""

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._create_custom_styles()

    def _create_custom_styles(self):
        """Create custom paragraph styles"""
        self.styles.add(ParagraphStyle(
            name='Title_Custom',
            parent=self.styles['Title'],
            fontSize=24,
            spaceAfter=30
        ))

        self.styles.add(ParagraphStyle(
            name='Section_Header',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=12,
            spaceBefore=20,
            textColor=colors.HexColor('#1a1a1a')
        ))

        self.styles.add(ParagraphStyle(
            name='Subsection_Header',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=8,
            spaceBefore=15
        ))

        self.styles.add(ParagraphStyle(
            name='Field_Label',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.gray
        ))

        self.styles.add(ParagraphStyle(
            name='Field_Value',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceAfter=6
        ))

        self.styles.add(ParagraphStyle(
            name='Error_Text',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.red
        ))

        self.styles.add(ParagraphStyle(
            name='Success_Text',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.green
        ))

        self.styles.add(ParagraphStyle(
            name='Failure_Text',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.red
        ))

    def generate_report(self, summary: AutomationSummary, output_path: str):
        """
        Generate PDF report for automation summary

        Args:
            summary: AutomationSummary with all results
            output_path: Path to save PDF file
        """
        logger.info(f"Generating PDF report: {output_path}")

        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch
        )

        story = []

        # Title
        story.append(Paragraph("Vendor Provisioning Report", self.styles['Title_Custom']))
        story.append(Spacer(1, 12))

        # Generation timestamp
        timestamp = datetime.now().strftime("%B %d, %Y at %I:%M %p")
        story.append(Paragraph(f"Generated: {timestamp}", self.styles['Field_Label']))
        story.append(Spacer(1, 20))

        # Horizontal line
        story.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))
        story.append(Spacer(1, 10))

        # User Profile Section
        story.extend(self._build_user_profile_section(summary))

        # Summary Statistics Section
        story.extend(self._build_stats_section(summary))

        # Per-Vendor Sections
        story.extend(self._build_vendor_sections(summary))

        # Build PDF
        doc.build(story)
        logger.info(f"PDF report generated successfully: {output_path}")

    def _build_user_profile_section(self, summary: AutomationSummary) -> list:
        """Build user profile section"""
        elements = []
        user = summary.user

        elements.append(Paragraph("User Profile", self.styles['Section_Header']))

        # User details table
        data = [
            ['Full Name:', user.display_name or 'N/A'],
            ['Email:', user.email or 'N/A'],
            ['Employee ID:', user.employee_id or 'N/A'],
            ['Job Title:', user.job_title or 'N/A'],
            ['Department:', user.department or 'N/A'],
            ['Office:', user.office_location or 'N/A'],
        ]

        table = Table(data, colWidths=[1.5 * inch, 5 * inch])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.gray),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(table)

        # Group memberships
        if user.groups:
            elements.append(Spacer(1, 10))
            elements.append(Paragraph("Group Memberships:", self.styles['Field_Label']))

            group_names = sorted([g.display_name for g in user.groups])
            # Show first 10 groups, then "and X more"
            if len(group_names) > 10:
                displayed = group_names[:10]
                remaining = len(group_names) - 10
                groups_text = ", ".join(displayed) + f", and {remaining} more..."
            else:
                groups_text = ", ".join(group_names) if group_names else "None"

            elements.append(Paragraph(groups_text, self.styles['Field_Value']))

        elements.append(Spacer(1, 15))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))

        return elements

    def _build_stats_section(self, summary: AutomationSummary) -> list:
        """Build summary statistics section"""
        elements = []

        elements.append(Paragraph("Summary Statistics", self.styles['Section_Header']))

        # Calculate stats
        total = len(summary.vendor_results)
        successful = summary.success_count
        failed = summary.failure_count

        # Duration formatting
        duration_seconds = summary.total_duration_seconds
        if duration_seconds >= 60:
            duration_text = f"{int(duration_seconds // 60)} min {int(duration_seconds % 60)} sec"
        else:
            duration_text = f"{int(duration_seconds)} seconds"

        # Stats table
        data = [
            ['Total Vendors:', str(total)],
            ['Successful:', str(successful)],
            ['Failed:', str(failed)],
            ['Total Duration:', duration_text],
            ['Start Time:', summary.start_time.strftime("%I:%M:%S %p") if summary.start_time else 'N/A'],
            ['End Time:', summary.end_time.strftime("%I:%M:%S %p") if summary.end_time else 'N/A'],
        ]

        table = Table(data, colWidths=[1.5 * inch, 3 * inch])
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.gray),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            # Color successful/failed counts
            ('TEXTCOLOR', (1, 1), (1, 1), colors.green),  # Successful count
            ('TEXTCOLOR', (1, 2), (1, 2), colors.red if failed > 0 else colors.gray),  # Failed count
        ]))
        elements.append(table)

        elements.append(Spacer(1, 15))
        elements.append(HRFlowable(width="100%", thickness=1, color=colors.lightgrey))

        return elements

    def _build_vendor_sections(self, summary: AutomationSummary) -> list:
        """Build per-vendor result sections"""
        elements = []

        elements.append(Paragraph("Vendor Results", self.styles['Section_Header']))

        for i, vendor_result in enumerate(summary.vendor_results):
            elements.extend(self._build_single_vendor_section(vendor_result, i + 1))

        return elements

    def _build_single_vendor_section(self, vendor_result: VendorResult, index: int) -> list:
        """Build a single vendor result section"""
        elements = []

        # Vendor header with status
        status_text = "[SUCCESS]" if vendor_result.success else "[FAILED]"
        status_style = 'Success_Text' if vendor_result.success else 'Failure_Text'

        header_text = f"{index}. {vendor_result.display_name}"
        elements.append(Paragraph(header_text, self.styles['Subsection_Header']))
        elements.append(Paragraph(status_text, self.styles[status_style]))

        # Timestamps
        if vendor_result.start_time:
            start_str = vendor_result.start_time.strftime("%I:%M:%S %p")
            elements.append(Paragraph(f"Start: {start_str}", self.styles['Field_Label']))

        if vendor_result.end_time:
            end_str = vendor_result.end_time.strftime("%I:%M:%S %p")
            duration_str = f"{vendor_result.duration_seconds:.1f}s"
            elements.append(Paragraph(f"End: {end_str} (Duration: {duration_str})", self.styles['Field_Label']))

        # Errors only (not full log)
        if vendor_result.errors:
            elements.append(Spacer(1, 8))
            elements.append(Paragraph("Errors:", self.styles['Field_Label']))

            for error in vendor_result.errors:
                # Clean the error text (remove special chars)
                clean_error = error.replace("\u2717", "").strip()
                elements.append(Paragraph(f"  - {clean_error}", self.styles['Error_Text']))

        # Image placeholder box
        elements.append(Spacer(1, 10))

        # Check if screenshot exists
        if vendor_result.screenshot_path and Path(vendor_result.screenshot_path).exists():
            try:
                # Import here to avoid issues if PIL not available
                from reportlab.platypus import Image as RLImage
                # Add actual image (scaled to fit)
                img = RLImage(vendor_result.screenshot_path, width=5 * inch, height=3 * inch)
                img.hAlign = 'LEFT'
                elements.append(img)
            except Exception as e:
                logger.warning(f"Could not add screenshot to PDF: {e}")
                elements.append(self._create_image_placeholder())
        else:
            elements.append(self._create_image_placeholder())

        elements.append(Spacer(1, 15))

        return elements

    def _create_image_placeholder(self) -> Table:
        """Create a placeholder box for image"""
        data = [['[Screenshot Placeholder]']]
        table = Table(data, colWidths=[5 * inch], rowHeights=[2 * inch])
        table.setStyle(TableStyle([
            ('BOX', (0, 0), (-1, -1), 1, colors.lightgrey),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.gray),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f5f5f5')),
        ]))
        return table
