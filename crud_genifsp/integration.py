"""Add apps and routes to the literal Django lists used in the class."""
import ast
import io
import tokenize


def named_assignment(tree, name, path):
    matches = [
        node for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == name
                for target in node.targets)
    ]
    if len(matches) != 1 or not isinstance(matches[0].value, (ast.List, ast.Tuple)):
        raise ValueError(f"Esperada uma lista literal {name} em {path}.")
    return matches[0]


def ast_offset(lines, lineno, column):
    # The AST counts UTF-8 bytes in a line. The string editor uses characters.
    prefix = lines[lineno - 1].encode("utf-8")[:column].decode("utf-8")
    return sum(map(len, lines[:lineno - 1])) + len(prefix)


def insert_entries(source, collection, entries, newline):
    """Insert entries, keeping comments, indentation and the original source."""
    lines = source.splitlines(keepends=True)
    start = ast_offset(lines, collection.lineno, collection.col_offset)
    end = ast_offset(lines, collection.end_lineno, collection.end_col_offset)
    closing = end - 1
    closing_line = sum(map(len, lines[:collection.end_lineno - 1]))
    closing_indent = source[closing_line:closing]
    if collection.end_lineno > collection.lineno and not closing_indent.strip():
        indent = closing_indent + "    "
        if collection.elts:
            first = collection.elts[0]
            first_offset = ast_offset(lines, first.lineno, first.col_offset)
            first_line = sum(map(len, lines[:first.lineno - 1]))
            first_indent = source[first_line:first_offset]
            if first_indent and not first_indent.strip():
                indent = first_indent
        insertion = (closing_line, "".join(f"{indent}{entry},{newline}" for entry in entries))
    else:
        insertion = (closing, " " + ", ".join(entries) + ",")

    edits = [insertion]
    if collection.elts:
        literal = source[start:end]
        ignored = {tokenize.COMMENT, tokenize.NL, tokenize.NEWLINE,
                   tokenize.INDENT, tokenize.DEDENT, tokenize.ENDMARKER}
        tokens = [
            tok for tok in tokenize.generate_tokens(io.StringIO(literal).readline)
            if tok.type not in ignored
        ]
        if tokens[-2].string != ",":
            row, col = tokens[-2].end
            offset = start + sum(map(len, literal.splitlines(keepends=True)[:row - 1])) + col
            edits.append((offset, ","))
    for offset, addition in sorted(edits, key=lambda edit: edit[0], reverse=True):
        source = source[:offset] + addition + source[offset:]
    return source


def read_source(path):
    data = path.read_bytes()
    encoding, _ = tokenize.detect_encoding(io.BytesIO(data).readline)
    return data, data.decode(encoding), encoding


def has_setting(tree, name):
    return any(
        isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == name for target in node.targets)
        for node in tree.body
    )


def has_media_route(tree):
    return any(
        isinstance(node, ast.Call)
        and any(isinstance(arg, ast.Attribute) and arg.attr == "MEDIA_URL" for arg in node.args)
        for node in ast.walk(tree)
    )


def local_model_targets(output, project):
    """Read the standard local apps without importing the existing project."""
    settings = output / project / "settings.py"
    tree = ast.parse(settings.read_bytes(), filename=str(settings))
    installed = named_assignment(tree, "INSTALLED_APPS", settings).value
    targets = set()
    for entry in installed.elts:
        if not isinstance(entry, ast.Constant) or not isinstance(entry.value, str):
            continue
        app = entry.value.split(".", 1)[0]
        if not app.isidentifier() or (entry.value != app and not entry.value.startswith(f"{app}.apps.")):
            continue
        source = output / app / "models.py"
        if not source.is_file():
            continue
        models_tree = ast.parse(source.read_bytes(), filename=str(source))
        for model in models_tree.body:
            if not isinstance(model, ast.ClassDef):
                continue
            uses_django_model = any(
                isinstance(base, ast.Attribute) and isinstance(base.value, ast.Name)
                and base.value.id == "models" and base.attr == "Model"
                for base in model.bases
            )
            abstract = any(
                isinstance(meta, ast.ClassDef) and meta.name == "Meta"
                and any(
                    isinstance(node, ast.Assign)
                    and any(isinstance(target, ast.Name) and target.id == "abstract" for target in node.targets)
                    and isinstance(node.value, ast.Constant) and node.value.value is True
                    for node in meta.body
                )
                for meta in model.body
            )
            if uses_django_model and not abstract:
                targets.add(f"{app}.{model.name}")
    return targets


def integration_plan(output, project, apps):
    settings_path = output / project / "settings.py"
    urls_path = output / project / "urls.py"
    original_settings, settings, settings_encoding = read_source(settings_path)
    original_urls, urls, urls_encoding = read_source(urls_path)
    settings_newline = "\r\n" if "\r\n" in settings else "\n"
    urls_newline = "\r\n" if "\r\n" in urls else "\n"
    settings_tree = ast.parse(settings, filename=str(settings_path))
    urls_tree = ast.parse(urls, filename=str(urls_path))

    installed_apps = named_assignment(settings_tree, "INSTALLED_APPS", settings_path).value
    app_names = [app["name"] for app in apps]
    registered = {
        element.value.split(".", 1)[0] for element in installed_apps.elts
        if isinstance(element, ast.Constant) and isinstance(element.value, str)
    }
    duplicates = registered.intersection(app_names)
    if duplicates:
        raise ValueError(f"Apps ja registrados em INSTALLED_APPS: {', '.join(sorted(duplicates))}.")
    settings = insert_entries(settings, installed_apps, list(map(repr, app_names)), settings_newline)

    urlpatterns = named_assignment(urls_tree, "urlpatterns", urls_path)
    urls = insert_entries(
        urls, urlpatterns.value,
        [f"path('', include('{name}.urls'))" for name in app_names],
        urls_newline,
    )
    imported = {
        alias.asname or alias.name for node in urls_tree.body
        if isinstance(node, ast.ImportFrom) and node.module == "django.urls"
        for alias in node.names
    }
    missing_imports = [name for name in ("path", "include") if name not in imported]
    if missing_imports:
        line_start = sum(map(len, urls.splitlines(keepends=True)[:urlpatterns.lineno - 1]))
        statement = "from django.urls import " + ", ".join(missing_imports)
        urls = urls[:line_start] + statement + urls_newline * 2 + urls[line_start:]

    uploads = any(field["type"] in {"image", "file"} for app in apps for field in app["fields"])
    if uploads:
        for name, value in (("MEDIA_URL", "'/media/'"), ("MEDIA_ROOT", "BASE_DIR / 'media'")):
            if not has_setting(settings_tree, name):
                settings += settings_newline * 2 + f"{name} = {value}" + settings_newline
        if not has_media_route(urls_tree):
            media_lines = [
                "",
                "",
                "from django.conf import settings as _crud_settings",
                "from django.conf.urls.static import static as _crud_static",
                "",
                "if _crud_settings.DEBUG:",
                "    urlpatterns += _crud_static(_crud_settings.MEDIA_URL, document_root=_crud_settings.MEDIA_ROOT)",
                "",
            ]
            urls += urls_newline.join(media_lines)

    updates = {
        settings_path: (original_settings, settings.encode(settings_encoding)),
        urls_path: (original_urls, urls.encode(urls_encoding)),
    }
    for path, (_, updated) in updates.items():
        ast.parse(updated, filename=str(path))
    return updates
