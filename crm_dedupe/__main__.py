import argparse
import sys

from .core import find_duplicates, naive_duplicates, load_csv, report


def main(argv=None):
    p = argparse.ArgumentParser(prog="crm-dedupe", description="Find duplicate company records in CSV exports.")
    p.add_argument("csv", nargs="+", help="one or more CSV files (columns: name, website or email, country)")
    p.add_argument("--threshold", type=float, default=0.88, help="fuzzy name threshold (default 0.88)")
    args = p.parse_args(argv)
    records = []
    for path in args.csv:
        records.extend(load_csv(path))
    clusters = find_duplicates(records, args.threshold)
    print(report(records, clusters, naive_duplicates(records)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
