"""Checks for value semantics and reusable Matplotlib behavior."""

import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from radialbundle import plot, plot_panels, read_csv, save


def gids(ax):
    return {artist.get_gid() for artist in ax.get_children() if artist.get_gid()}


def bar_length(ax, group, model):
    artist = next(a for a in ax.get_children() if a.get_gid() == f"bar:{group}:{model}")
    x, y = artist.get_data()
    return math.hypot(x[-1] - x[0], y[-1] - y[0])


class PlotTests(unittest.TestCase):
    def tearDown(self):
        plt.close("all")

    def test_best_and_highlight_are_independent_and_ties_are_preserved(self):
        data = {
            "Load": {"Baseline": 1.0, "Proposed": 2.0},
            "Wind": {"Baseline": 3.0, "Proposed": 3.0},
        }
        _, ax = plot(data, highlight="Proposed", legend=False)
        ids = gids(ax)
        self.assertIn("highlight:Load:Proposed", ids)
        self.assertNotIn("best:Load:Proposed", ids)
        self.assertIn("best:Load:Baseline", ids)
        self.assertIn("best:Wind:Baseline", ids)
        self.assertIn("best:Wind:Proposed", ids)

    def test_higher_is_better_and_missing_values(self):
        data = {
            "Load": {"Baseline": 1.0, "Proposed": 2.0},
            "Wind": {"Baseline": None, "Proposed": 0.0},
        }
        _, ax = plot(data, highlight="Proposed", lower_is_better=False, legend=False)
        ids = gids(ax)
        self.assertIn("best:Load:Proposed", ids)
        self.assertNotIn("best:Load:Baseline", ids)
        self.assertIn("best:Wind:Proposed", ids)
        self.assertNotIn("best:Wind:Baseline", ids)
        self.assertNotIn("bar:Wind:Baseline", ids)
        self.assertIn("label:Wind:Baseline", ids)

    def test_existing_axes_and_global_style_are_preserved(self):
        keys = ["font.family", "font.size", "font.weight", "axes.facecolor", "svg.fonttype", "pdf.fonttype"]
        before = {key: repr(matplotlib.rcParams[key]) for key in keys}
        fig, ax = plt.subplots()
        result_fig, result_ax = plot(
            {"Load": {"Proposed": 1.0}, "Wind": {"Proposed": 2.0}},
            ax=ax,
            highlight="Proposed",
        )
        self.assertIs(result_fig, fig)
        self.assertIs(result_ax, ax)
        self.assertEqual(before, {key: repr(matplotlib.rcParams[key]) for key in keys})

    def test_defaults_follow_matplotlib_font_and_color_context(self):
        data = {
            "Load": {"Baseline": 1.0, "Proposed": 0.8},
            "Wind": {"Baseline": 1.2, "Proposed": 0.9},
        }
        before_font = list(matplotlib.rcParams["font.family"])
        before_colors = matplotlib.rcParams["axes.prop_cycle"].by_key()["color"]
        colors = ["#335577", "#dd8844"]
        with matplotlib.rc_context({
            "font.family": ["DejaVu Sans Mono"],
            "axes.prop_cycle": plt.cycler(color=colors),
        }):
            _, ax = plot(data, legend=False)
            for group, color in zip(data, colors):
                bar = next(a for a in ax.get_children()
                           if a.get_gid() == f"bar:{group}:Baseline")
                self.assertEqual(matplotlib.colors.to_rgba(bar.get_color()),
                                 matplotlib.colors.to_rgba(color))
                label = next(a for a in ax.get_children()
                             if a.get_gid() == f"label:{group}:Baseline")
                self.assertIn("DejaVu Sans Mono", label.get_fontfamily())
                self.assertEqual(label.get_fontweight(), "normal")
        self.assertEqual(matplotlib.rcParams["font.family"], before_font)
        self.assertEqual(matplotlib.rcParams["axes.prop_cycle"].by_key()["color"], before_colors)

    def test_invalid_metrics_scales_and_names_fail_before_plotting(self):
        for value in [-1.0, math.inf, -math.inf, math.nan]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                plot({"Load": {"Proposed": value}, "Wind": {"Proposed": 1.0}})
        good = {"Load": {"Proposed": 1.0}, "Wind": {"Proposed": 2.0}}
        for scale in [0, -1, math.inf, math.nan]:
            with self.subTest(scale=scale), self.assertRaises(ValueError):
                plot(good, scale=scale)
        with self.assertRaises(ValueError):
            plot(good, highlight="MissingMethod")
        with self.assertRaises(ValueError):
            plot(good, model_order=["Proposed", "MissingMethod"])
        with self.assertRaises(ValueError):
            plot({"Load": {"Proposed": 1.0}})

    def test_shared_scale_preserves_cross_panel_magnitudes(self):
        panels = {
            "Small": {"Load": {"Proposed": 1.0}, "Wind": {"Proposed": 2.0}},
            "Large": {"Load": {"Proposed": 1.0}, "Wind": {"Proposed": 10.0}},
        }
        _, axes = plot_panels(panels, share_scale=True, highlight="Proposed", legend=False)
        flat = list(axes.flat) if hasattr(axes, "flat") else list(axes)
        self.assertAlmostEqual(bar_length(flat[0], "Load", "Proposed"), bar_length(flat[1], "Load", "Proposed"))


class CsvTests(unittest.TestCase):
    def write_csv(self, content):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        path = Path(folder.name) / "results.csv"
        path.write_text(content, encoding="utf-8-sig")
        return path

    def test_csv_bom_missing_values_and_order(self):
        path = self.write_csv(
            "group,model,value\n"
            "Load,DLinear,1.2\nLoad,Proposed,0.8\n"
            "Wind,DLinear,\nWind,Proposed,NA\n"
            "PV,DLinear,--\nPV,Proposed,—\n"
            "Net load,DLinear,NaN\nNet load,Proposed,0\n"
        )
        data = read_csv(path)
        self.assertEqual(list(data), ["Load", "Wind", "PV", "Net load"])
        self.assertEqual(data["Load"], {"DLinear": 1.2, "Proposed": 0.8})
        self.assertEqual(data["Wind"], {"DLinear": None, "Proposed": None})
        self.assertEqual(data["PV"], {"DLinear": None, "Proposed": None})
        self.assertEqual(data["Net load"], {"DLinear": None, "Proposed": 0.0})

    def test_csv_panel_selection_is_explicit(self):
        path = self.write_csv(
            "panel,group,model,value\n"
            "MAE,Load,Proposed,1\nRMSE,Load,Proposed,2\n"
        )
        with self.assertRaises(ValueError):
            read_csv(path)
        self.assertEqual(read_csv(path, panel="RMSE"), {"Load": {"Proposed": 2.0}})
        with self.assertRaises(ValueError):
            read_csv(path, panel="Absent")

    def test_duplicate_rows_and_missing_columns_are_rejected(self):
        duplicate = self.write_csv("group,model,value\nLoad,Proposed,1\nLoad,Proposed,2\n")
        with self.assertRaises(ValueError):
            read_csv(duplicate)
        missing = self.write_csv("group,value\nLoad,1\n")
        with self.assertRaises(ValueError):
            read_csv(missing)


class ExportTests(unittest.TestCase):
    def tearDown(self):
        plt.close("all")

    def test_public_save_writes_raster_and_editable_vector_files(self):
        fig, _ = plot({"Load": {"Proposed": 1.0}, "Wind": {"Proposed": 2.0}},
                      highlight="Proposed", background="#c8c8c8")
        with tempfile.TemporaryDirectory() as folder:
            outputs = save(fig, Path(folder) / "nested" / "result", dpi=80)
            self.assertEqual({p.suffix for p in outputs}, {".png", ".pdf", ".svg"})
            self.assertTrue(all(p.stat().st_size > 100 for p in outputs))
            self.assertTrue((Path(folder) / "nested" / "result.pdf").read_bytes().startswith(b"%PDF"))
            svg = (Path(folder) / "nested" / "result.svg").read_text(encoding="utf-8")
            self.assertIn("<text", svg)
            self.assertIn("Proposed", svg)

    def test_cli_draws_all_csv_panels_and_can_select_one(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "panels.csv"
            path.write_text(
                "panel,group,model,value\n"
                "MAE,Load,Proposed,1\nMAE,Wind,Proposed,2\n"
                "RMSE,Load,Proposed,3\nRMSE,Wind,Proposed,4\n",
                encoding="utf-8-sig",
            )
            prefix = Path(folder) / "multi"
            command = [sys.executable, "-m", "radialbundle", str(path),
                       "--output", str(prefix), "--formats", "svg",
                       "--highlight", "Proposed", "--share-scale"]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            svg = prefix.with_suffix(".svg").read_text(encoding="utf-8")
            self.assertIn("MAE", svg)
            self.assertIn("RMSE", svg)
            result = subprocess.run(command + ["--panel", "RMSE"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            svg = prefix.with_suffix(".svg").read_text(encoding="utf-8")
            self.assertNotIn(">MAE<", svg)


if __name__ == "__main__":
    unittest.main()
