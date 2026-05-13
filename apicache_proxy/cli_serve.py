"""CLI sub-command ``serve`` – start the local caching proxy HTTP server."""
from __future__ import annotations

import argparse
import logging

from .server import serve


def add_serve_subparser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    """Register the ``serve`` sub-command on *subparsers*."""
    p = subparsers.add_parser(
        "serve",
        help="Start the local caching proxy HTTP server.",
        description=(
            "Launch a lightweight HTTP proxy that caches upstream API responses "
            "locally so that repeated requests during development are served from "
            "disk instead of hitting the network."
        ),
    )
    p.add_argument(
        "--host",
        default="127.0.0.1",
        help="Interface to bind to (default: 127.0.0.1).",
    )
    p.add_argument(
        "--port",
        type=int,
        default=8080,
        help="TCP port to listen on (default: 8080).",
    )
    p.add_argument(
        "--cache-dir",
        default=".apicache",
        dest="cache_dir",
        help="Directory used to persist cached responses (default: .apicache).",
    )
    p.add_argument(
        "--ttl",
        type=int,
        default=300,
        dest="default_ttl",
        help="Default cache TTL in seconds (default: 300).",
    )
    p.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        dest="log_level",
        help="Logging verbosity (default: INFO).",
    )
    p.set_defaults(func=cmd_serve)


def cmd_serve(args: argparse.Namespace) -> None:
    """Entry-point called by the CLI when ``serve`` is chosen."""
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    serve(
        host=args.host,
        port=args.port,
        cache_dir=args.cache_dir,
        default_ttl=args.default_ttl,
    )
