import ast
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

    def test_incompatible_schema_rejects_before_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "project"
            bad_schemas = [
                ([], "objeto JSON"),
                ({"apps": [{"model": "Teacher", "fields": []}]}, "Nome do app"),
                ({"apps": [{"name": "teachers", "model": "Teacher", "fields": {}}]}, "lista fields"),
                ({"apps": [{"name": "teachers", "model": "Teacher", "fields": [
                    {"name": "delete", "type": "char"},
                ]}]}, "Campo duplicado ou reservado"),
                ({"apps": [{"name": "teachers", "model": "Teacher", "fields": [
                    {"name": "name", "type": []},
                ]}]}, "Tipo desconhecido"),
                ({"apps": [{"name": "admin", "model": "Subject", "fields": [
                    {"name": "name", "type": "char"},
                ]}]}, "nome reservado"),
            ]
            bad_fk = example()
            bad_fk["apps"][1]["fields"].append({"name": "instructor_id", "type": "integer"})
            bad_schemas.append((bad_fk, "ja e criado pela ForeignKey"))
            blank_date = example()
            blank_date["apps"][1]["fields"].append({"name": "start", "type": "date", "blank": True})
            bad_schemas.append((blank_date, "blank: true exige null: true"))
            bad_photo = example()
            bad_photo["apps"][0]["fields"][1]["upload_to"] = "../fotos"
            bad_schemas.append((bad_photo, "pasta relativa"))
            for schema, message in bad_schemas:
                with self.subTest(message=message):
                    with self.assertRaisesRegex(ValueError, message):
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
            settings_file = out / "setup/settings.py"
            original_settings = settings_file.read_bytes()
            settings_file.write_bytes(original_settings.replace(
                b"'django.contrib.staticfiles',",
                b"'django.contrib.staticfiles'  # keep the original comment",
            ))
            plans = out / "plans"
            plans.mkdir()
            (plans / "__init__.py").touch()
            (plans / "models.py").write_text(
                "from django.db import models\n\nclass Plan(models.Model):\n"
                "    title = models.CharField(max_length=80)\n",
                encoding="utf-8",
            )
            settings_file.write_bytes(settings_file.read_bytes().replace(
                b"'django.contrib.staticfiles'  #",
                b"'plans', 'django.contrib.staticfiles'  #",
                1,
            ))
            schema = example()
            schema["apps"][1]["fields"].append({"name": "plan", "type": "fk", "to": "plans.Plan"})
            baseline = {path: path.read_bytes() for path in out.rglob("*.py")}
            registered_files = {settings_file, out / "setup/urls.py"}
            plan = generate(schema, out, dry_run=True)
            self.assertTrue(registered_files.issubset(plan))
            self.assertFalse((out / "instructors").exists())
            for path, contents in baseline.items():
                self.assertEqual(path.read_bytes(), contents)

            blocked_app = out / "courses"
            blocked_app.write_text("keep", encoding="utf-8")
            with self.assertRaises(ValueError):
                generate(schema, out)
            self.assertEqual(blocked_app.read_text(encoding="utf-8"), "keep")
            self.assertFalse((out / "instructors").exists())
            self.assertFalse((out / "crud-genifsp.json").exists())
            blocked_app.unlink()

            generate(schema, out)
            for path, contents in baseline.items():
                if path not in registered_files:
                    self.assertEqual(path.read_bytes(), contents)
            tree = ast.parse(settings_file.read_bytes())
            assignment = next(node for node in tree.body if isinstance(node, ast.Assign)
                              and any(isinstance(target, ast.Name) and target.id == "INSTALLED_APPS"
                                      for target in node.targets))
            self.assertEqual(ast.literal_eval(assignment.value)[-2:], ["instructors", "courses"])
            self.assertIn(b"'django.contrib.staticfiles',  # keep the original comment", settings_file.read_bytes())
            self.assertFalse((out / "setup/crud_genifsp_registry.py").exists())
            self.assertFalse((out / "config").exists())
            self.assertTrue((out / "instructors/admin.py").is_file())
            self.assertTrue((out / "courses/admin.py").is_file())
            self.assertTrue((out / "courses/templates/courses/update.html").is_file())
            details = (out / "courses/templates/courses/details.html").read_text(encoding="utf-8")
            self.assertIn("{{ object.plan }}", details)
            self.assertNotIn("plans:details", details)
            managed = subprocess.run(
                [sys.executable, "manage.py", "check"],
                cwd=out, capture_output=True, text=True,
            )
            self.assertEqual(managed.returncode, 0, managed.stdout + managed.stderr)
            probe = """
from django.contrib import admin
from django.urls import resolve, reverse
from instructors.models import Instructor
from courses.models import Course
from plans.models import Plan

assert admin.site.is_registered(Instructor)
assert admin.site.is_registered(Course)
assert Course._meta.get_field('plan').related_model is Plan
assert reverse('instructors:instructors') == '/instructors/'
assert reverse('instructors:details', args=[7]) == '/instructors/details/7'
assert resolve('/courses/add/addrecord/').func.__name__ == 'addrecord'
assert reverse('courses:updaterecord', args=[7]) == '/courses/update/updaterecord/7'
assert reverse('admin:index') == '/admin/'
"""
            probed = subprocess.run(
                [sys.executable, "manage.py", "shell", "-c", probe],
                cwd=out, capture_output=True, text=True,
            )
            self.assertEqual(probed.returncode, 0, probed.stdout + probed.stderr)
            snapshot = {path: path.read_bytes() for path in out.rglob("*.py")}
            with self.assertRaises(ValueError):
                generate(schema, out)
            for path, contents in snapshot.items():
                self.assertEqual(path.read_bytes(), contents)

    def test_installed_package_full_crud_and_extension(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'project'
            schema = example()
            schema["apps"][1]["fields"].append({
                "name": "substitute", "type": "fk", "to": "instructors.Instructor",
                "on_delete": "SET_NULL", "blank": True, "null": True,
            })
            generate(schema, out)
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
