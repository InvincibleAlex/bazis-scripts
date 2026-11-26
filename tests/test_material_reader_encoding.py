"""Exercise the real CLI input path under a non-UTF-8 Windows pipe default."""
import ast
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


class MaterialInputEncoding(unittest.TestCase):
    def test_utf8_json_material_name_survives_windows_pipe_codepage(self):
        source = Path(__file__).resolve().parents[1] / 'tools/read_material_designations.py'
        tree = ast.parse(source.read_text(encoding='utf-8'))
        main = next(node for node in tree.body if isinstance(node, ast.If)
                    and isinstance(node.test, ast.Compare))
        program = compile(ast.Module(body=main.body, type_ignores=[]), str(source), 'exec')
        request = [{'material': 'Blat de bucătărie căntuit EGGER 26+, Stejar Casella Natur, H1385 ST40\r50144/1385',
                    'thickness_mm': 38}]
        received = []

        def read_materials(items):
            received.extend(items)
            return [{'desemnare': 'Blat_Stejar_Casella_Natur_H1385_ST40_38'}]

        payload = json.dumps(request, ensure_ascii=False).encode('utf-8')
        for codepage in ['cp1252', 'cp1250', 'utf-8']:
            with self.subTest(codepage=codepage):
                received.clear()
                stream = io.TextIOWrapper(io.BytesIO(payload), encoding=codepage)
                output = io.StringIO()
                with patch.object(sys, 'stdin', stream), patch.object(sys, 'stdout', output):
                    exec(program, {'sys': sys, 'json': json, 'read_materials': read_materials})
                self.assertEqual(received, request)
                self.assertTrue(json.loads(output.getvalue())['ok'])


if __name__ == '__main__':
    unittest.main()
