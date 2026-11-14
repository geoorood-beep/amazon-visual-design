#!/usr/bin/env python3
"""Pinned official Image API client; Python standard library only."""
import argparse
import base64
import datetime
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import sys
import urllib.error
import urllib.request
import uuid

MODEL = 'gpt-image-2.5-sunburst-2026-09-08'
BASE = 'https://api.openai.com/v1'
KEY_FILE = Path.home() / '.config/amazon-visual/openai_api_key'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def credential():
    if KEY_FILE.exists():
        if KEY_FILE.is_symlink() or KEY_FILE.stat().st_mode & 0o077:
            raise ValueError('专用密钥文件必须为普通文件且权限为 600')
        value = KEY_FILE.read_text().strip()
    else:
        value = os.environ.get('OPENAI_API_KEY', '').strip()
    if not value or any(c.isspace() for c in value):
        raise ValueError('缺少有效凭据，请在本机终端运行 configure')
    return value


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request(route, key, body=None, content_type='application/json'):
    req = urllib.request.Request(BASE + route, data=body, headers={
        'Authorization': 'Bearer ' + key, 'Content-Type': content_type})
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=300) as response:
            return json.load(response), response.headers.get('x-request-id')
    except urllib.error.HTTPError as exc:
        # Do not expose server messages: they can echo credentials or prompts.
        reasons = {400: '请求参数被拒绝', 401: '官方 API 认证失败',
                   403: '权限或访问受限', 404: '固定模型或接口不可用',
                   429: '额度不足或触发限流'}
        raise RuntimeError('HTTP %s: %s; request_id=%s; 未重试、未切换模型' % (
            exc.code, reasons.get(exc.code, '服务错误，执行结果可能不确定'),
            exc.headers.get('x-request-id', 'UNKNOWN'))) from None
    except (urllib.error.URLError, TimeoutError):
        raise RuntimeError('网络失败/超时；执行结果可能不确定，未自动重试') from None


def validate_size(size):
    if not re.fullmatch(r'[1-9]\d*x[1-9]\d*', size):
        raise ValueError('size 必须为 WIDTHxHEIGHT')
    w, h = map(int, size.split('x'))
    if w % 16 or h % 16 or max(w, h) > 3840 or max(w, h) > 3 * min(w, h) or not 655360 <= w*h <= 8294400:
        raise ValueError('API 尺寸：边长为16倍数，≤3840，比例≤3:1，总像素655360至8294400')
    return w, h


def multipart(fields, images):
    boundary = 'image25-' + uuid.uuid4().hex
    parts, sources = [], []
    for name, value in fields.items():
        parts.append(('--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n%s\r\n' % (boundary, name, value)).encode())
    for i, path in enumerate(images):
        path = Path(path).resolve()
        raw = path.read_bytes()
        if not raw or len(raw) >= 50 * 1024 * 1024:
            raise ValueError('参考图为空或超过本入口50MB限制')
        if raw.startswith(b'\x89PNG\r\n\x1a\n'):
            ext, mime = 'png', 'image/png'
        elif raw.startswith(b'\xff\xd8\xff'):
            ext, mime = 'jpg', 'image/jpeg'
        elif raw[:4] == b'RIFF' and raw[8:12] == b'WEBP':
            ext, mime = 'webp', 'image/webp'
        else:
            raise ValueError('参考图必须为 PNG/JPEG/WebP')
        parts.append(('--%s\r\nContent-Disposition: form-data; name="image[]"; filename="reference_%s.%s"\r\nContent-Type: %s\r\n\r\n' % (boundary, i, ext, mime)).encode() + raw + b'\r\n')
        sources.append({'path': str(path), 'sha256': digest(raw)})
    parts.append(('--%s--\r\n' % boundary).encode())
    return b''.join(parts), 'multipart/form-data; boundary=' + boundary, sources


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('configure', help='本机终端隐藏输入密钥，保存到权限600的项目专用配置')
    commands.add_parser('check', help='只读检查固定模型访问，不生成图片')
    for name in ('generate', 'edit'):
        p = commands.add_parser(name)
        p.add_argument('--prompt-file', type=Path, required=True)
        p.add_argument('--output-dir', type=Path, required=True, help='必须为不存在的新目录')
        p.add_argument('--size', default='1024x1024')
        p.add_argument('--quality', choices=['low', 'medium', 'high', 'xhigh', 'max', 'auto'], default='high')
        if name == 'edit':
            p.add_argument('--image', action='append', required=True)
    args = parser.parse_args()
    if args.command == 'configure':
        if not sys.stdin.isatty():
            raise ValueError('configure 只能在用户本机交互终端运行')
        value = getpass.getpass('OpenAI 官方 API Key（隐藏输入）: ').strip()
        if not value or any(c.isspace() for c in value):
            raise ValueError('密钥为空或含空白，未保存')
        KEY_FILE.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if KEY_FILE.is_symlink():
            raise ValueError('拒绝符号链接')
        fd = os.open(KEY_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w') as f:
            f.write(value + '\n')
        print('密钥已保存到项目外专用配置；尚未验证权限。请运行 check。')
        return
    key = credential()
    if args.command == 'check':
        data, rid = request('/models/' + MODEL, key)
        if data.get('id') != MODEL:
            raise ValueError('返回模型与固定快照不一致')
        print(json.dumps({'status': 'MODEL_ACCESS_OK', 'model': MODEL, 'request_id': rid,
                          'generation_verified': False}, ensure_ascii=False))
        return
    expected = validate_size(args.size)
    prompt = args.prompt_file.read_text().strip()
    if not prompt:
        raise ValueError('提示词不能为空')
    fields = dict(model=MODEL, prompt=prompt, n=1, size=args.size,
                  quality=args.quality, output_format='png')
    route = '/images/generations'
    sources = []
    if args.command == 'edit':
        if len(args.image) > 16:
            raise ValueError('本入口最多16张参考图')
        body, content_type, sources = multipart(fields, args.image)
        route = '/images/edits'
    else:
        body, content_type = json.dumps(fields).encode(), 'application/json'
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    manifest = dict(status='REQUEST_PREPARED', requested_model=MODEL, endpoint=BASE+route,
                    parameters={k:v for k,v in fields.items() if k != 'prompt'},
                    prompt_sha256=digest(prompt.encode()), inputs=sources,
                    utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), qa='NOT_REVIEWED')
    def log():
        (output/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    (output/'prompt.txt').write_text(prompt)
    log()
    try:
        data, rid = request(route, key, body, content_type)
        manifest.update(request_id=rid, response_model=data.get('model', 'UNKNOWN'), usage=data.get('usage'))
        if data.get('model') and data['model'] not in (MODEL, 'gpt-image-2.5-sunburst'):
            raise ValueError('响应返回不同模型，拒绝作为固定模型成品')
        raw = base64.b64decode(data['data'][0]['b64_json'], validate=True)
        if len(raw) < 33 or raw[:8] != b'\x89PNG\r\n\x1a\n' or raw[12:16] != b'IHDR':
            raise ValueError('响应不是有效PNG头；拒绝保存为候选图片')
        actual = struct.unpack('>II', raw[16:24])
        image_path = output/'candidate.png'
        image_path.write_bytes(raw)
        manifest.update(output=str(image_path), output_sha256=digest(raw), actual_size=list(actual),
                        status='CANDIDATE_SAVED' if actual == expected else 'SIZE_MISMATCH')
        if actual != expected:
            raise ValueError('返回尺寸不同，保留原始候选，禁止拉伸修正')
    except Exception as exc:
        manifest.update(status='BLOCKED', error=str(exc).replace(key, '[REDACTED]'))
        log()
        raise
    log()
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        # All HTTP response bodies intentionally excluded above.
        print(str(exc), file=sys.stderr)
        sys.exit(1)
