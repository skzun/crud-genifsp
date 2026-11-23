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

## Adaptar na prova

Edite o JSON antes de gerar. Cada item em `apps` declara `name`, `model` e `fields`.
Veja `examples/instructors_courses.json`. Cada app gerado contém um modelo.

Tipos: `char`, `text`, `image`, `file`, `integer`, `positive_integer`, `decimal`,
`float`, `boolean`, `date`, `datetime`, `email`, `url`, `fk`, `m2m`.

Opções: `max_length`, `blank`, `null`, `default`, `unique`, `upload_to`,
`max_digits`, `decimal_places`, `choices`, `verbose_name`, `help_text`, `related_name`.
Exemplo: `{"name":"price","type":"decimal","max_digits":8,"decimal_places":2}`.
Booleanos JSON são `true`/`false`. Choices usam pares, por exemplo
`"choices": [["A", "Ativo"], ["I", "Inativo"]]`.

Para ForeignKey, use `"to": "instructors.Instructor"` e opcionalmente
`"on_delete": "PROTECT"`. Também aceita CASCADE, RESTRICT e SET_NULL
(o último exige `"null": true`). O padrão PROTECT evita excluir um professor
que ainda possui cursos. A página de exclusão informa o vínculo e retorna 409.

Para adicionar mais dois módulos ao mesmo projeto:

```powershell
# Execute na pasta onde está o esquema e o diretório prova:
python -m crud_genifsp generate examples/students_enrollments.json --output prova --dry-run
python -m crud_genifsp generate examples/students_enrollments.json --output prova
cd prova
python manage.py makemigrations
python manage.py migrate
```

Esse exemplo adiciona students e enrollments relacionados a courses. Apps antigos
e seus models, views e templates permanecem intactos. O gerador atualiza apenas
o manifesto, a navegação gerada e o registro de apps/URLs. Não altera um projeto
Django arbitrário nem sobrescreve um app já existente. Para mudar campos de um
app existente, edite seu models.py, forms.py e templates e rode as migrações.
Modelos existentes continuam disponíveis como alvos de novas relações.

O projeto deve estar parado durante a geração. Faça backup das personalizações
antes de acrescentar apps; o registro generated.py e generated_nav.html é gerenciado.
Migrações são produzidas pelo próprio Django com os comandos acima, inclusive as
dependências entre os apps. A pasta `demo/` inclui as migrações do caso de teste.

## Desenvolvimento e testes

```powershell
python -m pip install -e .
python -m unittest discover -s tests -p "test_*.py" -v
python -m pip install build
python -m build
python -m pip install dist/crud_genifsp-0.1.0-py3-none-any.whl
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
