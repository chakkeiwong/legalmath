"""Exact-byte, date-qualified archive records; no publication/authenticity inference."""
from copy import deepcopy
from datetime import timezone
from email.parser import Parser
from email.utils import parsedate_to_datetime
import json
import re
from urllib.parse import urlsplit

from .admissions import review
from .anchors import fields
from .contracts import bound_path, digest, timestamp

VERSION = 'source-archive-observations.v1'
TEXTSEARCH_VERSION = 'source-archive-observations.textsearch.v1'


def _textsearch_url(value):
    if not isinstance(value, str) or any(c.isspace() for c in value):
        raise ValueError('Explicit text-search original URL required')
    url = urlsplit(value)
    if (url.scheme not in {'http', 'https'} or not url.hostname or url.username is not None
            or url.password is not None or url.fragment or url.port is not None):
        raise ValueError('Unsupported text-search original URL')
    return url


def _textsearch_metadata(index, row, headers, replay, content, root):
    """Retain a narrower replay observation, including unresolved URL spelling."""
    if index.get('linkToService') != 'https://arquivo.pt':
        raise ValueError('Unsupported text-search service')
    parameters = index.get('request_parameters')
    if not isinstance(parameters, dict) or not isinstance(parameters.get('q'), str) or not parameters['q'].strip():
        raise ValueError('Retained full-text search query required')
    original = _textsearch_url(row['original_url'])
    memento = _textsearch_url(row['memento_original_url'])
    if (original.hostname.removeprefix('www.') != memento.hostname.removeprefix('www.')
            or original.path != memento.path or original.query != memento.query):
        raise ValueError('Unsupported index/Memento URL variation')
    receipt = json.loads(_bytes(root, row['receipt'], 2 * 1024 * 1024))
    requests = receipt.get('requests') if isinstance(receipt, dict) else None
    position = row['receipt_request_index']
    if (not isinstance(requests, list) or any(not isinstance(r, dict) for r in requests)
            or type(position) is not int or not 0 <= position < len(requests)):
        raise ValueError('Exact archive acquisition request required')
    request = requests[position]
    argv = request.get('argv')
    if (not isinstance(argv, list) or not argv or any(not isinstance(v, str) for v in argv)
            or argv[0] != 'curl' or argv[-1] != replay or argv.count(replay) != 1
            or request.get('http_status') != 200 or request.get('curl_exit_code') != 0
            or type(request.get('bytes')) is not int or request['bytes'] != len(content)
            or request.get('sha256') != row['content']['sha256']
            or request.get('headers_sha256') != row['headers']['sha256']):
        raise ValueError('Archive acquisition receipt differs from replay evidence')
    for flag, key in (('--output', 'content'), ('--dump-header', 'headers')):
        if argv.count(flag) != 1 or argv.index(flag) + 1 >= len(argv):
            raise ValueError('Archive acquisition path missing or ambiguous')
        if bound_path(root, argv[argv.index(flag) + 1]) != bound_path(root, row[key]['path']):
            raise ValueError('Archive acquisition path differs from bound evidence')
    event = json.loads(_bytes(root, row['retrieval_record'], 128 * 1024))
    outputs = json.loads(_bytes(root, row['retained_outputs'], 2 * 1024 * 1024))
    if not isinstance(event, dict) or not isinstance(outputs, dict):
        raise ValueError('Retained acquisition record and outputs must be objects')
    event_body = {k: v for k, v in event.items() if k != 'sha256'}
    event_hash = digest(json.dumps(event_body, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode())
    if (event.get('kind') != 'RECORD' or event.get('sha256') != event_hash
            or event.get('outputs_sha256') != row['retained_outputs']['sha256']
            or _time(event.get('at')) != _time(row['retrieved_at'])):
        raise ValueError('Retained acquisition upper-bound record differs')
    folder = bound_path(root, row['retained_outputs']['path']).parent
    if bound_path(root, event.get('attempt', '')) != folder:
        raise ValueError('Retained acquisition attempt differs')
    for key in ('index', 'headers', 'content', 'receipt'):
        path = bound_path(root, row[key]['path'])
        if not path.is_relative_to(folder) or outputs.get(str(path.relative_to(folder))) != row[key]['sha256']:
            raise ValueError('Retained acquisition outputs do not bind ' + key)
    return {
        'memento_original_url': row['memento_original_url'],
        'original_url_equivalence': ('EXACT_STRING_MATCH' if row['original_url'] == row['memento_original_url'] else 'NOT_ESTABLISHED'),
        'archive_index_http_status': index['response_items'][row['record_index']].get('statusCode', 'UNKNOWN'),
        'replay_http_status': 200,
        'evidence_known_from_basis': 'SUPPLIED_RETAINED_OUTPUTS_RECORD_UPPER_BOUND',
        'independent_source_comparison': False,
    }


def _time(value):
    if not isinstance(value, str):
        raise ValueError('Archive times require timezone-qualified strings')
    return timestamp(value)


def _bytes(root, binding, maximum):
    fields(binding, {'path', 'sha256'}, {'path', 'sha256'})
    if not isinstance(binding['path'], str) or not isinstance(binding['sha256'], str):
        raise ValueError('Archive file binding requires path and hash strings')
    path = bound_path(root, binding['path'])
    if not 0 < path.stat().st_size <= maximum:
        raise ValueError('Archive evidence exceeds the bounded file size')
    raw = path.read_bytes()
    if digest(raw) != binding['sha256']:
        raise ValueError('Archive evidence bytes changed')
    return raw


def _headers(raw):
    lines = raw.decode('iso-8859-1').replace('\r\n', '\n').split('\n')
    blocks = [i for i, line in enumerate(lines) if line.startswith('HTTP/')]
    if not blocks or not re.fullmatch(r'HTTP/\d(?:\.\d)? 200(?: .*)?', lines[blocks[-1]]):
        raise ValueError('Archive response must end with HTTP 200')
    headers = Parser().parsestr('\n'.join(lines[blocks[-1] + 1:]))
    result = {}
    for name in ('Content-Type', 'Content-Length', 'Date', 'Memento-Datetime', 'Link'):
        values = headers.get_all(name, [])
        if len(values) != 1:
            raise ValueError('Archive response requires one ' + name + ' header')
        result[name] = values[0].strip()
    if result['Content-Type'].split(';', 1)[0].strip().lower() != 'application/pdf':
        raise ValueError('Archive response is not a PDF')
    return result


def _http_time(value):
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError) as exc:
        raise ValueError('Invalid archive HTTP date') from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError('Archive HTTP date requires timezone')
    return parsed


def admit(bundle, packet, root):
    """Bind supplied Arquivo/Memento evidence, preserving two distinct query dates."""
    keys = {'version', 'query_at', 'review', 'captures'}
    fields(packet, keys, keys)
    if packet['version'] not in {VERSION, TEXTSEARCH_VERSION}:
        raise ValueError('Unsupported archive observation profile')
    textsearch = packet['version'] == TEXTSEARCH_VERSION
    review(packet['review'])
    query_at, known_at = _time(packet['query_at']), _time(bundle['known_at'])
    if not isinstance(packet['captures'], list) or not 1 <= len(packet['captures']) <= 64:
        raise ValueError('One to 64 explicit archive captures required')
    documents = {d['id']: d for d in bundle['documents']}
    identities, observations = set(), []
    for row in packet['captures']:
        names = {'id', 'document', 'source_sha256', 'original_url', 'capture_at', 'retrieved_at',
                 'index', 'record_index', 'headers', 'content'}
        if textsearch:
            names |= {'memento_original_url', 'receipt', 'receipt_request_index', 'retrieval_record', 'retained_outputs'}
        fields(row, names, names)
        if not isinstance(row['id'], str) or not row['id'] or row['id'] in identities:
            raise ValueError('Distinct archive capture identity required')
        identities.add(row['id'])
        if not isinstance(row['document'], str):
            raise ValueError('Archive document identity must be a string')
        document = documents.get(row['document'])
        if document is None or document['sha256'] != row['source_sha256']:
            raise ValueError('Archive observation source edition differs')
        original_url = row['original_url']
        url = urlsplit(original_url) if isinstance(original_url, str) else None
        if (url is None or url.scheme not in {'http', 'https'} or not url.hostname or
                url.username is not None or url.password is not None or url.fragment):
            raise ValueError('Explicit original archive URL required')
        capture_at, retrieved_at = _time(row['capture_at']), _time(row['retrieved_at'])
        index = json.loads(_bytes(root, row['index'], 2 * 1024 * 1024))
        if not isinstance(index, dict):
            raise ValueError('Archive index response must be an object')
        records, position = index.get('response_items'), row['record_index']
        if (not isinstance(records, list) or any(not isinstance(r, dict) for r in records)
                or type(position) is not int or not 0 <= position < len(records)):
            raise ValueError('Exact archive index record required')
        record = records[position]
        stamp = capture_at.astimezone(timezone.utc).strftime('%Y%m%d%H%M%S')
        status_ok = (('statusCode' not in record or type(record['statusCode']) is int and record['statusCode'] == 200)
                     if textsearch else record.get('statusCode') == 200)
        if (capture_at.microsecond or record.get('tstamp') != stamp or record.get('originalURL') != original_url
                or record.get('mimeType') != 'application/pdf' or not status_ok):
            raise ValueError('Archive index URL, date or PDF status differs')
        if sum(r.get('tstamp') == stamp and r.get('originalURL') == original_url for r in records) != 1:
            raise ValueError('Archive index record is ambiguous')
        replay = 'https://arquivo.pt/noFrame/replay/' + stamp + 'id_/' + original_url
        if record.get('linkToOriginalFile') != replay:
            raise ValueError('Unsupported or inconsistent archive original-file URL')
        headers = _headers(_bytes(root, row['headers'], 128 * 1024))
        response_at = _http_time(headers['Date'])
        if _http_time(headers['Memento-Datetime']) != capture_at:
            raise ValueError('Memento date differs from archive capture')
        originals = re.findall(r'<([^>]+)>\s*;\s*rel="original"(?:\s*;[^,]*)?(?=,|$)', headers['Link'])
        if originals != [row['memento_original_url'] if textsearch else original_url]:
            raise ValueError('Archive response original URL differs or is ambiguous')
        if not capture_at <= response_at <= retrieved_at:
            raise ValueError('Capture, HTTP response and supplied retrieval times disagree')
        content = _bytes(root, row['content'], 32 * 1024 * 1024)
        source = _bytes(root, {'path': document['path'], 'sha256': document['sha256']}, 32 * 1024 * 1024)
        if not content.startswith(b'%PDF-') or content != source:
            raise ValueError('Archive PDF differs from the complete source bytes')
        if not re.fullmatch(r'[0-9]+', headers['Content-Length']) or int(headers['Content-Length']) != len(content):
            raise ValueError('Archive HTTP content length differs from retained bytes')
        extra = _textsearch_metadata(index, row, headers, replay, content, root) if textsearch else {}
        if textsearch:
            extra['source_origin'] = ('SAME_RETAINED_ARCHIVE_REPLAY'
                if bound_path(root, document['path']) == bound_path(root, row['content']['path'])
                else 'BYTE_EQUAL_SUPPLIED_SOURCE')
        if retrieved_at > known_at:
            assessment = 'EVIDENCE_NOT_YET_KNOWN'
        elif capture_at > query_at:
            assessment = 'NOT_ESTABLISHED_BY_THIS_CAPTURE'
        else:
            assessment = 'ARCHIVE_RECORDED_BY_QUERY_DATE'
        observations.append({'id': row['id'], 'document': row['document'], 'source_sha256': document['sha256'],
            'original_url': original_url, 'replay_url': replay, 'source_byte_count': len(source),
            'archive_observed_by': row['capture_at'], 'archive_response_at': response_at.isoformat(),
            'evidence_known_from': row['retrieved_at'], 'query_at': packet['query_at'],
            'knowledge_at': bundle['known_at'], 'as_of_query': assessment,
            'publication_date': 'UNKNOWN', 'edition_authenticity': 'UNKNOWN',
            'earlier_absence_established': False, 'legal_availability_established': False,
            'evidence': deepcopy(row),
            'qualification': ('Conditional on the retained text-search/replay record and supplied local recording upper bound; '
                'index HTTP status may be unknown, differing original URLs are not proved equivalent, and byte equality '
                'does not provide independent authentication, original publication or legal availability' if textsearch else
                'Conditional on the retained archive record and supplied retrieval provenance; exact byte agreement does not authenticate original publication or establish legal availability'),
            **extra})
    return {'version': ('admitted-source-archive-observations.textsearch.v1' if textsearch else 'admitted-source-archive-observations.v1'), 'input_sha256': digest(packet),
            'query_at': packet['query_at'], 'knowledge_at': bundle['known_at'],
            'review': deepcopy(packet['review']), 'observations': observations,
            'independent_legal_acceptance': False}
