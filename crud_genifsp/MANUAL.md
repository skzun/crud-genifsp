# Manual do crud-genifsp

Guia para gerar e conferir os CRUDs do My Tennis Club, aula 8, no Windows. O pacote gera um modelo por app, com código Django e páginas próprias para listar, detalhar, cadastrar, editar e excluir registros.

## 1. Preparar a pasta da prova

1. Extraia o ZIP fornecido para uma pasta nova. Abra no Explorador a pasta que contém `manage.py`, `setup`, `members` e `plans`.
2. Digite `cmd` na barra de endereços do Explorador e pressione Enter. Rode `dir manage.py` para confirmar o diretório.
3. Crie o ambiente virtual, ative-o e instale o pacote. Ele traz Django e Pillow como dependências. A versão `0.1.5` é a primeira que inclui este manual e as correções descritas aqui.

```bat
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install crud-genifsp==0.1.5
python -m pip show crud-genifsp
```

Se o laboratório usar o lançador `py`, você pode criar o ambiente com `py -m venv .venv`. Depois de ativar o ambiente, use `python` nos comandos seguintes. Procure `Version: 0.1.5` na saída de `pip show`.

Se já tiver a versão instalada, ative o mesmo ambiente na próxima sessão do CMD. Se `crud-genifsp` não for encontrado, substitua o comando por `python -m crud_genifsp`.

### Consultar ou copiar este manual

```bat
crud-genifsp manual
crud-genifsp manual --output MANUAL.md
notepad MANUAL.md
```

O primeiro comando exibe o manual, e o segundo cria uma cópia na pasta atual. O comando de cópia recusa um arquivo que já existe. Para escolher outro nome, use `--output MANUAL-CRUD.md`. Você também encontra o original em `.venv\Lib\site-packages\crud_genifsp\MANUAL.md`. Depois da instalação, a leitura funciona sem internet.

## 2. Gerar o exercício de instrutores e cursos

Se o enunciado pedir `Instructor(name, photo)` e `Course(name, description, instructor)`, use o esquema pronto.

```bat
crud-genifsp example schema.json
crud-genifsp generate schema.json --output . --migrate
python manage.py check
python manage.py runserver
```

- `example` cria somente `schema.json`. Você pode abrir e editar esse arquivo antes de executar `generate`.
- `--output .` significa a pasta atual, a mesma do `manage.py` da aula.
- `--migrate` cria as migrações dos apps novos e aplica as pendentes no banco existente. Para somente prever quais arquivos serão escritos, use `crud-genifsp generate schema.json --output . --dry-run`.
- Use `Ctrl+C` no CMD para parar o servidor antes de gerar outros apps ou aplicar migrações.

O gerador cria `instructors` e `courses` ao lado de `members` e `plans`. Cada módulo recebe `models.py`, `forms.py`, `views.py`, `urls.py`, `admin.py` e templates. Em `setup/settings.py`, confira `'instructors'` e `'courses'` dentro de `INSTALLED_APPS`. Em `setup/urls.py`, procure os dois `include(...)` dentro de `urlpatterns`. O site continua usando o `manage.py`, o SQLite e a mídia da aula.

### Conferir no navegador

1. Abra [Instrutores](http://127.0.0.1:8000/instructors/) e cadastre um instrutor com foto. Veja se ela aparece na lista e nos detalhes.
2. Abra [Cursos](http://127.0.0.1:8000/courses/) e cadastre um curso. Escolha o instrutor no formulário. Confira a descrição e o vínculo nos detalhes.
3. Edite um registro. Tente excluir o instrutor ainda ligado ao curso. Com `PROTECT`, o sistema pede que você exclua o curso primeiro.
4. Confira também [a página inicial do clube](http://127.0.0.1:8000/) e [os membros](http://127.0.0.1:8000/members/).

| Ação | Rota do exemplo |
| --- | --- |
| Listar | `/instructors/` |
| Abrir detalhes | `/instructors/details/1` |
| Abrir cadastro | `/instructors/add/` |
| Salvar cadastro | `POST /instructors/add/addrecord/` |
| Abrir edição | `/instructors/update/1` |
| Salvar edição | `POST /instructors/update/updaterecord/1` |
| Confirmar e excluir | `/instructors/delete/1`, com envio por `POST` |

Troque `1` pelo ID do registro e `instructors` por `courses` nas rotas de curso. Os formulários e os botões já apontam para as rotas de gravação.

Para conferir os novos modelos no [Django Admin](http://127.0.0.1:8000/admin/), crie um usuário com `python manage.py createsuperuser`. Faça isso em outro CMD na pasta do projeto, com o ambiente ativado. Os CRUDs públicos podem ser testados pelos links acima.

## 3. Adaptar o esquema quando o enunciado mudar

Use os nomes e campos exatos do enunciado. Cada objeto em `apps` tem `name`, a pasta do app, `model`, o nome da classe, e `fields`, a lista de campos. Prefira `snake_case` para apps e campos e `PascalCase` para classes. O Django cria o ID automaticamente.

### Trocar o app e remover a foto

Se o enunciado pedir `Teacher` sem foto e um curso ligado a esse professor, você pode usar o seguinte `schema.json`.

```json
{
  "apps": [
    {
      "name": "teachers",
      "model": "Teacher",
      "fields": [
        {"name": "name", "type": "char", "max_length": 150}
      ]
    },
    {
      "name": "courses",
      "model": "Course",
      "fields": [
        {"name": "name", "type": "char", "max_length": 150},
        {"name": "description", "type": "text"},
        {"name": "teacher", "type": "fk", "to": "teachers.Teacher", "on_delete": "PROTECT"}
      ]
    }
  ]
}
```

Ao retirar uma foto, remova o objeto inteiro do campo `photo`, incluindo a vírgula que ficaria sobrando. Ao renomear um app ou modelo, ajuste todos os `to` que apontavam para ele. Se o enunciado dispensar a relação, remova também o campo da chave estrangeira. No exemplo acima, a listagem passa a ser `/teachers/` e o formulário do curso passa a usar `teacher`.

Valide e aplique o esquema na pasta do `manage.py`.

```bat
python -m json.tool schema.json
crud-genifsp generate schema.json --output . --dry-run
crud-genifsp generate schema.json --output . --migrate
python manage.py check
python manage.py runserver
```

### Tipos de campos

| Enunciado | `type` no JSON | Opções comuns |
| --- | --- | --- |
| Nome ou texto curto | `char` | `max_length`, padrão 150 |
| Descrição longa | `text` | `blank` para permitir vazio |
| Inteiro ou contador | `integer`, `positive_integer` | `default` e `null` conforme o enunciado |
| Preço ou nota decimal | `decimal` | `max_digits` e `decimal_places`, com `max_digits > decimal_places >= 0` |
| Medida aproximada | `float` | `default` numérico |
| Sim ou não | `boolean` | `default` com `true` ou `false` |
| Data, ou data e hora | `date`, `datetime` | `blank` e `null` se puder ficar vazio |
| Endereço de e-mail ou link | `email`, `url` | `unique` se o valor precisar ser exclusivo |
| Foto ou arquivo | `image`, `file` | `upload_to` relativo a `media`, como `"instructors/"` |
| Escolher um registro de outro modelo | `fk` | `to` e `on_delete` |
| Selecionar vários registros | `m2m` | `to` e, se vazio for permitido, `"blank": true` |

Use `"profile": true` em `image` para gerar a miniatura na lista. `blank` permite deixar o campo vazio no formulário. `null` permite `NULL` no banco. Para data, número ou chave estrangeira opcionais, defina ambos como `true`. Para texto opcional, em geral basta `blank`. O JSON usa aspas duplas e valores `true`, `false` e `null` em minúsculas. Para opções fixas, use `"choices": [["A", "Ativo"], ["I", "Inativo"]]`.

### Relacionar com outros apps

Em `to`, escreva `"app.Modelo"` com a classe exatamente como está no esquema ou no projeto. No ZIP da aula, os apps existentes podem ser usados como alvos. Por exemplo, adicione um campo como `{"name": "member", "type": "fk", "to": "members.Member"}` ou `{"name": "plan", "type": "fk", "to": "plans.Plan"}`. O formulário mostra os registros já cadastrados no modelo alvo.

A regra padrão é `PROTECT`. Use `CASCADE` se excluir o alvo deve excluir também os registros dependentes. `RESTRICT` restringe a exclusão. `SET_NULL` mantém o registro dependente e zera o vínculo, exigindo `"null": true`. Para poder editar o registro e deixar a seleção vazia no formulário, adicione `"blank": true`.

Se houver duas chaves para o mesmo modelo, dê nomes de campo diferentes, como `teacher` e `substitute`. O gerador cria nomes reversos distintos se necessário. Se informar `related_name` à mão, use um valor diferente para cada relação que aponta para o mesmo alvo. Evite inventar um campo `teacher_id` ao lado de uma chave estrangeira `teacher`, pois o Django já cria esse atributo.

### Preencher pelo assistente interativo

Se preferir responder no terminal, use `crud-genifsp wizard --migrate` no lugar de `example` e `generate`. O assistente gera o código e salva as respostas em `schema.json`. Para reproduzir o exercício original, informe 2 apps, as pastas `instructors` e `courses` e as classes `Instructor` e `Course`. Informe 2 campos para `Instructor` e 3 para `Course`.

| Modelo | Campo | Tipo digitado | Opções da resposta |
| --- | --- | --- | --- |
| `Instructor` | `name` | `char` | Comprimento `150`, opcional `n` |
| `Instructor` | `photo` | `image` | Pasta `instructors/`, miniatura `s`, opcional `n` |
| `Course` | `name` | `char` | Comprimento `150`, opcional `n` |
| `Course` | `description` | `text` | Opcional `n` |
| `Course` | `instructor` | `fk` | Alvo `instructors.Instructor`, exclusão `PROTECT`, opcional `n` |

Para acrescentar apps diferentes ao mesmo projeto, use `crud-genifsp wizard --schema novos.json --migrate`. Com JSON, faça um novo esquema contendo só os apps que quer acrescentar. Use `to` para apontar para os modelos anteriores. Se o enunciado pedir mudar os campos de um app já gerado, edite o código desse app e crie novas migrações. Em um ensaio que possa recomeçar, extraia o ZIP novamente e gere a versão corrigida do esquema em uma pasta limpa.

## 4. Diagnosticar o que pode dar errado

| Situação | Como resolver |
| --- | --- |
| Não acha `manage.py` | Abra o CMD dentro da pasta do projeto extraído. Confirme com `dir manage.py` e use `--output .` nessa pasta. |
| App ou esquema já existe | Use outro nome para um arquivo de esquema novo. Para repetir o exercício com os mesmos apps, use uma extração limpa. O gerador preserva os apps já criados. |
| Campo reservado | Use nomes de campo diferentes de `id`, `pk`, `save` e `delete`. |
| Erro de JSON | Rode `python -m json.tool schema.json`. Confira vírgulas, aspas duplas, listas e chaves. |
| Relação inexistente | Confira `to` e o nome real da classe. O gerador aceita modelos do esquema atual, de gerações anteriores e modelos locais da aula declarados diretamente em `models.py` como subclasses de `models.Model`. Modelos de pacotes externos ou com configuração personalizada podem exigir integração à mão. |
| A lista de instrutores no curso está vazia | Cadastre um instrutor primeiro. Com duas relações novas circulares e obrigatórias, o primeiro cadastro precisa de um fluxo próprio ou de dados iniciais. Torne um vínculo opcional apenas se o enunciado permitir. |
| Migração falhou depois da geração | Os arquivos podem já ter sido criados. Leia a mensagem do Django, corrija a causa e rode `python manage.py makemigrations` seguido de `python manage.py migrate`. |
| Usou `generate` sem `--migrate` | Execute `python manage.py makemigrations` e `python manage.py migrate` antes de testar. |
| As rotas retornam 404 | Confirme o projeto em execução e confira `setup/urls.py`. O exercício usa `/instructors/` e `/courses/`. Se renomeou o app, use a nova pasta no URL. |
| O projeto usa configuração fora do padrão do ZIP | A integração direta espera `manage.py`, `settings.py` e `urls.py` no layout padrão, com `INSTALLED_APPS` e `urlpatterns` em listas ou tuplas literais. Em layouts com configurações dinâmicas, registre os apps e rotas conforme o projeto. |
| O enunciado pede um comportamento específico | Regras de negócio, autenticação nas páginas públicas, filtros personalizados, relação um a um e modelos intermediários próprios exigem adaptação em Django. O gerador cobre os tipos da tabela. |

O menu das páginas geradas liga os novos apps. Se o enunciado exigir atalhos no menu original do clube, acrescente links em `members/templates/navbar.html`, como `<a href="{% url 'instructors:instructors' %}">Instrutores</a>`. Os arquivos enviados permanecem na pasta de mídia após excluir um registro, que é o comportamento padrão do Django.

Se o enunciado pedir um projeto **separado**, fora da pasta da aula, você pode usar `crud-genifsp generate schema.json --output prova --migrate`. Entre em `prova` antes de rodar `python manage.py runserver`. Para integrar ao ZIP da aula, continue usando `--output .`.

## 5. Checklist de entrega

- [ ] Nomes dos apps, modelos, campos e relações conferidos com o enunciado.
- [ ] `python manage.py check` passou e as migrações foram aplicadas.
- [ ] Cadastro, listagem, detalhes, edição e exclusão testados em cada app.
- [ ] Upload testado se houver campo de imagem ou arquivo.
- [ ] Opções de relações aparecem no formulário e os detalhes mostram o vínculo.
- [ ] `members` e `plans` continuam no mesmo projeto da aula.
