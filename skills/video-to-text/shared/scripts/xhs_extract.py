#!/usr/bin/env python3
"""Extract Xiaohongshu note metadata from an SSR HTML page."""
import argparse
import html
import json
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse


XHS_NOTE_RE = re.compile(
    r'^/(?:explore|discovery/item)/([0-9a-fA-F]{24})(?:[/#?]|$)'
)
XHS_PROFILE_NOTE_RE = re.compile(
    r'^/user/profile/[^/]+/([0-9a-fA-F]{24})(?:[/#?]|$)'
)
INITIAL_STATE_RE = re.compile(
    r'window\.__INITIAL_STATE__\s*=\s*(.*?)</script>',
    re.DOTALL,
)
JS_LITERAL_RE = re.compile(r'(?<=[:,\[])\s*(undefined|NaN|Infinity|-Infinity)(?=\s*[,}\]])')


class XhsError(Exception):
    exit_code = 1


class UrlParseError(XhsError):
    exit_code = 2


class AuthError(XhsError):
    exit_code = 3


class NoVideoError(XhsError):
    exit_code = 4


class StateParseError(XhsError):
    exit_code = 5


def parse_note_url(url):
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if not (host == 'www.xiaohongshu.com' or host.endswith('.xiaohongshu.com')):
        raise UrlParseError('not a xiaohongshu.com URL')

    match = XHS_NOTE_RE.match(parsed.path) or XHS_PROFILE_NOTE_RE.match(parsed.path)
    if not match:
        raise UrlParseError('expected /explore/<note_id> URL with a 24-char note id')

    query = parse_qs(parsed.query)
    xsec_token = first_query_value(query, 'xsec_token')
    if not xsec_token:
        raise UrlParseError('missing xsec_token in Xiaohongshu note URL')

    note_id = match.group(1).lower()
    canonical_query = {'xsec_token': xsec_token}
    xsec_source = first_query_value(query, 'xsec_source')
    if xsec_source:
        canonical_query['xsec_source'] = xsec_source

    return {
        'note_id': note_id,
        'xsec_token': xsec_token,
        'xsec_source': xsec_source,
        'canonical_url': 'https://www.xiaohongshu.com/explore/{}?{}'.format(
            note_id,
            urlencode(canonical_query),
        ),
    }


def first_query_value(query, name):
    values = query.get(name) or []
    return values[0] if values else ''


def load_initial_state(html_text):
    match = INITIAL_STATE_RE.search(html_text)
    if not match:
        if looks_like_auth_wall(html_text):
            raise AuthError('Xiaohongshu returned a login, captcha, or access wall')
        raise StateParseError('window.__INITIAL_STATE__ not found')

    raw = html.unescape(match.group(1).strip())
    raw = raw[:-1].rstrip() if raw.endswith(';') else raw
    raw = JS_LITERAL_RE.sub('null', raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise StateParseError('failed to parse window.__INITIAL_STATE__: {}'.format(exc)) from exc


def looks_like_auth_wall(html_text):
    needles = (
        '验证码',
        '登录后查看',
        '安全验证',
        '访问受限',
        'no-access',
        'captcha',
    )
    return any(needle in html_text for needle in needles)


def extract_note(state, note_id):
    note_store = state.get('note') if isinstance(state, dict) else None
    detail_map = note_store.get('noteDetailMap', {}) if isinstance(note_store, dict) else {}
    detail = detail_map.get(note_id)
    if isinstance(detail, dict) and isinstance(detail.get('note'), dict):
        return detail['note']

    current_note_id = note_store.get('currentNoteId') if isinstance(note_store, dict) else ''
    if current_note_id and current_note_id in detail_map:
        detail = detail_map[current_note_id]
        if isinstance(detail, dict) and isinstance(detail.get('note'), dict):
            return detail['note']

    for item in walk_dicts(state):
        item_id = item.get('noteId') or item.get('note_id')
        if item_id == note_id:
            return item

    raise StateParseError('note {} not found in SSR state'.format(note_id))


def walk_dicts(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_dicts(child)


def build_desc(note):
    title = clean_text(note.get('title', ''))
    desc = clean_text(note.get('desc', ''))
    parts = []
    if title:
        parts.append(title)
    if desc and desc != title:
        parts.append(desc)

    tag_names = []
    for tag in note.get('tagList') or []:
        if not isinstance(tag, dict):
            continue
        name = clean_text(tag.get('name', ''))
        if name:
            tag_names.append(name)

    body = '\n'.join(parts).strip()
    missing_tags = []
    for name in tag_names:
        if '#{}'.format(name) not in body and '{}[话题]'.format(name) not in body:
            missing_tags.append('#{}'.format(name))

    if missing_tags:
        body = (body + '\n' if body else '') + ' '.join(missing_tags)

    return body


def clean_text(value):
    if value is None:
        return ''
    return str(value).replace('\r\n', '\n').replace('\r', '\n').strip()


def extract_video_url(note):
    if note.get('type') and note.get('type') != 'video':
        raise NoVideoError('note is not a video note')

    video = note.get('video')
    if not isinstance(video, dict):
        raise NoVideoError('note has no video payload')

    candidates = []
    media = video.get('media')
    if isinstance(media, dict):
        candidates.extend(video_stream_candidates(media.get('stream')))

    media_v2 = video.get('mediaV2')
    if isinstance(media_v2, str) and media_v2.strip():
        try:
            media_v2_obj = json.loads(media_v2)
        except json.JSONDecodeError:
            media_v2_obj = None
        if isinstance(media_v2_obj, dict):
            candidates.extend(video_stream_candidates(media_v2_obj.get('stream')))
            candidates.extend(opaque_stream_candidates(media_v2_obj))

    candidates.extend(opaque_stream_candidates(video))
    candidates.extend(recursive_url_candidates(video))

    best = choose_best_candidate(candidates)
    if not best:
        raise NoVideoError('video note has no downloadable mp4 stream')
    return best['url']


def video_stream_candidates(stream):
    candidates = []
    if not isinstance(stream, dict):
        return candidates

    # Prefer broadly compatible H.264 before newer codecs.
    for codec in ('h264', 'h265', 'h266', 'av1'):
        entries = stream.get(codec) or []
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            url = entry.get('masterUrl') or entry.get('master_url')
            if url:
                candidates.append({
                    'url': url,
                    'codec': codec,
                    'height': number(entry.get('height')),
                    'width': number(entry.get('width')),
                    'bitrate': number(entry.get('avgBitrate') or entry.get('avg_bitrate')),
                    'size': number(entry.get('size')),
                })
    return candidates


def opaque_stream_candidates(value):
    candidates = []
    opaque = value.get('opaque1') if isinstance(value, dict) else None
    if not isinstance(opaque, dict):
        return candidates
    for key in ('hd_screencast_stream', 'default_screencast_stream'):
        url = opaque.get(key)
        if url:
            candidates.append({'url': url, 'codec': 'h264', 'height': 0, 'width': 0, 'bitrate': 0, 'size': 0})
    return candidates


def recursive_url_candidates(value):
    candidates = []
    for item in walk_dicts(value):
        for key in ('masterUrl', 'master_url'):
            url = item.get(key)
            if url:
                candidates.append({
                    'url': url,
                    'codec': 'unknown',
                    'height': number(item.get('height')),
                    'width': number(item.get('width')),
                    'bitrate': number(item.get('avgBitrate') or item.get('avg_bitrate')),
                    'size': number(item.get('size')),
                })
    return candidates


def number(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def choose_best_candidate(candidates):
    seen = set()
    unique = []
    for candidate in candidates:
        url = candidate.get('url')
        if not url or url in seen:
            continue
        if '.mp4' not in urlparse(url).path.lower():
            continue
        seen.add(url)
        unique.append(candidate)
    if not unique:
        return None

    codec_rank = {'h264': 3, 'unknown': 2, 'h265': 1, 'h266': 1, 'av1': 1}
    unique.sort(
        key=lambda item: (
            codec_rank.get(item.get('codec'), 0),
            item.get('height', 0),
            item.get('width', 0),
            item.get('bitrate', 0),
            item.get('size', 0),
        ),
        reverse=True,
    )
    return unique[0]


def extract_note_info(html_path, url):
    parsed = parse_note_url(url)
    html_text = Path(html_path).read_text(encoding='utf-8')
    state = load_initial_state(html_text)
    note = extract_note(state, parsed['note_id'])
    return {
        'platform': 'xhs',
        'note_id': parsed['note_id'],
        'content_id': parsed['note_id'],
        'canonical_url': parsed['canonical_url'],
        'title': clean_text(note.get('title', '')),
        'desc': build_desc(note),
        'video_url': extract_video_url(note),
    }


def print_json(data):
    print(json.dumps(data, ensure_ascii=False, separators=(',', ':')))


def print_field(path, field):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    value = data.get(field, '')
    if isinstance(value, (dict, list)):
        print_json(value)
    else:
        print(value)


def main(argv):
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command', required=True)

    parse_url_parser = subparsers.add_parser('parse-url')
    parse_url_parser.add_argument('url')

    extract_parser = subparsers.add_parser('extract')
    extract_parser.add_argument('html_path')
    extract_parser.add_argument('url')

    field_parser = subparsers.add_parser('field')
    field_parser.add_argument('json_path')
    field_parser.add_argument('field')

    args = parser.parse_args(argv)
    try:
        if args.command == 'parse-url':
            print_json(parse_note_url(args.url))
        elif args.command == 'extract':
            print_json(extract_note_info(args.html_path, args.url))
        elif args.command == 'field':
            print_field(args.json_path, args.field)
    except XhsError as exc:
        print(str(exc), file=sys.stderr)
        return exc.exit_code
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
