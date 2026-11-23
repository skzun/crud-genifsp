"""Small command line interface. Generated projects do not need this package."""
import argparse
import json
from pathlib import Path

from .generator import generate, example
from .wizard import prompt_schema


def main():
    parser = argparse.ArgumentParser(description="Gera CRUDs Django editaveis para estudo.")
    sub = parser.add_subparsers(dest="command", required=True)
    sample = sub.add_parser("example", help="Escreve o esquema instructors/courses")
    sample.add_argument("path", nargs="?", default="schema.json")
    gen = sub.add_parser("generate", help="Cria projeto ou acrescenta apps ao projeto gerado")
    gen.add_argument("schema", type=Path)
    gen.add_argument("--output", type=Path, default=Path("prova"))
    gen.add_argument("--dry-run", action="store_true")
    wizard = sub.add_parser("wizard", help="Monta e gera o CRUD com perguntas no terminal")
    wizard.add_argument("--output", type=Path, default=Path("."))
    wizard.add_argument("--schema", type=Path, default=Path("schema.json"))
    args = parser.parse_args()
    try:
        if args.command == "example":
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
                generate(schema, args.output, dry_run=True)
                with args.schema.open("x", encoding="utf-8") as f:
                    json.dump(schema, f, indent=2, ensure_ascii=False)
            else:
                schema = json.loads(args.schema.read_text(encoding="utf-8-sig"))
            paths = generate(schema, args.output, dry_run)
            print("\n".join(str(p) for p in paths))
            if not dry_run:
                print(f"\ncd {args.output}\npython manage.py makemigrations\npython manage.py migrate\npython manage.py runserver")
    except (EOFError, KeyboardInterrupt):
        parser.exit(130, "\nOperacao cancelada.\n")
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        parser.exit(2, f"Erro: {exc}\n")
