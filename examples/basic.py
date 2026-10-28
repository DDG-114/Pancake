"""Dense four-group example. All values are synthetic, not research results."""

from pathlib import Path

import matplotlib.pyplot as plt

from radialbundle import plot, save


MODELS = [
    "DLinear", "PatchTST", "TimeXer", "P2D-former", "DAMixer", "SegRNN",
    "TFDNet", "TimesNet", "iTransformer", "Informer", "Autoformer",
    "Time-LLM", "CALF", "Proposed",
]
VALUES = {
    "Load": [0.96, 0.88, 0.85, 0.82, 0.91, 0.86, 0.89, 0.94, 0.84, 0.97, 0.92, 0.81, 0.79, 0.72],
    "Wind": [1.12, 0.95, 0.98, 0.93, 1.05, 0.97, 1.01, 1.09, 0.94, 1.15, 1.06, 0.96, 0.91, 0.83],
    "PV": [1.31, 1.19, 1.14, 1.12, 1.26, 1.17, 1.20, 1.29, 1.10, 1.35, 1.24, 1.16, 1.08, 0.99],
    "Net load": [0.89, 0.80, 0.78, 0.76, 0.86, 0.81, 0.84, 0.88, 0.79, 0.93, 0.87, 0.77, 0.74, 0.68],
}
DATA = {group: dict(zip(MODELS, values)) for group, values in VALUES.items()}


def main():
    out = Path(__file__).resolve().parent / "output"
    out.mkdir(exist_ok=True)
    for background, suffix in [("white", "white"), ("#c8c8c8", "gray")]:
        fig, _ = plot(
            DATA,
            highlight="Proposed",
            highlight_label="Proposed",
            best_label="Best in group",
            lower_is_better=True,
            value_format=".3f",
            background=background,
        )
        save(fig, out / f"four_tasks_{suffix}")
        print(out / f"four_tasks_{suffix}.png")
        plt.close(fig)


if __name__ == "__main__":
    main()
