import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from crud_genifsp.generator import example, generate


class GeneratorTests(unittest.TestCase):
    def test_invalid_relation_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'project'
            schema = example()
            schema['apps'][1]['fields'][2]['to'] = 'missing.Model'
            with self.assertRaises(ValueError):
                generate(schema, out)
            self.assertFalse(out.exists())

    def test_no_overwrite_and_dry_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'project'
            self.assertTrue(generate(example(), out, True))
            self.assertFalse(out.exists())
            out.mkdir()
            (out / 'mine.txt').write_text('keep')
            with self.assertRaises(ValueError):
                generate(example(), out)
            self.assertEqual((out / 'mine.txt').read_text(), 'keep')

    def test_installed_package_full_crud_and_extension(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'project'
            generate(example(), out)
            def manage(*args):
                result = subprocess.run([sys.executable, 'manage.py', *args], cwd=out, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            manage('makemigrations', '--noinput')
            manage('migrate', '--noinput')
            self.assertTrue((out / 'courses/migrations/0001_initial.py').exists())
            original = (out / 'instructors/models.py').read_bytes()
            generate({'project': 'config', 'apps': [
                {'name': 'students', 'model': 'Student', 'fields': [
                    {'name': 'name', 'type': 'char'}, {'name': 'email', 'type': 'email', 'unique': True},
                    {'name': 'courses', 'type': 'm2m', 'to': 'courses.Course'}]},
                {'name': 'enrollments', 'model': 'Enrollment', 'fields': [
                    {'name': 'student', 'type': 'fk', 'to': 'students.Student'},
                    {'name': 'course', 'type': 'fk', 'to': 'courses.Course'},
                    {'name': 'start', 'type': 'date'}, {'name': 'fee', 'type': 'decimal', 'max_digits': 8, 'decimal_places': 2},
                    {'name': 'active', 'type': 'boolean', 'default': True}]}]}, out)
            self.assertEqual((out / 'instructors/models.py').read_bytes(), original)
            manage('makemigrations', '--noinput')
            manage('migrate', '--noinput')
            manage('check')
            manage('makemigrations', '--check', '--dry-run')
            probe = Path(__file__).with_name('web_probe.py').read_text(encoding='utf-8')
            result = subprocess.run([sys.executable, '-c', probe], cwd=out, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('CRUD E2E OK', result.stdout)


if __name__ == '__main__':
    unittest.main()
