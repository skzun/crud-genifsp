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

## Passo a passo na aula 8

**1. Abra o projeto da prova.** Descompacte o ZIP da aula em uma pasta nova.
Abra no Explorador a pasta que contém o arquivo `manage.py` e digite `cmd` na
barra de endereços. Execute `dir manage.py` para confirmar que está no local certo.

**2. Prepare o ambiente.** No CMD, execute os comandos abaixo. A versão 0.1.4
é a primeira que usa as rotas da aula e registra os apps dentro de `INSTALLED_APPS`.

```bat
py -m venv .venv
.venv\Scripts\activate.bat
pip install django pillow crud-genifsp==0.1.4
pip show crud-genifsp
```

Se `py -m venv .venv` responder que não encontrou Python, rode `python -m venv .venv`.
Antes de gerar, confira que o `pip show crud-genifsp` exibe `Version: 0.1.4`.

**3. Gere os apps na pasta atual.** Para o enunciado com instructors e courses,
use o modelo pronto.

```bat
crud-genifsp example schema.json
crud-genifsp generate schema.json --output . --migrate
py manage.py check
py manage.py runserver
```

O ponto em `--output .` indica a pasta do projeto original. Com `--migrate`,
o gerador cria as migrações dos apps novos e aplica as pendentes no mesmo
SQLite. As duas pastas novas ficam ao lado de `members` e `plans`.
Confira em `setup/settings.py` as entradas `'instructors'` e `'courses'` dentro
de `INSTALLED_APPS`. Em `setup/urls.py`, há um `include` para cada app dentro da lista
`urlpatterns`. Cada app vem com models.py, forms.py, views.py, urls.py,
admin.py e templates.

**4. Verifique os CRUDs.** Abra a [lista de instrutores](http://127.0.0.1:8000/instructors/)
e cadastre um instrutor com foto. Em [Cursos](http://127.0.0.1:8000/courses/),
crie um curso, selecione o instrutor e edite o registro. Confira o vínculo
na tela de detalhes. A exclusão de um instrutor com cursos é bloqueada.

| Ação | Exemplo em instructors |
| --- | --- |
| Listar | /instructors/ |
| Ver detalhes | /instructors/details/1 |
| Abrir cadastro | /instructors/add/ |
| Salvar cadastro | POST /instructors/add/addrecord/ |
| Abrir edição | /instructors/update/1 |
| Salvar edição | POST /instructors/update/updaterecord/1 |
| Confirmar exclusão | GET /instructors/delete/1, seguido de POST na mesma rota |

Os cursos seguem as mesmas rotas sob /courses/. Para conferir os registros
no [Django Admin](http://127.0.0.1:8000/admin/), crie um superusuário com
`py manage.py createsuperuser` em outro CMD com o ambiente ativado.

### Quando o enunciado mudar

No passo 3, troque os comandos `example` e `generate` por `crud-genifsp wizard --migrate`.
Informe os módulos e modelos antes dos campos. Para reproduzir o exemplo
interativamente, informe 2 módulos, com as pastas instructors e courses
e os modelos Instructor e Course. Digite 2 campos para Instructor e 3
para Course.

| Modelo | Campo | Tipo | Respostas adicionais |
| --- | --- | --- | --- |
| Instructor | name | char | Comprimento 150, opcional n |
| Instructor | photo | image | Pasta instructors/, miniatura s, opcional n |
| Course | name | char | Comprimento 150, opcional n |
| Course | description | text | Opcional n |
| Course | instructor | fk | Alvo instructors.Instructor, exclusão PROTECT, opcional n |

O assistente salva as respostas em schema.json. Para acrescentar outros
apps depois, execute `crud-genifsp wizard --schema novos.json --migrate`. Escolha como alvo de uma relação
um modelo novo ou já cadastrado pelo gerador. O gerador preserva os apps
já existentes. Para conferir esta estrutura em uma cópia gerada com a
versão 0.1.3, extraia de novo o ZIP e repita a geração com a versão 0.1.4.

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
o manifesto, a navegação gerada e o registro de apps/URLs. Aceita a integração automática em projetos no layout padrão do Django e
recusa sobrescrever um app já existente. Para mudar campos de um
app existente, edite seu models.py, forms.py e templates e rode as migrações.
Modelos existentes continuam disponíveis como alvos de novas relações.

Pare o servidor durante a geração. O manifesto, o registro de apps e o menu
gerado são mantidos pelo gerador. Se você omitir `--migrate`, rode
`python manage.py makemigrations` e `python manage.py migrate` antes de abrir as páginas.

## Desenvolvimento e testes

```powershell
python -m pip install -e .
python -m unittest discover -s tests -p "test_*.py" -v
python -m pip install build
python -m build
python -m pip install dist/crud_genifsp-0.1.4-py3-none-any.whl
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
