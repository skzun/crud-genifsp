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

    def test_integrates_into_existing_project_without_replacing_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            started = subprocess.run(
                [sys.executable, "-m", "django", "startproject", "setup", "."],
                cwd=out, capture_output=True, text=True,
            )
            self.assertEqual(started.returncode, 0, started.stdout + started.stderr)
            baseline = {path: path.read_bytes() for path in out.rglob("*.py")}
            hooks = {out / "setup/settings.py", out / "setup/urls.py"}
            plan = generate(example(), out, dry_run=True)
            self.assertTrue(hooks.issubset(plan))
            self.assertFalse((out / "instructors").exists())
            for path, contents in baseline.items():
                self.assertEqual(path.read_bytes(), contents)

            # A pre-existing file in a generated directory must survive a failed attempt.
            blocked_dir = out / "crud_genifsp_templates"
            blocked_dir.write_text("keep", encoding="utf-8")
            with self.assertRaises(OSError):
                generate(example(), out)
            self.assertEqual(blocked_dir.read_text(encoding="utf-8"), "keep")
            self.assertFalse((out / "crud_genifsp_static").exists())
            self.assertFalse((out / "crud-genifsp.json").exists())
            blocked_dir.unlink()

            generate(example(), out)
            for path, contents in baseline.items():
                if path in hooks:
                    self.assertTrue(path.read_bytes().startswith(contents))
                    self.assertIn(b".crud_genifsp_registry", path.read_bytes()[len(contents):])
                else:
                    self.assertEqual(path.read_bytes(), contents)
            self.assertFalse((out / "config").exists())
            self.assertTrue((out / "instructors/models.py").is_file())
            self.assertTrue((out / "courses/urls.py").is_file())
            check = subprocess.run(
                [sys.executable, "manage.py", "check"],
                cwd=out, capture_output=True, text=True,
            )
            self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
            snapshot = {path: path.read_bytes() for path in out.rglob("*.py")}
            with self.assertRaises(ValueError):
                generate(example(), out)
            for path, contents in snapshot.items():
                self.assertEqual(path.read_bytes(), contents)

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
