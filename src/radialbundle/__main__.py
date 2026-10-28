"""Command-line CSV plotting."""

import argparse
import sys

from .csvio import _read_panels
from .plotting import Style, plot, plot_panels, save


def main(argv=None):
    parser = argparse.ArgumentParser(description="Draw grouped radial charts from a CSV file.")
    parser.add_argument("csv", help="CSV with group,model,value and optional panel columns")
    parser.add_argument("--output", "-o", default="radial_plot", help="output path prefix")
    parser.add_argument("--formats", nargs="+", default=["png", "pdf", "svg"], choices=["png", "pdf", "svg"])
    parser.add_argument("--panel", help="select one panel; by default draw all panels")
    parser.add_argument("--highlight", help="model to outline, e.g. Proposed")
    parser.add_argument("--background", default=None)
    parser.add_argument("--palette", choices=["reference", "reference_right", "matplotlib"], default="reference")
    parser.add_argument("--decimals", type=int, default=3)
    parser.add_argument("--higher-is-better", action="store_true")
    parser.add_argument("--share-scale", action="store_true", help="same length scale across panels")
    parser.add_argument("--ncols", type=int, default=2)
    parser.add_argument("--label-size", type=float, default=10)
    parser.add_argument("--font", default=None)
    parser.add_argument("--title")
    args = parser.parse_args(argv)
    if not 0 <= args.decimals <= 12:
        parser.error("--decimals must be between 0 and 12")
    try:
        panels = _read_panels(args.csv, "utf-8-sig")
        if args.panel is not None:
            if args.panel not in panels:
                raise ValueError(f"panel {args.panel!r} not found; available: {list(panels)}")
            panels = {args.panel: panels[args.panel]}
        options = dict(highlight=args.highlight, background=args.background, colors=args.palette,
                       lower_is_better=not args.higher_is_better,
                       value_format=f".{args.decimals}f",
                       style=Style(label_size=args.label_size, font_family=args.font))
        if args.title is not None:
            options["title"] = args.title
        if len(panels) == 1:
            fig, _ = plot(next(iter(panels.values())), **options)
        else:
            fig, _ = plot_panels(panels, ncols=args.ncols, share_scale=args.share_scale, **options)
        for path in save(fig, args.output, formats=args.formats):
            print(path.resolve())
    except (OSError, ValueError) as error:
        parser.exit(2, f"radialbundle: {error}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
