from __future__ import annotations

import argparse
from pathlib import Path

from durshift.panels.operations import build_operation_panel
from durshift.pipeline import run_sample_pipeline
from durshift.reporting.charts import plot_acceptance_by_bucket
from durshift.reporting.summary_tables import write_duration_summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="durshift")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_panel = subparsers.add_parser("build-operation-panel")
    build_panel.add_argument("--input", required=True)
    build_panel.add_argument("--output", required=True)

    build_summary = subparsers.add_parser("build-duration-summary")
    build_summary.add_argument("--input", required=True)
    build_summary.add_argument("--output", required=True)

    plot_acceptance = subparsers.add_parser("plot-acceptance")
    plot_acceptance.add_argument("--input", required=True)
    plot_acceptance.add_argument("--output", required=True)

    sample = subparsers.add_parser("run-sample")
    sample.add_argument("--repo-root", default=".")

    # --- Data ingestion commands ---
    fetch_auctions = subparsers.add_parser("fetch-auctions")
    fetch_auctions.add_argument("--output", required=True, help="CSV destination path")
    fetch_auctions.add_argument("--min-date", default="2020-01-01", help="Earliest auction_date")
    fetch_auctions.add_argument(
        "--types",
        nargs="+",
        default=None,
        help="Security types to fetch (e.g., Bill Note Bond)",
    )

    fetch_schedule = subparsers.add_parser("fetch-buyback-schedule")
    fetch_schedule.add_argument("--xml-output", required=True, help="Raw XML destination")
    fetch_schedule.add_argument("--csv-output", required=True, help="Parsed CSV destination")

    fetch_results = subparsers.add_parser("fetch-buyback-results")
    fetch_results.add_argument(
        "--index-output", required=True, help="Operation index JSON destination"
    )
    fetch_results.add_argument(
        "--csv-output", required=True, help="Security-level results CSV destination"
    )

    build_real = subparsers.add_parser("build-real-panel")
    build_real.add_argument("--input", required=True, help="Buyback results detail CSV")
    build_real.add_argument("--output", required=True, help="Output operation panel CSV")
    build_real.add_argument("--h15-rates", default=None, help="H.15 rates CSV for yield proxies")
    build_real.add_argument("--tips-yields", default=None, help="TIPS real yields CSV")

    fetch_h15 = subparsers.add_parser("fetch-h15-rates")
    fetch_h15.add_argument("--output", required=True, help="CSV destination path")

    fetch_tips = subparsers.add_parser("fetch-tips-real-yields")
    fetch_tips.add_argument("--output", required=True, help="CSV destination path")

    fetch_dealers = subparsers.add_parser("fetch-dealer-positions")
    fetch_dealers.add_argument("--output", required=True, help="CSV destination path")

    fetch_tips_frn = subparsers.add_parser("fetch-tips-frn-auctions")
    fetch_tips_frn.add_argument("--output", required=True, help="CSV destination path")
    fetch_tips_frn.add_argument("--min-date", default="2020-01-01", help="Earliest auction date")

    fetch_soma = subparsers.add_parser("fetch-soma-holdings")
    fetch_soma.add_argument("--output", required=True, help="CSV destination path")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "build-operation-panel":
        output = build_operation_panel(args.input, args.output)
        print(output)
        return

    if args.command == "build-duration-summary":
        output = write_duration_summary(args.input, args.output)
        print(output)
        return

    if args.command == "plot-acceptance":
        output = plot_acceptance_by_bucket(args.input, args.output)
        print(output)
        return

    if args.command == "run-sample":
        outputs = run_sample_pipeline(Path(args.repo_root).resolve())
        for name, path in outputs.items():
            print(f"{name}: {path}")
        return

    if args.command == "fetch-auctions":
        from durshift.data.fiscal_data_api import fetch_and_save_auctions

        output = fetch_and_save_auctions(
            args.output,
            min_auction_date=args.min_date,
            security_types=args.types,
        )
        print(f"Saved auction data to {output}")
        return

    if args.command == "fetch-buyback-schedule":
        from durshift.data.buyback_schedule import fetch_and_save_schedule

        xml_path, csv_path = fetch_and_save_schedule(args.xml_output, args.csv_output)
        print(f"Saved schedule XML to {xml_path}")
        print(f"Saved parsed CSV to {csv_path}")
        return

    if args.command == "fetch-buyback-results":
        from durshift.data.buyback_results import fetch_and_save_results

        index_path, csv_path = fetch_and_save_results(args.index_output, args.csv_output)
        print(f"Saved operation index to {index_path}")
        print(f"Saved results ({csv_path})")
        return

    if args.command == "build-real-panel":
        from durshift.panels.real_operations import build_and_save_real_panel

        output = build_and_save_real_panel(
            args.input,
            args.output,
            h15_rates_path=args.h15_rates,
            tips_yields_path=args.tips_yields,
        )
        print(f"Saved real operation panel to {output}")
        return

    if args.command == "fetch-h15-rates":
        from durshift.data.h15_rates import fetch_and_save_h15

        output = fetch_and_save_h15(args.output)
        print(f"Saved H.15 rates to {output}")
        return

    if args.command == "fetch-tips-real-yields":
        from durshift.data.h15_rates import fetch_and_save_tips_real_yields

        output = fetch_and_save_tips_real_yields(args.output)
        print(f"Saved TIPS real yields to {output}")
        return

    if args.command == "fetch-dealer-positions":
        from durshift.data.ny_fed_dealers import fetch_and_save_dealer_positions

        output = fetch_and_save_dealer_positions(args.output)
        print(f"Saved dealer positions to {output}")
        return

    if args.command == "fetch-tips-frn-auctions":
        from durshift.data.treasurydirect_api import fetch_and_save_tips_frn

        output = fetch_and_save_tips_frn(args.output, start_date=args.min_date)
        print(f"Saved TIPS+FRN auctions to {output}")
        return

    if args.command == "fetch-soma-holdings":
        from durshift.data.soma_holdings import fetch_and_save_soma_summary

        output = fetch_and_save_soma_summary(args.output)
        print(f"Saved SOMA holdings to {output}")
        return

    raise SystemExit("Unknown command.")


if __name__ == "__main__":
    main()
