from __future__ import annotations

from pathlib import Path

from durshift.panels.operations import build_operation_panel
from durshift.reporting.charts import plot_acceptance_by_bucket
from durshift.reporting.summary_tables import write_duration_summary


def run_sample_pipeline(repo_root: Path) -> dict[str, Path]:
    """Run the seed demo pipeline and return output paths."""

    sample_input = repo_root / "data" / "examples" / "sample_buybacks.csv"
    operation_panel = repo_root / "data" / "processed" / "sample_operation_panel.csv"
    summary_output = repo_root / "outputs" / "tables" / "sample_duration_summary.csv"
    chart_output = repo_root / "outputs" / "figures" / "sample_buyback_acceptance.png"

    build_operation_panel(sample_input, operation_panel)
    write_duration_summary(operation_panel, summary_output)
    plot_acceptance_by_bucket(operation_panel, chart_output)

    return {
        "operation_panel": operation_panel,
        "duration_summary": summary_output,
        "acceptance_chart": chart_output,
    }
