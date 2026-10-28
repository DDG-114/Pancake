"""Read the synthetic CSV template and export a radial comparison figure."""

from pathlib import Path

import matplotlib.pyplot as plt

from radialbundle import plot, read_csv, save


def main():
    here = Path(__file__).resolve().parent
    data = read_csv(here / "results.csv")
    out = here / "output"
    out.mkdir(exist_ok=True)
    fig, _ = plot(data, highlight="Proposed", value_format=".3f")
    save(fig, out / "from_csv")
    print(out / "from_csv.png")
    plt.close(fig)


if __name__ == "__main__":
    main()
