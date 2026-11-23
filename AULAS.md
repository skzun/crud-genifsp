# PDFs consultados em D:\PDFs

O PDF `1f5d717fac6f-c5ff0ae684d2434c88bb2e41bbec6c34.pdf` contém
exatamente o Exercício para Prova Final: instructors com name e photo,
courses com name, description e instructor, CRUDs completos e consulta
aos PDFs anteriores. O material recomenda instalar Django e Pillow.

Outros materiais identificados por extração de texto:

| Arquivo | Conteúdo identificado | Aplicação no gerador |
| --- | --- | --- |
| 1e2c1e157a3b-5a551499c37948febeaf8718150003ac.pdf | Reversão de Migrations, Static e FK | Migrações, CSS local e relações entre apps |
| 36ee87606b9f-95f567ecec6442628c0261ee84380bc0.pdf | Bootstrap e CRUD: Insert, Delete e Update | Formulários e operações de cadastro, edição e exclusão |
| 285ec43091bb-9c161663eeb04cd8a4337e48f4fdf023.pdf | QuerySets, barra de pesquisa e paginação | Listagem ordenada com paginação; busca não implementada |
| 018dc9924bb6-21ec1b36227f4a71a4945fa4f44720d6.pdf | Desacoplamento em API e frontend | Contexto adicional; este gerador produz Django com HTML no servidor |

Na aula 8, o exemplo concreto é `members.Member` ligado a `plans.Plan`
por uma ForeignKey. O exercício inverte a perspectiva do cadastro da mesma
maneira: cada curso escolhe um instrutor no formulário. A lista e os detalhes
vêm das aulas de CRUD e templates. O PDF de mídia
`5a17aaa42624-088bc7b715534bf6b4f30f227ec78908.pdf` ensina ImageField,
FileField, pasta media, miniatura na listagem e link para anexos. Por isso
o assistente pergunta pelo tipo do campo, pasta de upload, miniatura e
destino da relação. No exercício, `photo` pode virar foto de perfil na
lista e imagem nos detalhes. O código da aula usa CASCADE para Member e Plan.
O assistente permite escolher a regra e sugere PROTECT para bloquear a
exclusão de um instrutor com cursos, já que o enunciado não fixa essa regra.

O código usa ModelForms e views genéricas do Django para produzir arquivos
editáveis. A aula de Bootstrap menciona CDN; o gerador usa CSS próprio local,
conforme o requisito de funcionar sem CDN. Não foi feita equivalência linha
a linha entre as soluções das aulas e o código gerado.
