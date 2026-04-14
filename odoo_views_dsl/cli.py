"""CLI entry point: ``odoo-views compile|check <path>``."""
from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    """Entry point for the ``odoo-views`` command."""
    parser = argparse.ArgumentParser(
        prog='odoo-views',
        description='Compile Python DSL definitions to Odoo XML views.',
    )
    sub = parser.add_subparsers(dest='command')

    # ── compile ──
    p_compile = sub.add_parser('compile', help='Compile DSL → XML')
    p_compile.add_argument('path', help='Module directory or Python file')
    p_compile.add_argument(
        '-o', '--output', default=None,
        help='Output directory  (default: <path>/views/)',
    )

    # ── check ──
    p_check = sub.add_parser('check', help='Validate without writing files')
    p_check.add_argument('path', help='Module directory or Python file')

    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    from .compiler import compile_module

    if args.command == 'compile':
        result = compile_module(args.path, args.output)
        if result:
            for fname in result:
                print(f'  [ok] {fname}')
            print(f'\n{len(result)} file(s) generated.')
        else:
            print('  [!] No DSL definitions found.')
        return 0

    if args.command == 'check':
        result = compile_module(args.path, dry_run=True)
        if result:
            print(f'  [ok] Validated ({len(result)} file(s) would be generated)')
        else:
            print('  [!] No DSL definitions found.')
        return 0

    return 1


if __name__ == '__main__':
    sys.exit(main())
