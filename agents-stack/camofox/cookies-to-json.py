#!/usr/bin/env python3
"""Convert a Netscape cookies.txt export to the camofox cookie-import JSON.

Usage:
    python3 cookies-to-json.py cookies.txt -o cookies.json
    python3 cookies-to-json.py cookies.txt > cookies.json

Then POST the output to /sessions/<userId>/cookies
(Authorization: Bearer <CAMOFOX_API_KEY>, max 500 cookies per request).

Export the cookies.txt with a local-only exporter (e.g. the "Get cookies.txt
LOCALLY" browser extension) — never upload session cookies anywhere.
"""

import argparse
import json
import sys

MAX_PER_REQUEST = 500


def parse_line(line):
    """Parse one Netscape line into a camofox cookie object (or None to skip)."""
    http_only = False
    if line.startswith('#HttpOnly_'):
        http_only = True
        line = line[len('#HttpOnly_'):]
    parts = line.split('\t')
    if len(parts) != 7:
        return None
    domain, _, path, secure, expires, name, value = parts
    try:
        expires = int(expires) if expires else 0
    except ValueError:
        expires = 0
    if not name or not domain:
        return None
    return {
        'domain': domain,
        'path': path or '/',
        'secure': secure.upper() == 'TRUE',
        'expires': expires,
        'httpOnly': http_only,
        'name': name,
        'value': value,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', help='Netscape cookies.txt file')
    parser.add_argument('-o', '--output', default='-',
                        help='output JSON file (default: stdout)')
    args = parser.parse_args()

    cookies = []
    skipped = 0
    # utf-8-sig transparently strips a BOM (Windows editors love those)
    with open(args.input, encoding='utf-8-sig') as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith('#') and not line.startswith('#HttpOnly_'):
                continue
            cookie = parse_line(line)
            if cookie is None:
                skipped += 1
            else:
                cookies.append(cookie)

    if skipped:
        print(f'warning: skipped {skipped} malformed lines', file=sys.stderr)
    if len(cookies) > MAX_PER_REQUEST:
        print(f'warning: {len(cookies)} cookies exceed the {MAX_PER_REQUEST}/request '
              f'import limit — split the file', file=sys.stderr)

    payload = json.dumps({'cookies': cookies}, indent=2)
    if args.output == '-':
        print(payload)
    else:
        with open(args.output, 'w', encoding='utf-8') as fh:
            fh.write(payload + '\n')
        print(f'wrote {len(cookies)} cookies to {args.output}', file=sys.stderr)


if __name__ == '__main__':
    main()
