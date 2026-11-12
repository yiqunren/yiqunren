"""共用寫入權的本機入口；不啟動模型，也不修改登記範圍內的檔案。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.write_ownership import OwnershipError, configured_registry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    commands.add_parser('list')
    claim = commands.add_parser('claim')
    claim.add_argument('--project', required=True)
    claim.add_argument('--files', nargs='+', required=True)
    claim.add_argument('--holder', required=True)
    claim.add_argument('--ttl', type=int, default=300)
    for action in ('renew', 'release', 'unknown', 'resolve'):
        command = commands.add_parser(action)
        command.add_argument('--lease', required=True)
        command.add_argument('--holder', required=True)
        if action == 'renew':
            command.add_argument('--ttl', type=int, default=300)
        if action == 'resolve':
            command.add_argument('--confirmed-stopped', action='store_true')
    args = parser.parse_args()
    try:
        registry = configured_registry()
        if args.action == 'list':
            result = registry.list()
        elif args.action == 'claim':
            result = registry.claim(args.project, args.files, args.holder, args.ttl)
        else:
            result = registry.change(args.lease, args.holder, args.action,
                ttl=getattr(args, 'ttl', 300), stopped=getattr(args, 'confirmed_stopped', False))
        print(json.dumps({'ok': True, 'data': result}, ensure_ascii=False))
        return 0
    except OwnershipError as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
