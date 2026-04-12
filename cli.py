#!/usr/bin/env python3
"""Recipe Extractor CLI.

Usage:
    python cli.py <url>              # print markdown to stdout
    python cli.py <url> --json       # print JSON to stdout
    python cli.py <url> --out recipe.md   # write markdown to file
    python cli.py <url> --out recipe.json # write JSON to file
"""
import argparse
import json
import sys
import requests

from extractor import extract_recipe


def main():
    parser = argparse.ArgumentParser(description="Extract a recipe from a URL")
    parser.add_argument("url", help="URL of the recipe page")
    parser.add_argument("--json", action="store_true", help="Output full JSON instead of Markdown")
    parser.add_argument("--out", metavar="FILE", help="Write output to FILE (.md or .json)")
    args = parser.parse_args()

    try:
        result = extract_recipe(args.url)
    except (ValueError, requests.HTTPError, requests.ConnectionError) as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Determine output format
    if (args.out and args.out.endswith(".json")) or args.json:
        content = json.dumps(
            {"schema": result.schema, "markdown": result.markdown,
             "strategy": result.strategy, "title": result.title, "url": result.url},
            indent=2,
        )
    else:
        content = result.markdown

    if args.out:
        with open(args.out, "w") as f:
            f.write(content)
        print(f"Saved to {args.out}")
    else:
        print(content)


if __name__ == "__main__":
    main()
