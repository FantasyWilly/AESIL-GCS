

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Sequence
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile


@dataclass(slots=True)
class LogRow:
    timestamp: str
    event_type: str
    vehicle_name: str
    tracker_id: str
    label: str
    latitude: str
    longitude: str
    altitude: str
    extra: str


class DataLogger:
    headers = [
        "timestamp",
        "event_type",
        "vehicle_name",
        "tracker_id",
        "label",
        "latitude",
        "longitude",
        "altitude",
        "extra",
    ]

    def __init__(self) -> None:
        self.rows: List[LogRow] = []

    def log_aircraft(
        self,
        latitude: float,
        longitude: float,
        altitude: float,
        fix_type: str,
        timestamp: datetime | None = None,
    ) -> None:
        self.rows.append(
            LogRow(
                timestamp=(timestamp or datetime.utcnow()).isoformat(),
                event_type="aircraft",
                vehicle_name="",
                tracker_id="",
                label="",
                latitude=f"{latitude:.8f}",
                longitude=f"{longitude:.8f}",
                altitude=f"{altitude:.3f}",
                extra=fix_type,
            )
        )

    def log_target(
        self,
        vehicle_name: str,
        tracker_id: int,
        label: str,
        latitude: float,
        longitude: float,
        altitude: float,
        timestamp: datetime | None = None,
    ) -> None:
        self.rows.append(
            LogRow(
                timestamp=(timestamp or datetime.utcnow()).isoformat(),
                event_type="target",
                vehicle_name=vehicle_name,
                tracker_id=str(tracker_id),
                label=label,
                latitude=f"{latitude:.8f}",
                longitude=f"{longitude:.8f}",
                altitude=f"{altitude:.3f}",
                extra="",
            )
        )

    def export_csv(self, file_path: str | Path) -> Path:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [",".join(self.headers)]
        for row in self.rows:
            lines.append(",".join(self._csv_escape(value) for value in self._row_to_values(row)))
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path

    def export_xlsx(self, file_path: str | Path) -> Path:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        rows = [self.headers] + [list(self._row_to_values(row)) for row in self.rows]

        with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
            archive.writestr("[Content_Types].xml", self._content_types_xml())
            archive.writestr("_rels/.rels", self._root_rels_xml())
            archive.writestr("xl/workbook.xml", self._workbook_xml())
            archive.writestr("xl/_rels/workbook.xml.rels", self._workbook_rels_xml())
            archive.writestr("xl/styles.xml", self._styles_xml())
            archive.writestr("xl/worksheets/sheet1.xml", self._worksheet_xml(rows))
        return path

    def _row_to_values(self, row: LogRow) -> Sequence[str]:
        return (
            row.timestamp,
            row.event_type,
            row.vehicle_name,
            row.tracker_id,
            row.label,
            row.latitude,
            row.longitude,
            row.altitude,
            row.extra,
        )

    def _csv_escape(self, value: str) -> str:
        if any(char in value for char in [",", "\"", "\n"]):
            return '"' + value.replace('"', '""') + '"'
        return value

    def _worksheet_xml(self, rows: Iterable[Sequence[str]]) -> str:
        row_xml: List[str] = []
        for row_index, row_values in enumerate(rows, start=1):
            cells = []
            style_id = "1" if row_index == 1 else "0"
            for column_index, value in enumerate(row_values, start=1):
                ref = f"{self._column_name(column_index)}{row_index}"
                cells.append(
                    f'<c r="{ref}" t="inlineStr" s="{style_id}"><is><t>{escape(value)}</t></is></c>'
                )
            row_xml.append(f'<row r="{row_index}">{"".join(cells)}</row>')

        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<sheetViews><sheetView workbookViewId="0"/></sheetViews>'
            '<sheetFormatPr defaultRowHeight="15"/>'
            f'<sheetData>{"".join(row_xml)}</sheetData>'
            "</worksheet>"
        )

    def _column_name(self, index: int) -> str:
        name = ""
        while index:
            index, remainder = divmod(index - 1, 26)
            name = chr(65 + remainder) + name
        return name

    def _content_types_xml(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/styles.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
            "</Types>"
        )

    def _root_rels_xml(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="xl/workbook.xml"/>'
            "</Relationships>"
        )

    def _workbook_xml(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="flight_log" sheetId="1" r:id="rId1"/></sheets>'
            "</workbook>"
        )

    def _workbook_rels_xml(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            'Target="worksheets/sheet1.xml"/>'
            '<Relationship Id="rId2" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
            'Target="styles.xml"/>'
            "</Relationships>"
        )

    def _styles_xml(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<fonts count="2">'
            '<font><sz val="11"/><name val="Calibri"/></font>'
            '<font><b/><sz val="11"/><name val="Calibri"/></font>'
            "</fonts>"
            '<fills count="2">'
            '<fill><patternFill patternType="none"/></fill>'
            '<fill><patternFill patternType="gray125"/></fill>'
            "</fills>"
            '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
            '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
            '<cellXfs count="2">'
            '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
            '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/>'
            "</cellXfs>"
            '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
            "</styleSheet>"
        )
