"""CLI entry point for autowiki."""

import argparse
import sys
from pathlib import Path

from .wiki import init_wiki, get_wiki_path
from .lint import lint
from .query import search, get_page, list_pages
from .index import rebuild_index


def main():
    parser = argparse.ArgumentParser(
        prog="autowiki",
        description="Self-validating knowledge compiler  -  build a reusable KB from documents",
    )
    sub = parser.add_subparsers(dest="command")

    # init
    p_init = sub.add_parser("init", help="Initialize a new wiki")
    p_init.add_argument("--path", default=None, help="Wiki path (default: ~/wiki)")
    p_init.add_argument("--domain", default="General", help="Wiki domain description")

    # lint
    p_lint = sub.add_parser("lint", help="Health-check the wiki")
    p_lint.add_argument("--path", default=None, help="Wiki path")
    p_lint.add_argument("--verbose", "-v", action="store_true", help="Show fix suggestions")

    # search
    p_search = sub.add_parser("search", help="Search the wiki")
    p_search.add_argument("query", help="Search terms")
    p_search.add_argument("--path", default=None, help="Wiki path")
    p_search.add_argument("--type", choices=["entity", "concept", "comparison", "claim", "query"],
                          help="Filter by page type")
    p_search.add_argument("--tag", action="append", help="Filter by tag (repeatable)")
    p_search.add_argument("--limit", type=int, default=10, help="Max results")

    # show
    p_show = sub.add_parser("show", help="Show a wiki page")
    p_show.add_argument("slug", help="Page slug")
    p_show.add_argument("--path", default=None, help="Wiki path")

    # list
    p_list = sub.add_parser("list", help="List wiki pages")
    p_list.add_argument("--path", default=None, help="Wiki path")
    p_list.add_argument("--section", choices=["entities", "concepts", "comparisons", "claims", "queries"],
                        help="Filter by section")

    # index (rebuild)
    p_idx = sub.add_parser("index", help="Rebuild index.md from pages")
    p_idx.add_argument("--path", default=None, help="Wiki path")
    p_idx.add_argument("--write", action="store_true", help="Write to index.md (default: print to stdout)")

    # validate
    p_val = sub.add_parser("validate", help="Validate raw source drift")
    p_val.add_argument("--path", default=None, help="Wiki path")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    wiki = get_wiki_path(getattr(args, "path", None))

    if args.command == "init":
        path = init_wiki(args.path, args.domain)
        print(f"Wiki initialized at {path}")

    elif args.command == "lint":
        report = lint(wiki, verbose=args.verbose)
        print(report)

    elif args.command == "search":
        types = [args.type] if args.type else None
        results = search(wiki, args.query, types=types, tags=args.tag, limit=args.limit)
        if not results:
            print(f"No results for: {args.query}")
        for i, r in enumerate(results):
            print(f"\n{i+1}. [[{r['slug']}]] ({r['type']})  -  score: {r['score']}")
            print(f"   {r['title']}")
            if r['snippet']:
                print(f"   \"{r['snippet']}\"")

    elif args.command == "show":
        page = get_page(wiki, args.slug)
        if page:
            print(page["content"])
        else:
            print(f"Page not found: {args.slug}")

    elif args.command == "list":
        pages = list_pages(wiki, section=args.section)
        for p in pages:
            print(f"  [{p['type']}] {p['title']}  ({p['slug']})")

    elif args.command == "index":
        new_index = rebuild_index(wiki)
        if args.write:
            (wiki / "index.md").write_text(new_index)
            print(f"index.md rebuilt with {new_index.count('[[[')} pages")
        else:
            print(new_index)

    elif args.command == "validate":
        from .wiki import check_drift
        raw_dir = wiki / "raw"
        drifted = []
        if raw_dir.exists():
            for f in raw_dir.rglob("*.md"):
                if check_drift(f):
                    drifted.append(str(f.relative_to(wiki)))
        if drifted:
            print(f"DRIFT detected in {len(drifted)} files:")
            for d in drifted:
                print(f"  {d}")
        else:
            print("All raw sources unchanged.")


if __name__ == "__main__":
    main()
