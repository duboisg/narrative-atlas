"""Command-line interface."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .client import AzureCompletionClient, ResilientExtractor
from .config import Settings
from .extractors import SPECS
from .ingest import load_document
from .pipeline import NarrativePipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="narrative-atlas",
        description="Turn long-form narrative documents into structured, linked datasets.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest = subparsers.add_parser("ingest", help="Extract a PDF or normalize a text document")
    ingest.add_argument("source", type=Path)
    ingest.add_argument("--output", type=Path, required=True)

    analyze = subparsers.add_parser("analyze", help="Run the narrative extraction pipeline")
    analyze.add_argument("source", type=Path)
    analyze.add_argument("--output", type=Path, default=Path("workspace/output"))
    analyze.add_argument("--extract", nargs="+", choices=sorted(SPECS), default=sorted(SPECS))
    analyze.add_argument("--max-characters", type=int, default=24_000)
    analyze.add_argument("--overlap-characters", type=int, default=2_000)
    analyze.add_argument("--no-resume", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if args.command == "ingest":
        text = load_document(args.source)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
        print(f"Wrote {len(text):,} characters to {args.output}")
        return 0

    settings = Settings.from_env()
    client = AzureCompletionClient(settings)
    extractor = ResilientExtractor(client, request_delay=settings.request_delay)
    pipeline = NarrativePipeline(extractor, args.output)
    text = load_document(args.source)
    results = pipeline.run(
        text,
        kinds=args.extract,
        max_characters=args.max_characters,
        overlap_characters=args.overlap_characters,
        resume=not args.no_resume,
    )
    summary = ", ".join(f"{kind}={len(items)}" for kind, items in results.items())
    print(f"Extraction complete: {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
