import base64
import contextlib
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.error
import image25 as m


class ClientTests(unittest.TestCase):
    def run_job(self, command='generate', failure=None, actual=(1024, 1024)):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prompt = root/'prompt.txt'
            prompt.write_text('Test prompt')
            reference = root/'reference.png'
            # Header fixture only: transport tests, not a generated image.
            png = b'\x89PNG\r\n\x1a\n' + struct.pack('>I', 13) + b'IHDR' + struct.pack('>II', *actual) + b'\x08\x02\x00\x00\x00' + b'0000'
            reference.write_bytes(png)
            args = ['image25', command, '--prompt-file', str(prompt), '--output-dir', str(root/'out')]
            if command == 'edit':
                args += ['--image', str(reference)]
            response = {'data': [{'b64_json': base64.b64encode(png).decode()}]}
            with patch.object(sys, 'argv', args), patch.object(m, 'credential', return_value='secret-test'), patch.object(m, 'request', return_value=(response, 'req-test'), side_effect=failure) as call, contextlib.redirect_stdout(io.StringIO()):
                if failure or actual != (1024, 1024):
                    with self.assertRaises((RuntimeError, ValueError)):
                        m.main()
                else:
                    m.main()
            log = json.loads((root/'out/manifest.json').read_text())
            self.assertNotIn('secret-test', json.dumps(log))
            self.assertEqual(call.call_count, 1)
            self.assertEqual(log['requested_model'], m.MODEL)
            if failure:
                self.assertEqual(log['status'], 'BLOCKED')
                self.assertFalse((root/'out/candidate.png').exists())
            elif actual != (1024, 1024):
                self.assertEqual(log['status'], 'BLOCKED')
                self.assertEqual(log['actual_size'], list(actual))
            else:
                self.assertEqual(log['status'], 'CANDIDATE_SAVED')
                self.assertEqual(log['qa'], 'NOT_REVIEWED')
                self.assertEqual(log['response_model'], 'UNKNOWN')
                self.assertEqual((root/'out/candidate.png').read_bytes(), png)
            route, _, body, content_type = call.call_args.args
            if command == 'generate':
                self.assertEqual(route, '/images/generations')
                self.assertEqual(json.loads(body)['model'], m.MODEL)
            else:
                self.assertEqual(route, '/images/edits')
                self.assertIn(b'name="image[]"', body)
                self.assertIn(png, body)
                self.assertIn(m.MODEL.encode(), body)
                self.assertIn('multipart/form-data', content_type)

    def test_generate(self): self.run_job()
    def test_edit(self): self.run_job('edit')
    def test_failure_no_fallback(self): self.run_job(failure=RuntimeError('test auth failure'))
    def test_wrong_dimensions_blocked(self): self.run_job(actual=(1008, 1024))

    def test_sizes(self):
        for size in ['2000x2000', '1600x2000', '1952x800', '1280x960']:
            m.validate_size(size)
        for size in ['1464x600', '600x450', '0x0', '99999x99999', 'auto']:
            with self.assertRaises(ValueError): m.validate_size(size)

    def test_401_does_not_echo_key_or_retry(self):
        error = urllib.error.HTTPError(m.BASE, 401, 'secret-test', {}, io.BytesIO(b'secret-test'))
        with patch.object(m.urllib.request, 'build_opener') as opener:
            opener.return_value.open.side_effect = error
            with self.assertRaises(RuntimeError) as caught:
                m.request('/models/'+m.MODEL, 'secret-test')
            self.assertNotIn('secret-test', str(caught.exception))
            self.assertIn('401', str(caught.exception))
            self.assertEqual(opener.return_value.open.call_count, 1)

    def test_reject_redirect(self):
        self.assertIsNone(m.NoRedirect().redirect_request(None,None,302,'',{},'https://example.com'))


if __name__ == '__main__': unittest.main()
