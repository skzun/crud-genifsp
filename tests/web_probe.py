"""Executed in a fresh generated project by test_generator.py."""
import io
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
import django
django.setup()
from django.test import Client
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from instructors.models import Instructor
from courses.models import Course
from students.models import Student
from enrollments.models import Enrollment

client = Client(enforce_csrf_checks=True)
def get(path):
    response = client.get(path)
    assert response.status_code == 200, (path, response.status_code)
    return response
def post(path, data):
    get(path)
    data['csrfmiddlewaretoken'] = client.cookies['csrftoken'].value
    return client.post(path, data)
def image():
    buffer = io.BytesIO()
    Image.new('RGB', (4, 4), 'green').save(buffer, 'PNG')
    return SimpleUploadedFile('photo.png', buffer.getvalue(), content_type='image/png')

get('/')
for app in ['instructors', 'courses', 'students', 'enrollments']:
    get('/' + app + '/')
    get('/' + app + '/new/')
assert client.post('/instructors/new/', {'name': 'No token'}).status_code == 403
assert post('/instructors/new/', {'name': 'Invalid', 'photo': SimpleUploadedFile('fake.png', b'bad')}).status_code == 200
assert not Instructor.objects.exists()
assert post('/instructors/new/', {'name': 'Ada', 'photo': image()}).status_code == 302
instructor = Instructor.objects.get()
assert os.path.isfile(instructor.photo.path)
get(f'/instructors/{instructor.pk}/')
assert post(f'/instructors/{instructor.pk}/edit/', {'name': 'Ada Lovelace'}).status_code == 302
instructor.refresh_from_db()
assert instructor.name == 'Ada Lovelace'
assert post('/courses/new/', {'name': 'Django', 'description': 'Forms', 'instructor': 99999}).status_code == 200
assert not Course.objects.exists()
assert post('/courses/new/', {'name': 'Django', 'description': 'Forms', 'instructor': instructor.pk}).status_code == 302
course = Course.objects.get()
assert f'/instructors/{instructor.pk}/'.encode() in get(f'/courses/{course.pk}/').content
get(f'/instructors/{instructor.pk}/delete/')
assert Instructor.objects.count() == 1
assert post(f'/instructors/{instructor.pk}/delete/', {}).status_code == 409
assert post(f'/courses/{course.pk}/edit/', {'name': 'Python', 'description': '<script>alert(1)</script>', 'instructor': instructor.pk}).status_code == 302
assert b'&lt;script&gt;' in get(f'/courses/{course.pk}/').content
assert post('/students/new/', {'name': 'Lucas', 'email': 'lucas@example.com', 'courses': [course.pk]}).status_code == 302
student = Student.objects.get()
assert student.courses.get() == course
get(f'/students/{student.pk}/')
assert post('/enrollments/new/', {'student': student.pk, 'course': course.pk, 'start': '2026-11-23', 'fee': '99.90', 'active': 'on'}).status_code == 302
enrollment = Enrollment.objects.get()
get(f'/enrollments/{enrollment.pk}/')
assert b'value="2026-11-23"' in get(f'/enrollments/{enrollment.pk}/edit/').content
assert post(f'/enrollments/{enrollment.pk}/delete/', {}).status_code == 302
assert post(f'/students/{student.pk}/delete/', {}).status_code == 302
assert post(f'/courses/{course.pk}/delete/', {}).status_code == 302
assert post(f'/instructors/{instructor.pk}/delete/', {}).status_code == 302
assert not Instructor.objects.exists() and not Course.objects.exists()
assert client.get('/courses/99999/').status_code == 404
print('CRUD E2E OK: upload, validation, CSRF, escaped HTML, relations, protected deletion, M2M, extension, delete')
