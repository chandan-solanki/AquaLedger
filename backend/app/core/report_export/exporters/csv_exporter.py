import csv
import io

from app.core.report_export.base_exporter import BaseExporter
from app.core.report_export.export_models import ReportExportData


class CSVExporter(BaseExporter):
    """UTF-8 header row + raw data rows, nothing else (TASKS.md Sprint 11
    Session 5 Phase B: "No formatting. Raw values only."). Deliberately
    excludes title/subtitle/filters/summary/footer/generated_at that PDF
    and Excel both include - a CSV is for re-import/data-processing, not
    presentation, so every value is written exactly as it arrived in
    `ReportRow.data`, converted to text only by Python's own `str()` (no
    currency/date/percent rendering - see formatting.py's own docstring
    on why CSV never calls it).
    """

    content_type = "text/csv; charset=utf-8"
    file_extension = "csv"

    def export(self, data: ReportExportData) -> bytes:
        buffer = io.StringIO()
        writer = csv.writer(buffer)

        writer.writerow([column.title for column in data.columns])
        for row in data.rows:
            writer.writerow(
                [
                    "" if row.data[column.key] is None else row.data[column.key]
                    for column in data.columns
                ]
            )

        return buffer.getvalue().encode("utf-8")
