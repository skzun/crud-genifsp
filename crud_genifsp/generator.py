"""Generate ordinary Django sources from a validated JSON description."""
import ast
import importlib.util
import json
import keyword
from pathlib import Path
import secrets


def example():
    return {"project": "config", "apps": [
        {"name": "instructors", "model": "Instructor", "fields": [
            {"name": "name", "type": "char", "max_length": 150},
            {"name": "photo", "type": "image", "upload_to": "instructors/"}]},
        {"name": "courses", "model": "Course", "fields": [
            {"name": "name", "type": "char", "max_length": 150},
            {"name": "description", "type": "text"},
            {"name": "instructor", "type": "fk", "to": "instructors.Instructor", "on_delete": "PROTECT"}]}]}


TYPES = {"char": "CharField", "text": "TextField", "image": "ImageField", "file": "FileField",
         "integer": "IntegerField", "positive_integer": "PositiveIntegerField", "decimal": "DecimalField",
         "float": "FloatField", "boolean": "BooleanField", "date": "DateField", "datetime": "DateTimeField",
         "email": "EmailField", "url": "URLField", "fk": "ForeignKey", "m2m": "ManyToManyField"}
OPTIONS = {"max_length", "blank", "null", "default", "unique", "upload_to", "max_digits", "decimal_places", "choices", "verbose_name", "help_text", "related_name"}


def identifier(value):
    if not isinstance(value, str) or not value.isidentifier() or keyword.iskeyword(value) or value.startswith("_"):
        raise ValueError(f"Identificador invalido: {value!r}")
    return value


def validate(schema, previous):
    project = identifier(schema.get("project", "config"))
    if previous and project != previous["project"]:
        raise ValueError("O projeto deve manter o mesmo nome.")
    apps = schema.get("apps")
    if not isinstance(apps, list) or not apps:
        raise ValueError("apps deve ser uma lista nao vazia.")
    known = {a["name"]: a for a in previous.get("apps", [])}
    for app in apps:
        name, model = identifier(app["name"]), identifier(app["model"])
        if name in known or name in {project, "django", "static", "media", "templates"} or importlib.util.find_spec(name):
            raise ValueError(f"App existente ou nome reservado: {name}. Use outro app; edite models.py para alterar existentes.")
        if model in {"Meta", "objects", "DoesNotExist", "MultipleObjectsReturned"}:
            raise ValueError(f"Nome de modelo reservado: {model}")
        known[name] = app
    for app in apps:
        seen = {"id", "pk", "objects"}
        if not app.get("fields"):
            raise ValueError("Cada app precisa de fields.")
        for f in app["fields"]:
            name = identifier(f["name"])
            if name in seen or "__" in name or name.endswith("_"):
                raise ValueError(f"Campo duplicado ou reservado: {name}")
            seen.add(name)
            kind = f.get("type")
            if kind not in TYPES or set(f) - OPTIONS - {"name", "type", "to", "on_delete"}:
                raise ValueError(f"Tipo ou opcao desconhecida no campo {name}")
            if kind in {"fk", "m2m"}:
                target = f.get("to", "").split(".")
                if len(target) != 2 or target[0] not in known or target[1] != known[target[0]]["model"]:
                    raise ValueError(f"Relacao inexistente: {f.get('to')}")
                if f.get("on_delete", "PROTECT") not in {"CASCADE", "PROTECT", "SET_NULL", "RESTRICT"}:
                    raise ValueError("on_delete invalido")
                if f.get("on_delete") == "SET_NULL" and not f.get("null"):
                    raise ValueError("SET_NULL exige null: true")
            if kind == "decimal" and not (isinstance(f.get("max_digits"), int) and isinstance(f.get("decimal_places"), int) and 0 <= f["decimal_places"] < f["max_digits"]):
                raise ValueError("decimal exige max_digits > decimal_places >= 0")
            if "max_length" in f and (type(f["max_length"]) is not int or f["max_length"] < 1):
                raise ValueError("max_length deve ser inteiro positivo")
            for option in {"blank", "null", "unique"} & f.keys():
                if type(f[option]) is not bool:
                    raise ValueError(f"{option} deve ser booleano")
    return project, apps


def field_code(f):
    kind = f["type"]
    opts = {k: v for k, v in f.items() if k in OPTIONS}
    if kind == "char":
        opts.setdefault("max_length", 150)
    if kind in {"file", "image"}:
        opts.setdefault("upload_to", "uploads/")
    args = []
    if kind in {"fk", "m2m"}:
        args.append(repr(f["to"]))
    if kind == "fk":
        args.append("on_delete=models." + f.get("on_delete", "PROTECT"))
    args.extend(f"{k}={v!r}" for k, v in opts.items())
    return f"    {f['name']} = models.{TYPES[kind]}({', '.join(args)})"


STYLE = """*{box-sizing:border-box}body{font:16px system-ui;background:#f3f5fa;color:#15243a;margin:0}header{background:#15243a;padding:20px;color:white}nav a{color:white;margin-right:20px}main{max-width:1000px;margin:32px auto;padding:28px;background:white;border-radius:12px}a{color:#174eb8}table{width:100%;border-collapse:collapse}td,th{padding:12px;text-align:left;border-bottom:1px solid #ddd}input,textarea,select{display:block;width:100%;padding:10px;margin:8px 0 18px}input[type=checkbox]{width:auto}button,.button{display:inline-block;background:#174eb8;color:white;padding:10px 18px;border:0;border-radius:6px;text-decoration:none}img{max-width:240px;height:auto}.errorlist,.error{color:#b51d32}.actions a{margin-right:12px}@media(max-width:700px){main{margin:12px;padding:16px}table{display:block;overflow:auto}}"""


def existing_project(output):
    """Recognize the standard startproject layout used in the class."""
    manage = output / "manage.py"
    if not manage.is_file():
        raise ValueError("Destino nao vazio e sem manage.py de um projeto Django.")
    modules = {
        node.args[1].value
        for node in ast.walk(ast.parse(manage.read_text(encoding="utf-8-sig")))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "setdefault"
        and len(node.args) == 2
        and isinstance(node.args[0], ast.Constant)
        and node.args[0].value == "DJANGO_SETTINGS_MODULE"
        and isinstance(node.args[1], ast.Constant)
        and isinstance(node.args[1].value, str)
    }
    if len(modules) != 1:
        raise ValueError("Nao foi possivel detectar o DJANGO_SETTINGS_MODULE.")
    project, sep, module = modules.pop().partition(".")
    if not sep or module != "settings":
        raise ValueError("Esperado o layout Django <projeto>.settings.")
    identifier(project)
    for filename in ("settings.py", "urls.py"):
        if not (output / project / filename).is_file():
            raise ValueError(f"Arquivo de integracao nao encontrado: {project}/{filename}")
    return project


def generate(schema, output, dry_run=False):
    output = Path(output).resolve()
    manifest = output / "crud-genifsp.json"
    previous = json.loads(manifest.read_text(encoding="utf-8")) if manifest.exists() else {}
    integrating = not previous and output.exists() and any(output.iterdir())
    if integrating:
        schema = {**schema, "project": existing_project(output)}
    integrated = integrating or previous.get("integrated", False)
    if integrated and previous:
        schema = {**schema, "project": previous["project"]}
    project, apps = validate(schema, previous)
    all_apps = previous.get("apps", []) + apps
    legacy_templates = bool(previous) and not integrated and (output / "templates/base.html").exists() and not (output / "templates/crud_genifsp/base.html").exists()
    base_template = "base.html" if legacy_templates else "crud_genifsp/base.html"
    nav_template = "generated_nav.html" if legacy_templates else "crud_genifsp/generated_nav.html"
    files = {}
    def put(path, content):
        files[output / path] = content
    if not previous and not integrating:
        put("manage.py", f"import os, sys\nos.environ.setdefault('DJANGO_SETTINGS_MODULE', '{project}.settings')\nfrom django.core.management import execute_from_command_line\nexecute_from_command_line(sys.argv)\n")
        put(f"{project}/__init__.py", "")
        put(f"{project}/settings.py", f'''from pathlib import Path
import os
from .generated import GENERATED_APPS
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', {secrets.token_urlsafe(48)!r})
DEBUG = os.environ.get('DJANGO_DEBUG', '1') == '1'
ALLOWED_HOSTS = ['127.0.0.1', 'localhost', 'testserver']
INSTALLED_APPS = ['django.contrib.contenttypes', 'django.contrib.auth', 'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles'] + GENERATED_APPS
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware', 'django.middleware.common.CommonMiddleware', 'django.middleware.csrf.CsrfViewMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware', 'django.contrib.messages.middleware.MessageMiddleware', 'django.middleware.clickjacking.XFrameOptionsMiddleware']
ROOT_URLCONF = '{project}.urls'
TEMPLATES = [{{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [BASE_DIR / 'templates'], 'APP_DIRS': True, 'OPTIONS': {{'context_processors': ['django.template.context_processors.request', 'django.contrib.messages.context_processors.messages']}}}}]
DATABASES = {{'default': {{'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}}}
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_TZ = True
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
''')
        put(f"{project}/urls.py", '''from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from django.views.generic import TemplateView
from .generated import get_urlpatterns
urlpatterns = [path('', TemplateView.as_view(template_name='home.html'), name='home')] + get_urlpatterns()
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
''')
        put("static/crud.css", STYLE)
        put("templates/home.html", "{% extends 'crud_genifsp/base.html' %}{% block content %}<h1>Cadastro acadêmico</h1><p>Selecione um módulo no menu para listar, cadastrar, consultar, editar ou excluir.</p>{% endblock %}")
        put("requirements.txt", "Django>=4.2,<7\nPillow>=10\n")

    if not previous:
        base = """{% load static %}<!doctype html><html lang="pt-br"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{% block title %}CRUD{% endblock %}</title><link rel="stylesheet" href="{% static 'crud.css' %}"></head><body><header><nav><a href="{% url 'home' %}">Início</a>{% include 'generated_nav.html' %}</nav></header><main>{% block content %}{% endblock %}</main></body></html>"""
        if integrated:
            base = base.replace("{% url 'home' %}", "/")
            settings_path = f"{project}/settings.py"
            urls_path = f"{project}/urls.py"
            for relative, hook in (
                (settings_path, "\n\n# crud-genifsp\nfrom .crud_genifsp_registry import GENERATED_APPS\nINSTALLED_APPS = [*INSTALLED_APPS, *GENERATED_APPS]\nTEMPLATES[0]['DIRS'] = [*TEMPLATES[0].get('DIRS', []), BASE_DIR / 'crud_genifsp_templates']\nSTATICFILES_DIRS = [*globals().get('STATICFILES_DIRS', []), BASE_DIR / 'crud_genifsp_static']\n"),
                (urls_path, "\n\n# crud-genifsp\nfrom .crud_genifsp_registry import get_urlpatterns\nurlpatterns = [*get_urlpatterns(), *urlpatterns]\n"),
            ):
                put(relative, (output / relative).read_text(encoding="utf-8-sig") + hook)
            put("crud_genifsp_static/crud_genifsp/crud.css", STYLE)
        put(("crud_genifsp_templates/" if integrated else "templates/") + "crud_genifsp/base.html",
            base.replace("'generated_nav.html'", "'crud_genifsp/generated_nav.html'")
                .replace("'crud.css'", "'crud_genifsp/crud.css'") if integrated else
            base.replace("'generated_nav.html'", "'crud_genifsp/generated_nav.html'"))
    put(f"{project}/" + ("crud_genifsp_registry.py" if integrated else "generated.py"), "# Gerenciado por crud-genifsp. Personalize settings.py e urls.py livremente.\nfrom django.urls import include, path\nGENERATED_APPS = " + repr([a["name"] for a in all_apps]) + "\ndef get_urlpatterns():\n    return [\n" + "".join(f"        path('{a['name']}/', include('{a['name']}.urls')),\n" for a in all_apps) + "]\n")
    put(("crud_genifsp_templates/" if integrated else "templates/") + nav_template, " ".join(f'<a href="{{% url \'{a["name"]}:list\' %}}">{a["model"]}</a>' for a in all_apps))
    for app in apps:
        name, model = app["name"], app["model"]
        if (output / name).exists():
            raise ValueError(f"Diretorio ja existe: {name}")
        fields = app["fields"]
        label = next((f["name"] for f in fields if f["type"] in {"char", "text", "email"}), None)
        put(f"{name}/__init__.py", "")
        put(f"{name}/apps.py", f"from django.apps import AppConfig\n\nclass {model}Config(AppConfig):\n    default_auto_field = 'django.db.models.BigAutoField'\n    name = {name!r}\n")
        put(f"{name}/migrations/__init__.py", "")
        put(f"{name}/models.py", "from django.db import models\n\n\n" + f"class {model}(models.Model):\n" + "\n".join(field_code(f) for f in fields) + f"\n\n    def __str__(self):\n        return str(self.{label})\n".replace(f"self.{label}", f"self.{label}" if label else "self.pk"))
        put(f"{name}/forms.py", f"from django import forms\nfrom .models import {model}\n\nclass {model}Form(forms.ModelForm):\n    class Meta:\n        model = {model}\n        fields = {[f['name'] for f in fields]!r}\n        widgets = {{" + ", ".join(f"{f['name']!r}: forms.DateInput(attrs={{'type': 'date'}})" for f in fields if f['type'] == 'date') + "}\n")
        put(f"{name}/views.py", f'''from django.db.models.deletion import ProtectedError, RestrictedError
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from .models import {model}
from .forms import {model}Form

class {model}List(ListView):
    model = {model}
    template_name = '{name}/list.html'
    ordering = 'pk'
    paginate_by = 20

class {model}Detail(DetailView):
    model = {model}
    template_name = '{name}/detail.html'

class {model}Create(CreateView):
    model = {model}
    form_class = {model}Form
    template_name = '{name}/form.html'
    success_url = reverse_lazy('{name}:list')

class {model}Update(UpdateView):
    model = {model}
    form_class = {model}Form
    template_name = '{name}/form.html'
    success_url = reverse_lazy('{name}:list')

class {model}Delete(DeleteView):
    model = {model}
    template_name = '{name}/confirm_delete.html'
    success_url = reverse_lazy('{name}:list')

    def form_valid(self, form):
        try:
            return super().form_valid(form)
        except (ProtectedError, RestrictedError):
            return self.render_to_response(self.get_context_data(form=form, error='Este registro possui vínculos. Exclua os registros relacionados primeiro.'), status=409)
''')
        put(f"{name}/urls.py", f"from django.urls import path\nfrom . import views\napp_name = {name!r}\nurlpatterns = [\n" + "".join(f"    path({route!r}, views.{model}{view}.as_view(), name={url!r}),\n" for route, view, url in [("", "List", "list"), ("new/", "Create", "create"), ("<int:pk>/", "Detail", "detail"), ("<int:pk>/edit/", "Update", "update"), ("<int:pk>/delete/", "Delete", "delete")]) + "]\n")
        def url(action, obj=""):
            return "{% url '" + name + ":" + action + "'" + (" " + obj if obj else "") + " %}"
        def page(body):
            return "{% extends " + repr(base_template) + " %}{% block content %}" + body + "{% endblock %}"
        put(f"{name}/templates/{name}/list.html", page(f'<h1>{model}</h1><p><a class="button" href="{url("create")}">Novo cadastro</a></p><table><thead><tr><th>Registro</th><th>Ações</th></tr></thead><tbody>{{% for object in object_list %}}<tr><td>{{{{ object }}}}</td><td class="actions"><a href="{url("detail", "object.pk")}">Detalhes</a><a href="{url("update", "object.pk")}">Editar</a><a href="{url("delete", "object.pk")}">Excluir</a></td></tr>{{% empty %}}<tr><td colspan="2">Nenhum registro.</td></tr>{{% endfor %}}</tbody></table>{{% if page_obj.has_previous %}}<a href="?page={{{{ page_obj.previous_page_number }}}}">Anterior</a>{{% endif %}} {{{{ page_obj.number }}}} {{% if page_obj.has_next %}}<a href="?page={{{{ page_obj.next_page_number }}}}">Próxima</a>{{% endif %}}'))
        details = ""
        for f in fields:
            v = "object." + f["name"]
            val = "{{ " + v + " }}"
            if f["type"] in {"image", "file"}:
                val = "{% if " + v + " %}<a href=\"{{ " + v + ".url }}\">Arquivo</a>" + ("<img alt=\"Foto\" src=\"{{ " + v + ".url }}\">" if f["type"] == "image" else "") + "{% endif %}"
            elif f["type"] == "fk":
                target = f["to"].split(".")[0]
                val = "{% if " + v + " %}<a href=\"{% url '" + target + ":detail' " + v + ".pk %}\">" + val + "</a>{% endif %}"
            elif f["type"] == "m2m":
                val = "{% for related in " + v + ".all %}{{ related }}{% if not forloop.last %}, {% endif %}{% empty %}—{% endfor %}"
            details += f"<dt>{f['name']}</dt><dd>{val}</dd>"
        put(f"{name}/templates/{name}/detail.html", page(f'<h1>{{{{ object }}}}</h1><dl>{details}</dl><a href="{url("update", "object.pk")}">Editar</a> | <a href="{url("list")}">Voltar</a>'))
        put(f"{name}/templates/{name}/form.html", page(f'<h1>{model}: cadastro</h1><form method="post" enctype="multipart/form-data">{{% csrf_token %}}{{{{ form.as_p }}}}<button type="submit">Salvar</button></form><a href="{url("list")}">Cancelar</a>'))
        put(f"{name}/templates/{name}/confirm_delete.html", page(f'<h1>Excluir {{{{ object }}}}?</h1>{{% if error %}}<p class="error">{{{{ error }}}}</p>{{% endif %}}<form method="post">{{% csrf_token %}}<button type="submit">Confirmar exclusão</button></form><a href="{url("list")}">Cancelar</a>'))
    put("crud-genifsp.json", json.dumps({"project": project, "apps": all_apps, "integrated": integrated}, indent=2, ensure_ascii=False))
    if integrating:
        allowed = {output / project / "settings.py", output / project / "urls.py"}
        collisions = [path for path in files if path.exists() and path not in allowed]
        if collisions:
            raise ValueError(f"Arquivo existente seria sobrescrito: {collisions[0]}")
    for path, source in files.items():
        if path.suffix == ".py":
            ast.parse(source, filename=str(path))
        if path.is_symlink() or any(parent.is_symlink() for parent in path.parents if parent != output.parent):
            raise ValueError(f"Destino com link simbolico: {path}")
    if not dry_run:
        for path, source in files.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(source, encoding="utf-8")
    return list(files)
