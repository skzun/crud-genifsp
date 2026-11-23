"""Interactive schema entry for the CLI."""
import json

from .generator import TYPES, identifier


def ask(label, default=None):
    while True:
        hint = f" [{default}]" if default is not None else ""
        value = input(f"{label}{hint}: ").strip()
        if value or default is not None:
            return value or str(default)


def number(label, default=None, minimum=1):
    while True:
        value = ask(label, default)
        if value.isdecimal() and int(value) >= minimum:
            return int(value)
        print(f"Informe um inteiro maior ou igual a {minimum}.")


def choose(label, options, default=None):
    values = dict(enumerate(options, 1))
    print("  ".join(f"{i}. {value}" for i, value in values.items()))
    while True:
        value = ask(label, default)
        if value in options:
            return value
        if value.isdecimal() and int(value) in values:
            return values[int(value)]
        print("Escolha uma das opcoes acima.")


def prompt_schema(output):
    manifest = output / "crud-genifsp.json"
    existing = json.loads(manifest.read_text(encoding="utf-8")) if manifest.is_file() else {}
    apps = []
    for index in range(number("Quantos modulos deseja criar")):
        print(f"\nModulo {index + 1}")
        name = identifier(ask("Nome da pasta do modulo (ex.: instructors)"))
        model = identifier(ask("Nome da classe do modelo (ex.: Instructor)"))
        apps.append({"name": name, "model": model, "fields": []})
    targets = [
        f"{app['name']}.{app['model']}"
        for app in existing.get("apps", []) + apps
    ]
    for app in apps:
        print(f"\nCampos de {app['model']}")
        count = number("Quantos campos (sem contar o ID automatico)")
        for index in range(count):
            name = identifier(ask(f"Nome do campo {index + 1}"))
            kind = choose("Tipo do campo", list(TYPES))
            field = {"name": name, "type": kind}
            if kind == "char":
                field["max_length"] = number("Limite de caracteres", 150)
            if kind == "decimal":
                places = number("Casas decimais", 2, minimum=0)
                field["decimal_places"] = places
                field["max_digits"] = number("Total de digitos", max(10, places + 1), minimum=places + 1)
            if kind in {"image", "file"}:
                field["upload_to"] = ask("Subpasta em media", f"{app['name']}/")
                if kind == "image":
                    field["profile"] = choose("Mostrar miniatura de perfil na lista", ["s", "n"], "n") == "s"
            if kind in {"fk", "m2m"}:
                field["to"] = choose("Modelo relacionado", targets)
                if kind == "fk":
                    action = choose("Ao excluir o registro relacionado", ["PROTECT", "CASCADE", "RESTRICT", "SET_NULL"], "PROTECT")
                    field["on_delete"] = action
                    if action == "SET_NULL":
                        field.update(null=True, blank=True)
            if not field.get("blank"):
                optional = choose("Campo opcional", ["s", "n"], "n") == "s"
                if optional:
                    field["blank"] = True
                    if kind not in {"char", "text", "email", "url", "image", "file", "m2m", "boolean"}:
                        field["null"] = True
            app["fields"].append(field)
    return {"project": existing.get("project", "config"), "apps": apps}
