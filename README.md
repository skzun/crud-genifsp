# crud-genifsp

Gerador de projetos Django para estudo: recebe um esquema JSON e escreve models,
ModelForms, views, URLs e páginas HTML locais de listar, detalhar, criar, editar e
excluir. Os arquivos gerados são código Django comum e podem ser editados.
Consulte as regras da sua avaliação antes de usar bibliotecas externas.

## Instalar e executar

Depois da publicação no PyPI:

```powershell
python -m pip install crud-genifsp
python -m crud_genifsp example schema.json
python -m crud_genifsp generate schema.json --output prova
cd prova
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```

Abra http://127.0.0.1:8000/. Os módulos instructors e courses têm páginas próprias,
sem depender do Django Admin. `photo` é um ImageField validado pelo Pillow;
o formulário usa multipart e CSRF. O campo instructor é um select com os
professores cadastrados. Crie o professor antes de cadastrar um curso.
Os detalhes do curso incluem um link para o professor. O CSS é local, sem CDN.

O comando também está disponível como `crud-genifsp`. Caso o executável não esteja
no PATH do Windows, use `python -m crud_genifsp`.

## Manual instalado

A partir da versão 0.1.5, o [MANUAL.md](crud_genifsp/MANUAL.md) acompanha o pacote.
Ele explica a preparação da aula 8, as variações do esquema, o assistente
interativo, as rotas e os ajustes que podem ser pedidos no enunciado.

```bat
crud-genifsp manual
crud-genifsp manual --output MANUAL.md
```

## Começar com o exercício da aula 8

Abra o CMD na pasta com `manage.py`, depois de descompactar o ZIP da aula.

```bat
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install crud-genifsp==0.1.5
crud-genifsp example schema.json
crud-genifsp generate schema.json --output . --migrate
python manage.py check
python manage.py runserver
```

Abra [Instrutores](http://127.0.0.1:8000/instructors/) e [Cursos](http://127.0.0.1:8000/courses/).
Caso o enunciado mude, ajuste `schema.json` antes de gerar ou use
`crud-genifsp wizard --migrate` no lugar de `example` e `generate`.
No projeto da aula, é possível ligar os apps novos a `members.Member`
ou `plans.Plan`.

## Desenvolvimento e testes

```powershell
python -m pip install -e .
python -m unittest discover -s tests -p "test_*.py" -v
python -m pip install build
python -m build
python -m pip install dist/crud_genifsp-0.1.5-py3-none-any.whl
```

O teste de integração gera um projeto temporário, cria e aplica migrações,
acrescenta dois apps e exercita CRUD HTTP com CSRF real, imagem válida/inválida,
FK inválida, relação M2M, HTML escapado e proteção na exclusão. As dependências
precisam estar instaladas ou disponíveis no índice para uma instalação offline.

Ambiente de desenvolvimento local: DEBUG habilitado, SQLite e páginas acessíveis
sem autenticação, conforme o exercício. Antes de publicar o aplicativo na internet,
adicione autenticação/permissões, ajuste os hosts, segredo, DEBUG e entrega de mídia.
Excluir registros não remove os arquivos enviados do disco automaticamente.

## Publicar

O workflow `.github/workflows/publish.yml` testa, constrói e publica versões
marcadas `v*` usando PyPI Trusted Publishing. Configure no PyPI o projeto
`crud-genifsp`, owner `skzun`, repositório `crud-genifsp`, workflow `publish.yml`
e environment `pypi`. A versão em pyproject.toml deve coincidir com a tag.
Nenhuma chave de GitHub ou PyPI deve ser incluída no código.

Referências: https://docs.djangoproject.com/en/5.2/topics/forms/modelforms/
e https://docs.pypi.org/trusted-publishers/using-a-publisher/.
