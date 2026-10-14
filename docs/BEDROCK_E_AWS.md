# Credenciais, Bedrock e AWS

Depois da troca do assistente pela Cora, a AWS entra no projeto em dois
lugares, e só um deles é necessário para a demo.

| Onde | Para quê | Obrigatório? | Credencial vai em |
|---|---|---|---|
| **Kit da Cora** | O modelo da Cora (Claude Sonnet 5.5 no Bedrock) conversa e chama as ferramentas do MVP | **Sim**, para a conversa | Terminal ou `.env` **do kit da Cora** |
| **MVP** | Resumo em texto da página DNA (`llm.py`) | Não: sem Bedrock, o resumo sai por regras | Terminal do MVP, com `DNA_USE_BEDROCK=1` |

O MVP **não precisa de nenhuma credencial**: as análises rodam localmente e o
servidor de ferramentas (`/mcp`) não tem login. Passo a passo da Cora:
[CORA.md](CORA.md).

## 1. A credencial da Cora (obrigatória para conversar)

- **Normalmente vem dos organizadores** junto com o kit. O zip do kit que
  recebemos só tinha código, sem `.env`: confirme com eles.
- A conta precisa ter acesso ao modelo `us.anthropic.claude-sonnet-5-5` na
  região do kit (padrão `us-east-2`; muda com `BEDROCK_REGION`).
- Exporte **antes** de subir o kit:
  ```bash
  export AWS_ACCESS_KEY_ID=...  AWS_SECRET_ACCESS_KEY=...  AWS_SESSION_TOKEN=...
  docker compose up -d --build        # na pasta do kit
  ```
- Teste rápido: mande "oi" no chat da Cora. Se der erro de acesso, é a
  credencial, a região ou o modelo não liberado na conta.
- No hackathon, a Cora roda com `AUTH_BYPASS=true`: **não há login nem
  credencial da Cora**. Isso só é aceito em ambiente local; por isso não se
  publica a Cora do kit na internet.

## 2. O Bedrock do MVP (opcional, só o resumo da página DNA)

### O que foi e o que NÃO foi verificado

| Verificado | Resultado |
|---|---|
| O resumo chama o Bedrock e **cai para regras** se falhar | Testado |
| `make bedrock-check` falha **dizendo o que consertar** quando não há credenciais | Rodado: `NoCredentialsError` com a instrução |
| `make demo-ready` sobe **sem** Bedrock por padrão e só o testa com `DNA_USE_BEDROCK=1` | Script ajustado e com sintaxe conferida; **não rodado** aqui (sem Docker neste ambiente) |
| O texto enviado ao modelo **não leva dado pessoal** | Testado com um cliente simulado que captura o prompt |

**Não verificado:** nenhuma chamada **real** ao Bedrock a partir do MVP.

### Como ligar

```bash
export DNA_USE_BEDROCK=1 AWS_REGION=us-east-1 BEDROCK_MODEL_ID=<ID do console>
export AWS_ACCESS_KEY_ID=...  AWS_SECRET_ACCESS_KEY=...  AWS_SESSION_TOKEN=...
make demo-ready        # sobe, testa o Bedrock, aquece o cache dos resumos, confere o /mcp e roda o pré-voo
```

O padrão do projeto é `us.anthropic.claude-haiku-4-5-20251001-v1:0` em
`us-east-1`. Basta uma chamada simples (o resumo **não** usa ferramentas).
Política mínima (não testada aqui):

```json
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["bedrock:InvokeModel"],
  "Resource":["arn:aws:bedrock:*::foundation-model/anthropic.*","arn:aws:bedrock:*:*:inference-profile/*"]}]}
```

**Sem `make`** (Windows sem WSL):

```bash
docker compose up -d --build
docker compose exec -T backend python backend/scripts/bedrock_check.py
docker compose exec -T backend python backend/scripts/bedrock_warm.py
docker compose exec -T -e DEMO_BASE_URL=http://frontend:8080 -e DEMO_REQUIRE_BEDROCK=1 backend python backend/scripts/preflight.py
```

Se a máquina usa perfil ou SSO em vez de chaves:
`AWS_PROFILE=meu-perfil docker compose -f compose.yaml -f compose.aws.yaml up -d --build`
(monta `~/.aws` só para leitura; prefira credenciais temporárias exportadas).

### Diagnóstico: erro, causa e correção

| O diagnóstico diz | Causa | Correção |
|---|---|---|
| `NoCredentialsError` | O container não vê credenciais | Exportar as variáveis **antes** do `up`, ou usar `compose.aws.yaml` |
| `ExpiredToken...` | Credencial temporária venceu | Gerar nova e subir de novo |
| `UnrecognizedClientException` | Chave errada, ou de outra conta | Conferir as chaves |
| `AccessDeniedException` | Sem permissão, ou modelo não habilitado | Política com `bedrock:InvokeModel` e habilitar o modelo no console, na região |
| `ValidationException` (perfil de inferência) | O modelo exige perfil | Usar o ID com prefixo de região (`us.anthropic...`) |
| `ValidationException` (ID) | ID inválido | Copiar o ID exato do console |
| `ResourceNotFoundException` | Modelo não existe nesta região | Conferir `AWS_REGION` e `BEDROCK_MODEL_ID` |
| `ThrottlingException` | Limite de requisições | Esperar; usar o cache |
| `EndpointConnectionError` | Sem rede até a AWS | Internet, proxy, VPN |

Se o motivo não estiver na tabela, leia a linha `detalhe:` que o
`bedrock_check` imprime: ela traz a mensagem original da AWS. A mesma tabela
serve para erros da Cora, que usa o mesmo serviço.

### Cache dos resumos

- `make bedrock-warm` grava no cache os resumos das máquinas da demo. Com o
  cache aquecido, o resumo continua aparecendo se a rede da AWS falhar.
- O cache mora no volume `dna_cache`. `make down` o preserva;
  **`docker compose down -v` o apaga**.

## Privacidade: o que vai para a AWS

- **Pela Cora:** o modelo da Cora recebe o resultado das ferramentas `dna_*`,
  calculado sobre a base **mascarada** e mascarado de novo na saída
  (telefone, e-mail, CPF e CEP viram `[telefone]` etc.). Recebe também o
  contexto da tela (série em foco, melhorias cadastradas).
- **Pelo resumo do MVP (se ligado):** fatos de uma máquina e o texto do
  técnico, também da cópia mascarada.
- Nomes próprios e endereços por extenso **não** são detectados.
- Os dados reais do desafio só podem ser usados no evento (Art. 37). Use a
  **conta AWS do evento ou da organização**, nunca uma conta pessoal, sem
  confirmar com eles.

## Segurança

- Nunca grave credenciais em arquivo do projeto nem faça commit delas.
  `.env` está no `.gitignore`. Não cole credenciais no chat do Kiro.
- Os scripts não imprimem chaves nem tokens.
- **Não publique nada na internet:** a API e o `/mcp` do MVP não têm
  autenticação, e a Cora do kit roda com `AUTH_BYPASS` (qualquer visitante
  vira administrador). Demonstre a partir do notebook.
