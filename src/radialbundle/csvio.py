"""Load long-form CSV comparison data without a pandas dependency."""

import csv
import math


MISSING = {"", "na", "n/a", "nan", "none", "null", "--", "—", "–"}


def _read_panels(path, encoding):
    panels = {}
    with open(path, newline="", encoding=encoding) as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or not {"group", "model", "value"}.issubset(reader.fieldnames):
            raise ValueError("CSV requires group, model, value columns (and optionally panel)")
        for line, row in enumerate(reader, 2):
            if not any(value for value in row.values() if value is not None):
                continue
            panel = (row.get("panel") or "").strip()
            group, model = (row["group"] or "").strip(), (row["model"] or "").strip()
            if not group or not model:
                raise ValueError(f"CSV line {line}: group and model must be nonempty")
            text = (row["value"] or "").strip()
            if text.lower() in MISSING:
                value = None
            else:
                try:
                    value = float(text)
                except ValueError as error:
                    raise ValueError(f"CSV line {line}: invalid numeric value {text!r}") from error
                if not math.isfinite(value) or value < 0:
                    raise ValueError(f"CSV line {line}: value must be finite and nonnegative")
            entries = panels.setdefault(panel, {}).setdefault(group, {})
            if model in entries:
                raise ValueError(f"CSV line {line}: duplicate panel/group/model: {panel}/{group}/{model}")
            entries[model] = value
    if not panels:
        raise ValueError("CSV contains no data rows")
    return panels


def read_csv(path, *, panel=None, encoding="utf-8-sig"):
    """Read group/model/value CSV, optionally selecting one named panel.

    Blank, NA, NaN, -- and em dash values become None. Multiple panels require
    an explicit selection so that rows are never silently merged.
    """
    panels = _read_panels(path, encoding)
    if panel is not None:
        if panel not in panels:
            raise ValueError(f"panel {panel!r} not found; available panels: {list(panels)}")
        return panels[panel]
    if len(panels) != 1:
        raise ValueError(f"CSV has multiple panels; select panel= from {list(panels)}")
    return next(iter(panels.values()))
