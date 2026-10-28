"""Reference palettes with Matplotlib fonts. All values are synthetic."""

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
    for background, suffix in [("white", ""), ("#c8c8c8", "_gray")]:
        fig, _ = plot_panels(
            panels,
            share_scale=True,
            panel_colors={"Dataset A": "reference", "Dataset B": "reference_right"},
            highlight="Proposed",
            best_label="Best in group",
            value_format=".3f",
            background=background,
        )
        save(fig, out / f"two_panels{suffix}")
        print(out / f"two_panels{suffix}.png")
        plt.close(fig)


if __name__ == "__main__":
    main()
