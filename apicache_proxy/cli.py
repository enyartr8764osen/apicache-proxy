"""Command-line interface for apicache-proxy."""

import argparse
import sys
import json
from pathlib import Path

from apicache_proxy.proxy import CachingProxy
from apicache_proxy.storage import DiskStorage


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="apicache-proxy",
        description="Lightweight local caching proxy for REST APIs.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- get sub-command ---
    get_cmd = subparsers.add_parser("get", help="Perform a cached GET request.")
    get_cmd.add_argument("url", help="Target URL")
    get_cmd.add_argument(
        "--ttl", type=int, default=300, help="Cache TTL in seconds (default: 300)"
    )
    get_cmd.add_argument(
        "--cache-dir", default=".apicache", help="Directory for cache storage"
    )
    get_cmd.add_argument(
        "--bypass", action="store_true", help="Bypass cache and force network call"
    )
    get_cmd.add_argument(
        "--headers", type=json.loads, default={}, metavar="JSON",
        help='Extra request headers as a JSON string, e.g. \'{"Authorization": "Bearer tok"}\'',
    )

    # --- clear sub-command ---
    clear_cmd = subparsers.add_parser("clear", help="Clear all cached entries.")
    clear_cmd.add_argument(
        "--cache-dir", default=".apicache", help="Directory for cache storage"
    )

    # --- stats sub-command ---
    stats_cmd = subparsers.add_parser("stats", help="Show cache statistics.")
    stats_cmd.add_argument(
        "--cache-dir", default=".apicache", help="Directory for cache storage"
    )

    return parser


def cmd_get(args: argparse.Namespace) -> int:
    storage = DiskStorage(cache_dir=args.cache_dir)
    proxy = CachingProxy(storage=storage, default_ttl=args.ttl)
    response = proxy.get(args.url, headers=args.headers, bypass_cache=args.bypass)
    print(json.dumps(response, indent=2, default=str))
    return 0


def cmd_clear(args: argparse.Namespace) -> int:
    storage = DiskStorage(cache_dir=args.cache_dir)
    removed = storage.clear()
    print(f"Cleared {removed} cached entry/entries from '{args.cache_dir}'.")
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    storage = DiskStorage(cache_dir=args.cache_dir)
    stats = storage.stats()
    print(json.dumps(stats, indent=2))
    return 0


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    dispatch = {
        "get": cmd_get,
        "clear": cmd_clear,
        "stats": cmd_stats,
    }
    return dispatch[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
