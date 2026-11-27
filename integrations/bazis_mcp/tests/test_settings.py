import json
from pathlib import Path
import tempfile
import unittest

from bazis_mcp.settings import SettingsStore, SettingsError, scan, serialize_value
from bazis_mcp.transport import BridgeClient, atomic_json


SAMPLE = ('\ufeff<?xml version="1.0" encoding="UTF-8"?>\r\n'
          '<Settings custom="unchanged">\r\n'
          '  <!-- keep this comment and every byte outside explicit edits -->\r\n'
          '  <Profiles><Profile><Name>Test profile</Name><Enabled>Y</Enabled>'
          '<Scale>.125</Scale><Mode>3</Mode><Empty/><Caption>A &amp; B</Caption>'
          '<Password>private</Password><AutoStartScript>C:/script.js</AutoStartScript>'
          '<123numeric><On>N</On></123numeric><Русский>Y</Русский>'
          '<Legacy>A\x0bB</Legacy></Profile>'
          '<Profile><Name>Second</Name><Enabled>N</Enabled></Profile></Profiles>\r\n'
          '</Settings>\r\n').encode('utf-8')


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.root = self.home / 'Bazis'
        self.root.mkdir()
        self.config = self.home / 'private' / 'config.json'
        atomic_json(self.config, {'token': 'test' * 12, 'bridge_dir': str(self.home / 'runtime'), 'allow_edits': True})
        self.path = self.root / 'Settings.xml'
        self.path.write_bytes(SAMPLE)
        self.store = SettingsStore(BridgeClient(self.config), self.root, processes=lambda: [])

    def tearDown(self):
        self.temp.cleanup()

    def stage(self, name='Enabled', value=False):
        current = self.store.read('Settings.xml', 'Test profile ' + name)
        self.assertEqual(current['total'], 1)
        item = current['items'][0]
        return self.store.stage('Settings.xml', current['revision'],
                                [{'setting_id': item['setting_id'], 'expected_value': item['value'], 'value': value}])

    def test_catalog_search_paging_repeated_nodes_and_legacy_markup(self):
        catalog = self.store.catalog()
        self.assertEqual(catalog['items'][0]['status'], 'readable')
        rows = self.store.read('Settings.xml', 'Enabled', limit=1)
        self.assertEqual(rows['total'], 2)
        self.assertEqual(rows['next_offset'], 1)
        self.assertEqual(rows['items'][0]['context'], ['Test profile'])
        second = self.store.read('Settings.xml', 'Enabled', offset=1)['items'][0]
        self.assertEqual(second['context'], ['Second'])
        self.assertNotEqual(second['setting_id'], rows['items'][0]['setting_id'])
        self.assertEqual(self.store.read('Settings.xml', 'Русский')['items'][0]['value'], 'Y')
        self.assertEqual(self.store.read('Settings.xml', '123numeric')['items'][0]['value'], 'N')
        self.assertFalse(self.store.read('Settings.xml', 'Empty')['items'][0]['can_stage'])

    def test_stage_only_changes_requested_bytes_and_does_not_apply(self):
        staged = self.stage()
        self.assertFalse(staged['applied_to_bazis'])
        self.assertEqual(self.path.read_bytes(), SAMPLE)
        self.assertEqual(Path(staged['preview_file']).read_bytes(), SAMPLE.replace(b'<Enabled>Y</Enabled>', b'<Enabled>N</Enabled>'))
        self.assertEqual(self.store.result(staged['stage_id'])['current_matches'], 'before')

    def test_apply_and_exact_restore_and_no_replay(self):
        staged = self.stage()
        applied = self.store.apply(staged['stage_id'])
        self.assertEqual(applied['state'], 'applied')
        self.assertEqual(Path(applied['backup_file']).read_bytes(), SAMPLE)
        self.assertEqual(self.store.result(staged['stage_id'])['current_matches'], 'after')
        with self.assertRaisesRegex(SettingsError, 'Do not replay'):
            self.store.apply(staged['stage_id'])
        self.store.apply(staged['stage_id'], restore=True)
        self.assertEqual(self.path.read_bytes(), SAMPLE)

    def test_running_bazis_blocks_apply_without_changing_any_file(self):
        staged = self.stage()
        self.store.processes = lambda: [{'name': 'Bazis.exe', 'pid': 123}]
        with self.assertRaisesRegex(SettingsError, 'BAZIS_RUNNING'):
            self.store.apply(staged['stage_id'])
        self.assertEqual(self.path.read_bytes(), SAMPLE)
        self.assertEqual(self.store.result(staged['stage_id'])['state'], 'staged')

    def test_source_changes_block_stage_apply_and_restore(self):
        current = self.store.read('Settings.xml', 'Test profile Enabled')
        item = current['items'][0]
        self.path.write_bytes(SAMPLE + b' ')
        with self.assertRaisesRegex(SettingsError, 'SETTINGS_CHANGED'):
            self.store.stage('Settings.xml', current['revision'], [{'setting_id': item['setting_id'], 'expected_value': 'Y', 'value': False}])
        self.path.write_bytes(SAMPLE)
        staged = self.stage()
        self.path.write_bytes(SAMPLE + b' ')
        with self.assertRaisesRegex(SettingsError, 'SETTINGS_CHANGED'):
            self.store.apply(staged['stage_id'])
        self.path.write_bytes(SAMPLE)
        self.store.apply(staged['stage_id'])
        self.path.write_bytes(self.path.read_bytes() + b' ')
        with self.assertRaisesRegex(SettingsError, 'SETTINGS_CHANGED'):
            self.store.apply(staged['stage_id'], restore=True)

    def test_sensitive_and_execution_fields_cannot_be_staged(self):
        result = self.store.read('Settings.xml')
        serialized = json.dumps(result)
        self.assertNotIn('private', serialized)
        for name in ('Password', 'AutoStartScript'):
            row = self.store.read('Settings.xml', name)['items'][0]
            self.assertFalse(row['can_stage'])
            with self.assertRaisesRegex(SettingsError, 'dedicated adapter'):
                self.store.stage('Settings.xml', result['revision'], [{'setting_id': row['setting_id'], 'expected_value': row['value'], 'value': 'test'}])

    def test_paths_duplicates_wrong_expected_value_and_disabled_edits(self):
        with self.assertRaises(SettingsError):
            self.store.read('../config.json')
        with self.assertRaises(SettingsError):
            self.store.result('../x')
        current = self.store.read('Settings.xml', 'Test profile Enabled')
        change = {'setting_id': current['items'][0]['setting_id'], 'expected_value': 'wrong', 'value': False}
        with self.assertRaisesRegex(SettingsError, 'mismatch'):
            self.store.stage('Settings.xml', current['revision'], [change])
        change['expected_value'] = 'Y'
        with self.assertRaisesRegex(SettingsError, 'Duplicate'):
            self.store.stage('Settings.xml', current['revision'], [change, change])
        atomic_json(self.config, {'token': 'test' * 12, 'bridge_dir': 'unused', 'allow_edits': False})
        with self.assertRaisesRegex(SettingsError, 'disabled'):
            self.stage()

    def test_text_escaping_and_numeric_semantics(self):
        staged = self.stage('Caption', '<new> & old\rname')
        preview = Path(staged['preview_file']).read_bytes()
        self.assertIn(b'&lt;new&gt; &amp; old&#13;name', preview)
        self.assertEqual(serialize_value(1.0, '3'), '1')
        for value in (True, 'NaN', 'Infinity', '1e999', 1.5):
            with self.assertRaises(SettingsError):
                serialize_value(value, '3')
        with self.assertRaises(SettingsError):
            serialize_value('false', 'Y')
        # 0/1 remain numeric; no guess about enum vs flag.
        self.assertEqual(serialize_value(0, '1'), '0')

    def test_tampered_preview_and_root_mismatch_block_apply(self):
        staged = self.stage()
        preview = Path(staged['preview_file'])
        preview.write_bytes(preview.read_bytes() + b' ')
        with self.assertRaisesRegex(SettingsError, 'integrity'):
            self.store.apply(staged['stage_id'])
        other = self.home / 'Other'
        other.mkdir()
        store = SettingsStore(self.store.client, other, processes=lambda: [])
        with self.assertRaisesRegex(SettingsError, 'another configuration'):
            store.result(staged['stage_id'])

    def test_unsupported_binary_and_unsafe_xml_are_explicit(self):
        (self.root / 'MasterBox.xml').write_bytes(b'\x01\0\0\xffBINARY')
        item = next(i for i in self.store.catalog()['items'] if i['file_id'] == 'MasterBox.xml')
        self.assertEqual(item['status'], 'unsupported')
        for source in (b'<R><A></R>', b'<R>&bad;</R>', b'<!DOCTYPE R [<!ENTITY x SYSTEM "file:///x">]><R/>', b'<R><![CDATA[x]]></R>'):
            with self.assertRaises(SettingsError):
                nodes = scan(source)
                # Entity decoding occurs only on read, with no expansion.
                for n in nodes:
                    self.store._row(n)

    def test_lock_prevents_simultaneous_writers_and_unknown_outcomes_inspectable(self):
        staged = self.stage()
        import hashlib
        lock = self.store._workspace() / (hashlib.sha256(str(self.path.resolve()).encode()).hexdigest() + '.lock')
        lock.write_text('busy')
        with self.assertRaisesRegex(SettingsError, 'Another settings operation'):
            self.store.apply(staged['stage_id'])
        self.assertEqual(self.path.read_bytes(), SAMPLE)
        lock.unlink()
        # Simulate crash after atomic replace, before manifest marked complete.
        self.path.write_bytes(Path(staged['preview_file']).read_bytes())
        with self.assertRaisesRegex(SettingsError, 'SETTINGS_CHANGED'):
            self.store.apply(staged['stage_id'])
        result = self.store.result(staged['stage_id'])
        self.assertEqual((result['state'], result['current_matches']), ('staged', 'after'))


if __name__ == '__main__':
    unittest.main()
