"""Two Matplotlib-style panels. All values are synthetic, not research results."""

from pathlib import Path

import matplotlib.pyplot as plt

from radialbundle import plot_panels, save
from basic import DATA


def main():
    out = Path(__file__).resolve().parent / "output"
    data_b = {
        group: {model: round(value * (0.91 + 0.025 * (index % 4)), 3)
                for index, (model, value) in enumerate(values.items())}
        for group, values in DATA.items()
    }
    panels = {"Dataset A": DATA, "Dataset B": data_b}
    fig, _ = plot_panels(
        panels,
        share_scale=True,
        highlight="Proposed",
        best_label="Best in group",
        value_format=".3f",
    )
    save(fig, out / "two_panels")
    print(out / "two_panels.png")
    plt.close(fig)


if __name__ == "__main__":
    main()
