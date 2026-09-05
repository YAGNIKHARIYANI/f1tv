import os
import sys
import time
import json
import ssl
import re
import urllib.request
import urllib.parse
import urllib.error
from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, 'static')
os.makedirs(STATIC_DIR, exist_ok=True)

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path='')
CORS(app)

CHANNELS_API_URL = "https://cdn.f1live.dpdns.org/channels.json"
SCHEDULE_API_URL = "https://api.jolpi.ca/ergast/f1/2026/races/?format=json"
CACHE_TTL = 30  # seconds

cached_channels = []
last_fetch_time = 0

cached_schedule = []
last_schedule_time = 0

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9,gu;q=0.8",
    "Origin": "https://f1live.dpdns.org",
    "Referer": "https://f1live.dpdns.org/stream",
    "Sec-Ch-Ua": '"Not=A?Brand";v="99", "Google Chrome";v="151", "Chromium";v="151"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "Priority": "u=1, i"
}

# Fallback channel dataset
FALLBACK_CHANNELS = [
    {
        "id": 172218,
        "title": "[Clean] Sky Sports F1 FHD (50 FPS)",
        "uri": "https://alpha.f1live.dpdns.org/p/AwZGQwwEZA/index.m3u8?token=c1lhdWg1N0lxNldaaE12ZnJ0MkRsY1NtcVoyQnk2eUYzWXVkbUthcHhxekRxNEduaVp1UnBxU2VlWmF0ZnRlRGxaMm0wNStDbnJOOXJJM0puSytpbkE9PQ==",
        "timeline": 0,
        "status": "online",
        "is_embed": False,
        "blockable": False,
        "provider": "other",
        "updated_at": "2026-03-29T05:06:49.634688"
    },
    {
        "id": 20,
        "title": "[Embed] Sky Sports F1 [UK HD]",
        "uri": "https://videocdn-4726.website/shopping2/?channel_id=sky_sport_f1_uk",
        "timeline": 0,
        "status": "online",
        "is_embed": True,
        "blockable": False,
        "provider": "embed",
        "updated_at": "2026-04-23T19:20:02.144"
    },
    {
        "id": 154837,
        "title": "Sky Sports F1 (CDN Live TV)",
        "uri": "https://cdnlivetv.tv/api/v1/channels/player/?name=sky+sports+f1&code=gb&user=cdnlivetv&plan=free",
        "timeline": 0,
        "status": "online",
        "is_embed": True,
        "blockable": False,
        "provider": "embed",
        "updated_at": "2026-03-13T18:44:06.152377"
    },
    {
        "id": 21,
        "title": "F1 TV Pro HD",
        "uri": "https://hakunamatata5.org/hakunamatata5.html",
        "timeline": 0,
        "status": "online",
        "is_embed": True,
        "blockable": True,
        "provider": "embed",
        "updated_at": "2025-08-30T16:06:18.21799"
    },
    {
        "id": 172217,
        "title": "Sky Sports F1 UHD (4K Feed)",
        "uri": "https://a1xs.vip/2000016",
        "timeline": 0,
        "status": "online",
        "is_embed": False,
        "blockable": False,
        "provider": "other",
        "updated_at": "2026-03-29T05:06:11.890111"
    },
    {
        "id": 22,
        "title": "Sky Sports F1 HD",
        "uri": "https://vileembeds.pages.dev/embed/sky-sports-f1",
        "timeline": 0,
        "status": "online",
        "is_embed": True,
        "blockable": False,
        "provider": "embed",
        "updated_at": "2025-08-30T16:06:18.21799"
    },
    {
        "id": 2051,
        "title": "Sky Sports F1 Mirror 2",
        "uri": "https://junkieembeds.pages.dev/embed/sky-sports-f1",
        "timeline": 0,
        "status": "online",
        "is_embed": True,
        "blockable": False,
        "provider": "embed",
        "updated_at": "2025-08-31T10:32:48.52959"
    },
    {
        "id": 2054,
        "title": "Sky Sport Live 1",
        "uri": "https://pushembdz.store/embed/019ce27c-7352-7d6b-8ba3-f6117cbac2a4",
        "timeline": 0,
        "status": "online",
        "is_embed": True,
        "blockable": True,
        "provider": "embed",
        "updated_at": "2025-08-31T10:39:02.817511"
    },
    {
        "id": 18,
        "title": "[Embed] Sky Sports F1 GP Race",
        "uri": "https://embed.st/embed/admin/ppv-dutch-grand-prix-race/1",
        "timeline": 0,
        "status": "online",
        "is_embed": True,
        "blockable": False,
        "provider": "embed",
        "updated_at": "2026-08-22T16:15:05.505"
    },
    {
        "id": 1936,
        "title": "Sky Sports F1 Live Practice",
        "uri": "https://embedindia.st/embed/f1/2026/monaco/fp3",
        "timeline": 0,
        "status": "online",
        "is_embed": True,
        "blockable": False,
        "provider": "embed",
        "updated_at": "2025-08-31T09:33:05.499712"
    },
    {
        "id": 23,
        "title": "[Embed] Sky Sports Racing Origin",
        "uri": "https://streamfree.top/embed/racing/skyf1?server=origin&quality=1080p&category=racing",
        "timeline": 0,
        "status": "online",
        "is_embed": True,
        "blockable": False,
        "provider": "embed",
        "updated_at": "2025-08-30T16:06:18.21799"
    },
    {
        "id": 2052,
        "title": "ESPN 1 F1 Broadcast",
        "uri": "https://embedsports.top/embed/alpha/espn/1",
        "timeline": 0,
        "status": "offline",
        "is_embed": True,
        "blockable": False,
        "provider": "embed",
        "updated_at": "2025-08-31T10:33:58.827515"
    }
]


def fetch_channels():
    global cached_channels, last_fetch_time
    now = time.time()
    if cached_channels and (now - last_fetch_time < CACHE_TTL):
        return cached_channels

    try:
        req = urllib.request.Request(CHANNELS_API_URL, headers=DEFAULT_HEADERS)
        with urllib.request.urlopen(req, context=ssl_ctx, timeout=8) as resp:
            content = resp.read().decode('utf-8')
            data = json.loads(content)
            if isinstance(data, list) and len(data) > 0:
                cached_channels = data
                last_fetch_time = now
                print(f"[F1 API] Successfully refreshed {len(data)} channels from CDN.")
                return cached_channels
    except Exception as e:
        print(f"[F1 API WARN] Live channels fetch failed: {e}. Using cached/fallback data.")

    if not cached_channels:
        cached_channels = FALLBACK_CHANNELS
        last_fetch_time = now

    return cached_channels


def fetch_schedule():
    global cached_schedule, last_schedule_time
    now = time.time()
    if cached_schedule and (now - last_schedule_time < 3600):
        return cached_schedule

    try:
        req = urllib.request.Request(SCHEDULE_API_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, context=ssl_ctx, timeout=8) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            races = data.get("MRData", {}).get("RaceTable", {}).get("Races", [])
            if races:
                cached_schedule = races
                last_schedule_time = now
                print(f"[F1 SCHEDULE] Refreshed {len(races)} races for 2026 season.")
                return cached_schedule
    except Exception as e:
        print(f"[F1 SCHEDULE WARN] Jolpi API schedule fetch error: {e}")

    return cached_schedule


@app.route('/')
def index():
    return send_from_directory(STATIC_DIR, 'index.html')


@app.route('/api/channels', methods=['GET'])
def get_channels():
    force = request.args.get('force', '').lower() == 'true'
    global last_fetch_time
    if force:
        last_fetch_time = 0
    channels = fetch_channels()

    # Enhance channels with playback metadata & proxy links
    enhanced = []
    for ch in channels:
        uri = ch.get('uri', '')
        is_m3u8 = bool(re.search(r'\.m3u8(\?|$)', uri, re.IGNORECASE))
        is_embed = ch.get('is_embed', False) or ch.get('provider') == 'embed'

        title = ch.get('title', 'F1 Stream')
        quality = 'HD 720p'
        if 'UHD' in title or '4K' in title:
            quality = 'UHD 4K'
        elif 'FHD' in title or '1080p' in title:
            quality = 'FHD 1080p'
        elif '720p' in title or 'HD' in title:
            quality = 'HD 720p'

        tag = 'Sky Sports'
        if 'F1 TV' in title:
            tag = 'F1 TV'
        elif 'ESPN' in title:
            tag = 'ESPN'
        elif 'Live 1' in title or 'Practice' in title or 'Race' in title:
            tag = 'Live Event'

        # Proxy links for 100% unblocked playback
        if is_m3u8:
            playback_url = f"/api/proxy_m3u8?url={urllib.parse.quote(uri, safe='')}"
        elif is_embed:
            playback_url = f"/api/proxy_embed?url={urllib.parse.quote(uri, safe='')}"
        else:
            playback_url = uri

        enhanced.append({
            **ch,
            'is_m3u8': is_m3u8,
            'is_embed': is_embed,
            'quality_label': quality,
            'category_tag': tag,
            'direct_stream_url': playback_url
        })

    # Sort to put Clean / Working streams at the top
    enhanced.sort(key=lambda x: (x.get('status') != 'online', not x.get('is_m3u8'), x.get('id', 9999)))

    return jsonify({
        'success': True,
        'count': len(enhanced),
        'timestamp': int(time.time()),
        'channels': enhanced
    })


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Proxies live viewer statistics from stats.f1live.dpdns.org."""
    viewer_id = request.args.get('viewerId', '262f0aed-5407-400c-9509-4aab22f91bcc')
    channel_id = request.args.get('channelId', '172218')
    stats_url = f"https://stats.f1live.dpdns.org/counts?viewerId={viewer_id}&channelId={channel_id}"

    try:
        req = urllib.request.Request(stats_url, headers=DEFAULT_HEADERS)
        with urllib.request.urlopen(req, context=ssl_ctx, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return jsonify({'success': True, 'counts': data})
    except Exception as e:
        return jsonify({'success': False, 'counts': {}, 'error': str(e)})


@app.route('/api/schedule', methods=['GET'])
def get_schedule():
    races = fetch_schedule()
    return jsonify({
        'success': True,
        'season': '2026',
        'total': len(races),
        'races': races
    })


def fetch_upstream_with_retry(target_url, headers, timeout=6, max_retries=3):
    """Fetches upstream content with automatic retries for transient 502/503/504 errors."""
    last_err = None
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(target_url, headers=headers)
            with urllib.request.urlopen(req, context=ssl_ctx, timeout=timeout) as resp:
                data = resp.read()
                return resp.status, resp.headers, data
        except urllib.error.HTTPError as e:
            last_err = e
            # 404 means the rolling segment expired from the live window; do not retry
            if e.code == 404:
                raise e
            # Retry transient gateway / origin blips
            if e.code in (500, 502, 503, 504) and attempt < max_retries - 1:
                time.sleep(0.18 * (attempt + 1))
                continue
            raise e
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
            last_err = e
            if attempt < max_retries - 1:
                time.sleep(0.18 * (attempt + 1))
                continue
            raise e
    if last_err:
        raise last_err


@app.route('/api/proxy_embed', methods=['GET'])
def proxy_embed():
    """Proxies and unlocks web embed players by stripping X-Frame-Options and CSP headers."""
    target_url = request.args.get('url')
    if not target_url:
        return Response("Missing 'url' parameter", status=400)

    try:
        parsed_target = urllib.parse.urlparse(target_url)
        base_origin = f"{parsed_target.scheme}://{parsed_target.netloc}"

        custom_headers = {
            "User-Agent": DEFAULT_HEADERS["User-Agent"],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": base_origin + "/",
            "Origin": base_origin
        }

        _, _, raw_bytes = fetch_upstream_with_retry(target_url, custom_headers, timeout=6, max_retries=2)
        content = raw_bytes.decode('utf-8', errors='ignore')

        # Inject base tag for relative links
        base_tag = f'<base href="{target_url}">'
        if '<head>' in content:
            content = content.replace('<head>', f'<head>{base_tag}', 1)
        else:
            content = f'{base_tag}{content}'

        response = Response(content, mimetype='text/html')
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Cache-Control'] = 'no-cache'
        return response

    except Exception as e:
        print(f"[EMBED PROXY WARN] {target_url} -> {e}")
        return Response(f"""
        <!DOCTYPE html>
        <html>
        <head><meta http-equiv="refresh" content="0;url={target_url}"></head>
        <body style="background:#000;color:#fff;display:flex;align-items:center;justify-content:center;height:100vh;font-family:sans-serif;">
          <div>Connecting to Stream... <a href="{target_url}" target="_blank" style="color:#00d2be;">Click here if not redirected</a></div>
        </body>
        </html>
        """, mimetype='text/html')


@app.route('/api/proxy_m3u8', methods=['GET'])
def proxy_m3u8():
    """Proxies and rewrites M3U8 playlists with resilient retry and CORS bypass."""
    target_url = request.args.get('url')
    if not target_url:
        return Response("Missing 'url' parameter", status=400)

    try:
        parsed_target = urllib.parse.urlparse(target_url)

        custom_headers = {
            **DEFAULT_HEADERS,
            "Referer": "https://f1live.dpdns.org/stream" if "dpdns.org" in parsed_target.netloc else f"{parsed_target.scheme}://{parsed_target.netloc}/",
            "Origin": "https://f1live.dpdns.org" if "dpdns.org" in parsed_target.netloc else f"{parsed_target.scheme}://{parsed_target.netloc}"
        }

        status, resp_headers, raw_bytes = fetch_upstream_with_retry(target_url, custom_headers, timeout=6, max_retries=3)
        content_type = resp_headers.get('Content-Type', 'application/vnd.apple.mpegurl')

        if b'#EXTM3U' in raw_bytes:
            content_str = raw_bytes.decode('utf-8', errors='ignore')
            rewritten_lines = []

            for line in content_str.splitlines():
                trimmed = line.strip()
                if not trimmed:
                    continue

                if trimmed.startswith('#EXT-X-KEY') or trimmed.startswith('#EXT-X-MAP'):
                    def replace_key_uri(match):
                        uri_val = match.group(1)
                        full_uri = urllib.parse.urljoin(target_url, uri_val)
                        proxied = f"/api/proxy_segment?url={urllib.parse.quote(full_uri, safe='')}"
                        return f'URI="{proxied}"'
                    new_line = re.sub(r'URI=["\']([^"\']+)["\']', replace_key_uri, trimmed)
                    rewritten_lines.append(new_line)

                elif not trimmed.startswith('#'):
                    full_seg_url = urllib.parse.urljoin(target_url, trimmed)
                    if '.m3u8' in full_seg_url.lower():
                        proxied_url = f"/api/proxy_m3u8?url={urllib.parse.quote(full_seg_url, safe='')}"
                    else:
                        proxied_url = f"/api/proxy_segment?url={urllib.parse.quote(full_seg_url, safe='')}"
                    rewritten_lines.append(proxied_url)
                else:
                    rewritten_lines.append(trimmed)

            final_m3u8 = "\n".join(rewritten_lines) + "\n"
            response = Response(final_m3u8, mimetype='application/vnd.apple.mpegurl')
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            return response
        else:
            response = Response(raw_bytes, mimetype=content_type)
            response.headers['Access-Control-Allow-Origin'] = '*'
            return response

    except urllib.error.HTTPError as e:
        print(f"[M3U8 PROXY ERROR] {target_url} -> HTTP {e.code}: {e.reason}")
        return Response(f"#EXTM3U\n#EXT-X-ERROR: Upstream HTTP {e.code}\n", status=e.code if e.code in (403, 404, 502, 503) else 502, mimetype='application/vnd.apple.mpegurl')
    except Exception as e:
        print(f"[M3U8 PROXY ERROR] {target_url} -> {e}")
        return Response(f"#EXTM3U\n#EXT-X-ERROR: {e}\n", status=502, mimetype='application/vnd.apple.mpegurl')


@app.route('/api/proxy_segment', methods=['GET'])
def proxy_segment():
    """Proxies TS and M4S media segments with high-speed streaming and edge caching."""
    target_url = request.args.get('url')
    if not target_url:
        return Response("Missing 'url'", status=400)

    try:
        parsed_target = urllib.parse.urlparse(target_url)

        custom_headers = {
            **DEFAULT_HEADERS,
            "Referer": "https://f1live.dpdns.org/stream" if "dpdns.org" in parsed_target.netloc else f"{parsed_target.scheme}://{parsed_target.netloc}/",
            "Origin": "https://f1live.dpdns.org" if "dpdns.org" in parsed_target.netloc else f"{parsed_target.scheme}://{parsed_target.netloc}"
        }

        if 'Range' in request.headers:
            custom_headers['Range'] = request.headers['Range']

        status, resp_headers, data = fetch_upstream_with_retry(target_url, custom_headers, timeout=8, max_retries=3)
        c_type = resp_headers.get('Content-Type', 'video/MP2T')

        response = Response(data, status=status, mimetype=c_type)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Cache-Control'] = 'public, max-age=86400, s-maxage=86400, immutable'
        if 'Content-Range' in resp_headers:
            response.headers['Content-Range'] = resp_headers['Content-Range']
        return response

    except urllib.error.HTTPError as e:
        # If segment is expired on live edge (404), return 404 cleanly so Hls.js skips it
        if e.code == 404:
            res = Response("Segment expired from live window", status=404, mimetype='text/plain')
            res.headers['Cache-Control'] = 'no-cache, no-store'
            return res
        print(f"[SEGMENT PROXY ERROR] {target_url} -> HTTP {e.code}: {e.reason}")
        res = Response(f"Upstream HTTP {e.code}", status=e.code if e.code in (403, 404, 502, 503) else 502, mimetype='text/plain')
        res.headers['Cache-Control'] = 'no-cache, no-store'
        return res
    except Exception as e:
        print(f"[SEGMENT PROXY ERROR] {target_url} -> {e}")
        res = Response(str(e), status=502, mimetype='text/plain')
        res.headers['Cache-Control'] = 'no-cache, no-store'
        return res


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5005))
    print("=" * 60)
    print(f"  F1 LIVE CHANNELS STREAMING HUB (2026 SEASON)")
    print(f"  Live Sync from: {CHANNELS_API_URL}")
    print(f"  Player Server: http://localhost:{port}")
    print("=" * 60)
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
