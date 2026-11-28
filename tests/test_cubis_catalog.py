import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import zipfile

SPEC = importlib.util.spec_from_file_location('read_catalog', Path(__file__).resolve().parents[1] / 'tools/cubis/read_catalog.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CatalogTests(unittest.TestCase):
    def test_growing_native_catalog_and_cell_types(self):
        main = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
        rel = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
        with TemporaryDirectory() as directory:
            file = Path(directory) / 'catalog.xlsx'
            with zipfile.ZipFile(file, 'w') as book:
                book.writestr('xl/workbook.xml', f'<workbook xmlns="{main}" xmlns:r="{rel}"><sheets><sheet name="ABS" r:id="rId9"/><sheet name="PAL" r:id="rId2"/></sheets></workbook>')
                book.writestr('xl/_rels/workbook.xml.rels', '<Relationships><Relationship Id="rId9" Target="/xl/worksheets/edges.xml"/><Relationship Id="rId2" Target="worksheets/materials.xml"/></Relationships>')
                book.writestr('xl/sharedStrings.xml', f'<sst xmlns="{main}"><si><t>SHARED_MATERIAL</t></si></sst>')
                rows = ['<row r="1"><c r="A1" t="str"><v>HEADER</v></c></row>']
                rows += [f'<row r="{i+2}"><c r="A{i+2}" t="str"><v>MAT_{i}</v></c></row>' for i in range(12350)]
                rows += ['<row r="12352"><c r="A12352" t="s"><v>0</v></c></row>', '<row r="12353"><c r="A12353" t="inlineStr"><is><t>INLINE_MATERIAL</t></is></c></row>', '<row r="12354"><c r="A12354" t="str"><v>MAT_1</v></c><c r="B12354" t="str"><v>NOT_A_MATERIAL</v></c></row>']
                book.writestr('xl/worksheets/materials.xml', f'<worksheet xmlns="{main}"><sheetData>{"".join(rows)}</sheetData></worksheet>')
                book.writestr('xl/worksheets/edges.xml', f'<worksheet xmlns="{main}"><sheetData><row r="1"><c r="A1" t="str"><v>HEADER</v></c></row><row r="2"><c r="A2" t="str"><v>EDGE</v></c></row></sheetData></worksheet>')
            result = MODULE.read_catalogs(file)
            self.assertEqual(len(result['PAL']), 12352)
            self.assertIn('MAT_12349', result['PAL'])
            self.assertIn('SHARED_MATERIAL', result['PAL'])
            self.assertIn('INLINE_MATERIAL', result['PAL'])
            self.assertEqual(result['PAL'].count('MAT_1'), 1)
            self.assertNotIn('HEADER', result['PAL'])
            self.assertNotIn('NOT_A_MATERIAL', result['PAL'])
            self.assertEqual(result['ABS'], ['EDGE'])


if __name__ == '__main__':
    unittest.main()
