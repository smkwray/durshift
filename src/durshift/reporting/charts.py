from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from durshift.utils.files import ensure_parent_dir


def plot_acceptance_by_bucket(input_path: str | Path, output_path: str | Path) -> Path:
    """Create a simple accepted-amount by maturity-bucket chart."""

    frame = pd.read_csv(input_path)
    amount_col = (
        "par_amount_accepted" if "par_amount_accepted" in frame.columns else "accepted_amount"
    )
    chart_data = frame.groupby("maturity_bucket", dropna=False)[amount_col].sum().sort_index()

    output_file = ensure_parent_dir(output_path)
    fig, ax = plt.subplots(figsize=(8, 5))
    chart_data.plot(kind="bar", ax=ax)
    ax.set_title("Accepted Buyback Amount by Maturity Bucket")
    ax.set_xlabel("Maturity bucket")
    ax.set_ylabel("Accepted amount")
    fig.tight_layout()
    fig.savefig(output_file, dpi=150)
    plt.close(fig)
    return output_file
