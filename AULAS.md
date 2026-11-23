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

Foram encontrados 11 PDFs na pasta. Esta tabela registra apenas os cinco cujo
conteúdo foi identificado na consulta inicial. Os PDFs não são redistribuídos.

O código usa ModelForms e views genéricas do Django para produzir arquivos
editáveis. A aula de Bootstrap menciona CDN; o gerador usa CSS próprio local,
conforme o requisito de funcionar sem CDN. Não foi feita equivalência linha
a linha entre as soluções das aulas e o código gerado.
