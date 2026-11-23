"""Validate the schema before generating any Django source."""
from collections import Counter
import importlib.util
import keyword
from pathlib import PurePosixPath, PureWindowsPath

from django.db.models import Model


TYPES = {
    "char": "CharField", "text": "TextField", "image": "ImageField", "file": "FileField",
    "integer": "IntegerField", "positive_integer": "PositiveIntegerField",
    "decimal": "DecimalField", "float": "FloatField", "boolean": "BooleanField",
    "date": "DateField", "datetime": "DateTimeField", "email": "EmailField",
    "url": "URLField", "fk": "ForeignKey", "m2m": "ManyToManyField",
}
MODEL_OPTIONS = {
    "max_length", "blank", "null", "default", "unique", "upload_to", "max_digits",
    "decimal_places", "choices", "verbose_name", "help_text", "related_name",
}
TYPE_OPTIONS = {
    "image": {"upload_to", "profile"},
    "file": {"upload_to"},
    "decimal": {"max_digits", "decimal_places"},
    "fk": {"to", "related_name", "on_delete"},
    "m2m": {"to", "related_name"},
}
SPECIFIC_OPTIONS = frozenset().union(*TYPE_OPTIONS.values())
COMMON_OPTIONS = MODEL_OPTIONS - SPECIFIC_OPTIONS
RELATIONS = {"fk", "m2m"}
NULLABLE_WHEN_BLANK = {"integer", "positive_integer", "decimal", "float", "date", "datetime", "fk"}
DELETE_POLICIES = ("PROTECT", "CASCADE", "RESTRICT", "SET_NULL")
RESERVED_APP_NAMES = {
    "admin", "auth", "contenttypes", "sessions", "messages", "staticfiles",
    "django", "manage", "static", "media", "templates", "requirements",
    "crud_genifsp_static", "crud_genifsp_templates",
    "con", "prn", "aux", "nul",
    *(f"com{number}" for number in range(1, 10)),
    *(f"lpt{number}" for number in range(1, 10)),
}


def identifier(value, context="Identificador"):
    if (not isinstance(value, str) or not value.isidentifier()
            or keyword.iskeyword(value) or value.startswith("_")):
        raise ValueError(f"{context} invalido: {value!r}. Use um identificador Python.")
    return value


def validate(schema, previous, project, local_targets=()):
    identifier(project, "Nome do projeto")
    if previous and project != previous["project"]:
        raise ValueError("O projeto deve manter o mesmo nome.")
    apps = schema.get("apps")
    if not isinstance(apps, list) or not apps:
        raise ValueError("apps deve ser uma lista nao vazia.")

    # Case-insensitive comparison also protects Windows against two paths for the same app.
    existing = previous.get("apps", [])
    known_names = {app["name"].casefold() for app in existing}
    known_names.update(target.split(".", 1)[0].casefold() for target in local_targets)
    reserved = RESERVED_APP_NAMES | {project.casefold()}
    for index, app in enumerate(apps, 1):
        if not isinstance(app, dict):
            raise ValueError(f"apps[{index - 1}] deve ser um objeto JSON.")
        name = identifier(app.get("name"), f"Nome do app {index}")
        model = identifier(app.get("model"), f"Modelo do app {name}")
        if name.casefold() in known_names | reserved or importlib.util.find_spec(name):
            raise ValueError(f"App existente, duplicado ou nome reservado: {name}. Use outro nome.")
        if model in {"Meta", "objects", "DoesNotExist", "MultipleObjectsReturned", "admin", "forms"}:
            raise ValueError(f"Nome de modelo reservado: {model}")
        known_names.add(name.casefold())

    targets = {f"{app['name']}.{app['model']}" for app in existing + apps} | set(local_targets)
    validated = []
    for app in apps:
        fields = app.get("fields")
        if not isinstance(fields, list) or not fields:
            raise ValueError(f"O app {app['name']} precisa de uma lista fields nao vazia.")
        seen = set()
        for field in fields:
            if not isinstance(field, dict):
                raise ValueError(f"Cada campo de {app['name']}.fields deve ser um objeto JSON.")
            name = identifier(field.get("name"), f"Nome de campo em {app['name']}")
            if (name in seen or name in {"id", "pk", "objects", "Meta"}
                    or "__" in name or name.endswith("_") or hasattr(Model, name)):
                raise ValueError(f"Campo duplicado ou reservado: {app['name']}.{name}")
            seen.add(name)
            validate_field(app["name"], field, targets)
        for field in fields:
            if field["type"] == "fk" and f"{field['name']}_id" in seen:
                raise ValueError(f"{app['name']}.{field['name']}_id ja e criado pela ForeignKey.")
        validated.append({**app, "fields": [dict(field) for field in fields]})

    assign_related_names(validated, existing, set(local_targets))
    return validated


def validate_field(app, field, targets):
    location = f"{app}.{field['name']}"
    kind = field.get("type")
    if not isinstance(kind, str) or kind not in TYPES:
        raise ValueError(f"Tipo desconhecido em {location}: {kind!r}.")
    allowed = {"name", "type"} | COMMON_OPTIONS | TYPE_OPTIONS.get(kind, set())
    unsupported = field.keys() - allowed
    if kind == "m2m":
        unsupported |= field.keys() & {"null", "unique", "default", "choices"}
    if unsupported:
        raise ValueError(f"Opcoes invalidas para {kind} em {location}: {', '.join(sorted(unsupported))}.")
    for option in {"blank", "null", "unique", "profile"} & field.keys():
        if type(field[option]) is not bool:
            raise ValueError(f"{location}.{option} deve ser true ou false.")
    if kind in NULLABLE_WHEN_BLANK and field.get("blank") and not field.get("null"):
        raise ValueError(f"{location}: blank: true exige null: true para o campo {kind}.")
    if "max_length" in field and (type(field["max_length"]) is not int or field["max_length"] < 1):
        raise ValueError(f"{location}.max_length deve ser um inteiro positivo.")
    if kind == "decimal":
        digits, places = field.get("max_digits"), field.get("decimal_places")
        if type(digits) is not int or type(places) is not int or not 0 <= places < digits:
            raise ValueError(f"{location} exige max_digits > decimal_places >= 0, ambos inteiros.")
    if "upload_to" in field:
        path = field["upload_to"]
        if (not isinstance(path, str) or "\\" in path or PureWindowsPath(path).drive
                or PurePosixPath(path).is_absolute() or ".." in PurePosixPath(path).parts):
            raise ValueError(f"{location}.upload_to deve usar uma pasta relativa a media com barras '/'.")
    if "choices" in field:
        choices = field["choices"]
        if not isinstance(choices, list) or any(not isinstance(pair, (list, tuple)) or len(pair) != 2 for pair in choices):
            raise ValueError(f"{location}.choices deve ser uma lista de pares [valor, rotulo].")
    if kind in RELATIONS:
        target = field.get("to")
        if not isinstance(target, str) or target not in targets:
            raise ValueError(f"Relacao inexistente em {location}: {target!r}. Use app.Modelo.")
        related_name = field.get("related_name")
        if related_name is not None and (
            not isinstance(related_name, str)
            or not (related_name.isidentifier() or related_name.endswith("+"))
        ):
            raise ValueError(f"{location}.related_name deve ser um identificador ou '+'.")
    if kind == "fk":
        policy = field.get("on_delete", "PROTECT")
        if policy not in DELETE_POLICIES:
            raise ValueError(f"{location}.on_delete deve ser uma destas opcoes: {', '.join(DELETE_POLICIES)}.")
        if policy == "SET_NULL" and not field.get("null"):
            raise ValueError(f"{location}: SET_NULL exige null: true.")


def relation_fields(apps):
    for app in apps:
        for field in app["fields"]:
            if field["type"] in RELATIONS:
                yield app, field


def default_reverse_name(app):
    return app["model"].lower() + "_set"


def assign_related_names(apps, existing, local_targets):
    implicit = Counter(
        (field["to"], default_reverse_name(app))
        for app, field in relation_fields(existing + apps)
        if field.get("related_name") is None
    )
    for app, field in relation_fields(apps):
        target = field["to"]
        if field.get("related_name") is None and (
            target in local_targets or implicit[target, default_reverse_name(app)] > 1
        ):
            field["related_name"] = f"{app['name']}_{field['name']}_set"

    used = {}
    for app, field in relation_fields(existing + apps):
        related_name = field.get("related_name") or default_reverse_name(app)
        if related_name.endswith("+"):
            continue
        key = field["to"], related_name
        location = f"{app['name']}.{field['name']}"
        if key in used:
            raise ValueError(f"related_name duplicado para {field['to']}: {location} e {used[key]}.")
        used[key] = location
