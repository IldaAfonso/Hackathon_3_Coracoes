# Guia de design da Karen: DNA da Máquina

## 1. A ideia em uma frase
**Cada máquina tem um DNA, que é a sequência de tudo o que aconteceu com ela.** A metáfora visual é uma
**fita / linha do tempo**: cada chamado é um "gene" colorido pela causa. Melhorias da engenharia são
marcos verticais nessa fita.

## 2. Quem usa e o que precisa ver primeiro
| Persona | Tela | Primeira coisa que o olho deve achar |
|---|---|---|
| Marina (P&D) | Melhoria × impacto | Veredito grande ("Funcionou") + antes → depois |
| P&D (revisão de engenharia) | Melhoria × impacto / Caso bandeja | Um número: **‑28% de vazamentos** |
| Carlos (técnico) | DNA da máquina | Voltas em 90 dias + quais melhorias a máquina tem |
| Rafael (CS) | DNA da máquina | "Esta máquina já teve esse problema?" (sim/não) |

## 3. Telas (wireframes em texto; o app real está em `docs/screens/`)

### 3.1 DNA da máquina (tela-símbolo do projeto)
```
┌─────────────────────────────────────────────────────────────┐
│ [ busca: número de série ......................... 🔍 ]    │
├───────────┬───────────┬───────────┬───────────┬────────────┤
│ Passione  │ Fab. 2022 │ 10        │ 8 voltas  │ Adaptação  │
│ modelo    │ S04       │ chamados  │ em 90 d ⚠ │ hidráulica:│
│           │           │           │           │ NÃO        │
├───────────┴───────────┴───────────┴───────────┴────────────┤
│ Selos: ✅ Bandeja nova (de fábrica)  ➖ O-ring  ➖ Adaptação│
├─────────────────────────────────────────────────────────────┤
│ FITA DO DNA  ●──●────●──────────────●●●─●──●●              │
│              fev  mar                jul  ago               │
│  (cor = causa; borda tracejada = sem registro técnico)      │
├─────────────────────────────────────────────────────────────┤
│ Tabela: data · consumidor disse · técnico escreveu · voltou?│
└─────────────────────────────────────────────────────────────┘
```
Máquina de demonstração: **G5PS000220465809**, com 10 chamados em 7 meses, 6 por vazamento, 4 causas diferentes registradas e nunca recebeu o kit.

### 3.2 Melhoria × impacto
- Topo: seletor de melhoria + texto do boletim.
- Faixa de 4 KPIs: **Antes 19,6% · Depois 14,2% (‑28%) · confiança (p < 0,001) · Veredito**.
- Esquerda: duas barras com intervalo de confiança.
- Direita: barras por **semana de fabricação**, cinza antes do corte e café depois. O degrau é a imagem do pitch.
- Rodapé: "Premissas desta análise" (sanfona).

### 3.3 Duas vozes
Heatmap sintoma (linhas) × causa (colunas). Destacar com anotação as duas células-surpresa:
- "Botões piscando" → contador volumétrico (29%)
- "Máquina vazando" → bico entupido (38%)

### 3.4 Radar
Lista de alertas como **cards** (não tabela) quando for para o pitch: "Luna · Não extrai · +468% nos últimos 3 meses".

### 3.5 Importar base
Área de arrastar .xlsx + relatório de qualidade de dados como "semáforo".

### 3.6 Entrada e áreas
A página inicial tem dois cartões, **P&D** (borda bordô) e **Pós-venda**
(borda laranja), cada um com a pergunta do time e o seu menu. Dentro da área,
o menu mostra um selo com o nome da área. Todas as listas abrem e fecham
(seta laranja, contagem no título).

### 3.7 Fotos dos modelos
O DNA mostra o nome e a **foto do modelo** no topo. Precisamos das fotos
oficiais da **TRES G5 Passione** e da **TRES G4 Luna** (fundo branco ou
transparente, retrato ~4:5), salvas como `passione.webp` e `luna.webp` em
`frontend/public/assets/modelos/`. Enquanto faltarem, aparece uma ilustração
neutra ("G5"/"G4"). A única foto dos materiais do desafio está lá como
`_briefing_confirmar_modelo.webp`: confirmar com os mentores qual modelo é.

### 3.8 Assistente (Cora)
A conversa é a **Cora**, a IA corporativa da 3corações, incorporada num quadro
(iframe) dentro da página. **O visual de dentro do quadro é da Cora** (tema
escuro dela) e não muda com os nossos tokens; o que é nosso é a moldura:
título, texto de apoio, borda do quadro e a seção "Respostas prontas"
abaixo. Para o pitch, o momento visual é o **selo "1 ferramenta"** na
resposta: é a prova de que o número veio do nosso código. Vale um print
com esse selo destacado (seta ou círculo) no slide da demo ou no vídeo de
backup.

## 4. Tokens visuais
| Token | Cor | Uso |
|---|---|---|
| `--cafe` | `#6B3E26` | Primária, "depois", ações |
| `--crema` | `#C8893B` | Destaque secundário, série 2 |
| `--leite` | `#FBF8F4` | Fundo |
| `--espuma` | `#F1EAE2` | Superfícies, sidebar |
| `--grao` | `#2A1F1A` | Texto |
| `--neutro` | `#8A8178` | "Antes", dados de contexto |
| `--alerta` | `#C2410C` | Radar, reincidência |
| `--ok` | `#2F7D4F` | Veredito positivo |

- **Tipografia:** títulos em uma sans geométrica (ex.: *Inter* ou *Source Sans 3*); números/KPIs em *JetBrains Mono* (já usada no material do hackathon), o que reforça "dado de engenharia".
- **Gráficos:** sem grade pesada, rótulo direto na barra, no máximo 2 cores por gráfico + cinza.
- **Acessibilidade:** não depender só de cor no "antes/depois"; usar também rótulo e textura/legenda.

## 5. Identidade do projeto
- Nome: **DNA da Máquina**. Assinatura: *"do chamado à engenharia"*.
- Ícone: hélice dupla formada por dois fios, um café (voz do consumidor) e outro crema (voz do técnico), unidos por "degraus" que são os chamados.
- Não usar marcas da 3corações/TRES como se o app fosse oficial. No pitch, citar "Desafio TRES" é suficiente.

## 6. Deck do pitch (5 min, 8 slides)
Estrutura e falas em `docs/ROTEIRO_PITCH.md`. Diretrizes:
- Um número ou uma imagem por slide. Nada de tabela.
- O slide 4 (o degrau da bandeja) é o centro do pitch. Ele merece o maior cuidado visual.
- Use os prints de `docs/screens/` com moldura de navegador. Para a demo ao vivo, deixe o app aberto na máquina do Cristiano.

## 7. Checklist de entrega da Karen
- [ ] Tokens aplicados (entregar para a Ilza: tabela da seção 4)
- [ ] Ícone/logo do DNA da Máquina (SVG)
- [ ] Deck final (8 slides) a partir do rascunho
- [ ] Mockup da fita do DNA (seção 3.1) caso a Ilza consiga implementar
- [ ] Fotos oficiais dos dois modelos em `frontend/public/assets/modelos/`
- [ ] Vídeo de backup da demo (60–90 s), incluindo uma pergunta à Cora com o selo de ferramenta visível
