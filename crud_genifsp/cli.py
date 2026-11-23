"""Small command line interface. Generated projects do not need this package."""
import argparse
from importlib.resources import files
import json
from pathlib import Path
import subprocess
import sys

from .generator import generate, example
from .wizard import prompt_schema


def apply_migrations(schema, output):
    app_names = [app["name"] for app in schema["apps"]]
    commands = [("makemigrations", *app_names, "--noinput"), ("migrate", "--noinput")]
    for command in commands:
        print("Executando: python manage.py " + " ".join(command), flush=True)
        result = subprocess.run([sys.executable, "manage.py", *command], cwd=output)
        if result.returncode:
            raise ValueError("Arquivos gerados. Corrija o erro acima e retome com os comandos de migracao.")


def main():
    parser = argparse.ArgumentParser(description="Gera CRUDs Django editaveis para estudo.")
    sub = parser.add_subparsers(dest="command", required=True)
    manual = sub.add_parser("manual", help="Mostra ou copia o manual Markdown instalado")
    manual.add_argument("-o", "--output", type=Path, help="Salva uma copia no caminho informado")
    sample = sub.add_parser("example", help="Escreve o esquema instructors/courses")
    sample.add_argument("path", nargs="?", default="schema.json")
    gen = sub.add_parser("generate", help="Cria projeto ou acrescenta apps ao projeto gerado")
    gen.add_argument("schema", type=Path)
    gen.add_argument("--output", type=Path, default=Path("prova"))
    modes = gen.add_mutually_exclusive_group()
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--migrate", action="store_true", help="Cria e aplica as migracoes")
    wizard = sub.add_parser("wizard", help="Monta e gera o CRUD com perguntas no terminal")
    wizard.add_argument("--output", type=Path, default=Path("."))
    wizard.add_argument("--schema", type=Path, default=Path("schema.json"))
    wizard.add_argument("--migrate", action="store_true", help="Cria e aplica as migracoes")
    args = parser.parse_args()
    try:
        if args.command == "manual":
            guide = files("crud_genifsp").joinpath("MANUAL.md")
            if args.output is None:
                sys.stdout.write(guide.read_text(encoding="utf-8"))
            else:
                with args.output.open("xb") as f:
                    f.write(guide.read_bytes())
                print(f"Manual salvo: {args.output}")
        elif args.command == "example":
            path = Path(args.path)
            with path.open("x", encoding="utf-8") as f:
                json.dump(example(), f, indent=2, ensure_ascii=False)
            print(f"Esquema criado: {path}")
        else:
            dry_run = getattr(args, "dry_run", False)
            if args.command == "wizard":
                if args.schema.exists():
                    raise ValueError(f"O esquema {args.schema} ja existe. Escolha outro com --schema.")
                schema = prompt_schema(args.output)
                planned_paths = generate(schema, args.output, dry_run=True)
                if args.schema.resolve() in planned_paths:
                    raise ValueError("Escolha um nome de esquema diferente dos arquivos gerados.")
                if not args.schema.parent.is_dir():
                    raise ValueError(f"A pasta do esquema nao existe: {args.schema.parent}")
            else:
                schema = json.loads(args.schema.read_text(encoding="utf-8-sig"))
            paths = generate(schema, args.output, dry_run)
            if args.command == "wizard":
                with args.schema.open("x", encoding="utf-8") as f:
                    json.dump(schema, f, indent=2, ensure_ascii=False)
            print("\n".join(str(p) for p in paths))
            if not dry_run:
                if args.migrate:
                    apply_migrations(schema, args.output)
                print(f'\ncd "{args.output}"')
                if not args.migrate:
                    print("python manage.py makemigrations\npython manage.py migrate")
                print("python manage.py runserver")
    except (EOFError, KeyboardInterrupt):
        parser.exit(130, "\nOperacao cancelada.\n")
    except (ValueError, OSError, SyntaxError) as exc:
        parser.exit(2, f"Erro: {exc}\n")
