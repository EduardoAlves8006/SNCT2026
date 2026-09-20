# 23ª SNCT — IFRO Campus Ariquemes

Site da 23ª Semana Nacional de Ciência e Tecnologia do IFRO Campus Ariquemes,
com cronograma gerenciado pelas próprias coordenações.

Aplicação Django + PostgreSQL, em container, sob o domínio
**snctifroari.online**. Sobe com um `docker compose up -d`.

```
                    SNCT IFRO
                       │
              ┌────────┴────────┐
              │                 │
           Público          Coordenação
              │                 │
              ▼                 ▼
     /  e  /cronograma/      /painel/
              └────────┬────────┘
                       ▼
                     Django
                       ▼
                   PostgreSQL
```

## O que tem

| Endereço | Quem entra | Para quê |
|---|---|---|
| `/` | qualquer um | página da semana (a mesma de sempre) |
| `/cronograma/` | qualquer um | cronograma, dia por dia, vindo do banco |
| `/painel/` | coordenações | cadastrar os eventos das próprias áreas e abrir/fechar a inscrição delas |
| `/painel/submissao/` | só o administrador | link e prazo da submissão de trabalhos |
| `/painel/cartoes/` | só o administrador | os sete cartões da seção Eventos |
| `/admin/` | só o administrador | contas, cursos/áreas e todos os eventos |

A permissão é por **curso/área**. Uma conta de coordenação pode cuidar de uma
ou de várias áreas, e só mexe nos eventos delas. A checagem é feita no
servidor: pedir pela URL o evento de outra área devolve 404, mesmo que o botão
não apareça na tela.

---

## Rodar na sua máquina

Precisa de Python 3.12 ou mais novo. A imagem de produção usa 3.13.

```bash
git clone https://github.com/PolarIF/SNCT2026.git
cd SNCT2026

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env               # e edite: gere uma SECRET_KEY, deixe DEBUG=1

python manage.py migrate
python manage.py createsuperuser   # essa é a sua conta de administrador
python manage.py runserver
```

Abra <http://127.0.0.1:8000/>.

Sem a variável `DATABASE_URL`, o projeto usa um arquivo SQLite (`db.sqlite3`) —
o suficiente para desenvolver. A migração inicial já cria os cursos/áreas que
apareciam na página: Geral, CIEEC, Agronomia e Agropecuária, Alimentos,
Informática, Biologia e Medicina Veterinária.

### Rodar os testes

```bash
python manage.py test
```

São 56 testes, a maioria sobre permissão: o que cada tipo de conta consegue e
não consegue fazer, inclusive por POST direto na URL. Também cobrem o estado
das inscrições na página inicial e o filtro do cronograma.

---

## Primeiros passos como administrador

Depois do `createsuperuser`, entre em `/admin/`.

### 1. Conferir os cursos/áreas

**Cursos/áreas** → a lista já vem preenchida. Renomeie, desative ou acrescente
o que faltar. Desativar esconde a área do site sem apagar os eventos dela.

### 2. Criar a conta de uma coordenação

**Usuários → Adicionar usuário**:

- **Usuário**: algo simples, tipo `coord_informatica`
- **Senha**: defina uma e passe para a coordenação
- **Cursos/áreas que esta conta pode administrar**: marque as áreas dela

Deixe **is_superuser** e **is_staff** desmarcados. Coordenação não usa o
`/admin/` — ela usa o `/painel/`.

### 3. Dar mais uma área para uma conta existente

Dois caminhos, tanto faz:

- **Usuários** → abra a conta → marque a área a mais; ou
- **Cursos/áreas** → abra a área → acrescente a pessoa em "quem pode administrar".

### 4. Abrir a inscrição de um curso/área

Isso **quem faz é a própria coordenação**, no painel — não precisa passar por
você. Em `/painel/`, no bloco "Inscrições", ela clica em *Alterar* na área
dela, marca **inscrições abertas** e cola o link do SUAP. O cartão daquele
curso na página inicial troca na hora o "Inscrições em breve" pelo botão
vermelho "Inscreva-se".

Você também alcança isso em **Cursos/áreas**, para qualquer área, e a coluna
"inscrições abertas" é editável direto na lista — dá para abrir ou fechar as
sete de uma vez.

Sem link, a caixa marcada só mostra o selo "Inscrições abertas" e nenhum
botão — de propósito, para não gerar link quebrado. O painel avisa isso com
"Falta o link".

### 5. Abrir a submissão de trabalhos

A submissão é **uma só para a semana inteira** — não é por curso nem por
evento —, então quem mexe nela é você, e não as coordenações. Em `/painel/`,
no bloco "Submissão de trabalhos", clique em *Alterar*, marque **submissão
aberta** e cole o link do formulário. O prazo é opcional: preenchido, a página
mostra "Envios até …"; em branco, não fala em prazo.

É a primeira seção da página inicial. Enquanto estiver fechada, ela mostra
"A submissão abre em breve" no lugar do botão — a seção não some, para quem
chega saber que vai existir.

Uma coordenação que digite `/painel/submissao/` na barra de endereços recebe
404: a checagem é no servidor, não em esconder o bloco da tela.

### 6. Editar os cartões da página inicial

Os sete cartões da seção **Eventos** também são dados: título, etiqueta,
responsável, descrição e a programação resumida. Em `/painel/` há o atalho
**Cartões da página inicial** — só você o vê; uma coordenação que digite
`/painel/cartoes/` recebe 404.

Algumas coisas que vale saber:

- **Programação**: um item por linha. Sem nenhuma linha, o cartão não mostra a
  lista recolhida.
- **Etiqueta**: é o selo verde do alto. Em branco, usa o nome do curso/área —
  serve para casos como “Abertura oficial”, que não é o nome de nenhum curso.
- **Responsável** em branco vira “a confirmar” no site.
- **Link dos horários**: em branco, o botão “Ver horários” leva ao cronograma
  do site, filtrado por aquele curso. Preenchido, leva ao endereço informado e
  abre em outra aba — é o caso do IFROmatizando, que publica a programação em
  página própria.
- **Ordem**: menor primeiro. É por ela que se reordena a grade.
- **Publicado**: desmarcado, o cartão sai do site sem ser apagado.
- O **botão de inscrição não se define aqui** — ele vem do curso/área escolhido
  no cartão, e quem controla isso é a coordenação (passo 4).
- O texto é gravado como texto: digitar HTML ali aparece como HTML no site, em
  vez de virar negrito. A única exceção é a palavra *Campus*, que o site põe em
  itálico sozinho.

### 7. Desativar uma conta

**Usuários** → abra a conta → desmarque **Ativo**. Ela deixa de conseguir
entrar, e os eventos que cadastrou continuam no lugar.

### 8. Trocar uma senha

**Usuários** → abra a conta → no campo de senha, clique no link para definir
uma nova.

---

## Colocar no ar

O site roda em container. Quem administra o servidor tem o passo a passo
completo em **[IMPLANTACAO.md](IMPLANTACAO.md)** — em resumo:

```bash
git clone https://github.com/PolarIF/SNCT2026.git
cd SNCT2026
cp .env.producao.exemplo .env    # preencher
docker compose up -d --build
```

Sobem três containers: a aplicação, o PostgreSQL e um proxy que resolve o
certificado HTTPS sozinho. As migrações rodam no início de cada container e a
primeira conta de administrador é criada a partir do `.env`, então não é
preciso rodar nada à mão no servidor depois.

Para atualizar: `git pull && docker compose up -d --build`.

## Estrutura

```
manage.py
requirements.txt
.env.example             modelo do .env de desenvolvimento

Dockerfile               a imagem da aplicação
docker-compose.yml       aplicação + PostgreSQL + proxy com HTTPS
Caddyfile                o proxy: certificado automático
scripts/entrypoint.sh    migra e garante o administrador a cada boot
.env.producao.exemplo    modelo do .env do servidor
IMPLANTACAO.md           passo a passo para quem administra o servidor

config/
  settings.py            tudo que varia entre máquinas vem de variável de ambiente
  urls.py

eventos/
  models.py              Area, Evento, Submissao, Cartao e areas_do_usuario()
  views.py               site público e painel (@so_administrador fecha o que é só seu)
  forms.py               formulários do painel
  admin.py               Django Admin, incluindo o campo de áreas no usuário
  templatetags/snct.py   |campus, que põe a palavra Campus em itálico
  management/commands/   criar_admin: a conta inicial, a partir do .env
  tests.py               91 testes, sobretudo de permissão
  migrations/
    0001_initial.py
    0002_areas_iniciais.py         cria os cursos/áreas da semana
    0003_inscricao_por_area.py     link e estado da inscrição
    0004_submissao_de_trabalhos.py a submissão, uma linha só
    0005_cartoes_da_home.py        os sete cartões, com o texto que já estava no ar
    0006_link_de_horarios_proprio.py  horários fora do site, por cartão

templates/
  base.html              cabeçalho, rodapé e meta tags do site público
  index.html             a página da semana
  cronograma.html        o cronograma público
  painel/                as telas da coordenação e do administrador

static/
  css/style.css          o site
  css/painel.css         o painel
  js/site.js             contagem de dias, realce do menu, sombra do topo
  img/                   marca do IFRO em SVG, favicon, imagem de compartilhamento

marca-ifro/              PNGs e PDF originais da marca (não são servidos)
.impeccable.md           as decisões de design da página pública
```

### Onde está a regra de permissão

Em um lugar só: `areas_do_usuario()`, em `eventos/models.py`. As views e o
formulário chamam essa função, então mudar a regra é mudar uma função.

- **Listar** — `Evento.objects.filter(area__in=areas_do_usuario(user))`
- **Criar/editar** — o campo de área do formulário só aceita essas áreas, e é a
  mesma queryset que valida o POST
- **Editar/excluir** — `get_object_or_404(..., area__in=areas_do_usuario(user))`
- **Inscrição** — `get_object_or_404(areas_do_usuario(user), slug=slug)`
- **Submissão de trabalhos e cartões da home** — valem para o evento inteiro,
  então a porta é o decorador `@so_administrador`: quem não é superusuário
  recebe 404, no GET e no POST
- **Administrador** — `is_superuser` recebe todas as áreas ativas

---

## Sobre a página pública

A página inicial é o template `templates/index.html`, com o cabeçalho e o
rodapé em `base.html` para não ficarem duplicados no cronograma.

A ordem das seções é:

1. **herói** — data, tema e contagem regressiva;
2. **Submissão de trabalhos** (`#trabalhos`) — a primeira seção: faixa escura
   inteira, separada do herói por um fio vermelho, com um cartão claro à
   direita. O cartão mostra o prazo em corpo grande quando há data, e o
   estado (“Em breve”/“Aberta”) quando não há. Link e prazo vêm do banco;
3. **Programação geral** (`#programacao`) — os quatro dias, em três cartões;
4. **Eventos** (`#eventos`) — abre com o bloco **Como se inscrever**
   (`#inscrever`, três passos, sempre visível) e depois os cartões, que vêm
   do banco (`Cartao`) e se editam em `/painel/cartoes/`;
5. **Sobre** (`#sobre`).

Nada do que aparece nessas seções depende de reimplantação, exceto o texto:
os dois estados que mudam durante a semana — inscrição por área e submissão de
trabalhos — são dados, e se mexem pelo painel.

Ainda falta preencher:

- o **responsável** de 6 dos 7 cartões — agora em `/painel/cartoes/`, sem
  precisar de reimplantação;
- o **contato da comissão organizadora**, que continua sendo texto fixo em
  `templates/index.html` (`grep -n "a confirmar" templates/index.html`).

Os links de inscrição **não** ficam mais no HTML: são cadastrados em
/admin/ → Cursos/áreas, um por curso/área.

### A marca do IFRO

Os SVGs em `static/img/ifro-*.svg` foram extraídos do PDF vetorial oficial do
campus (`marca-ifro/Logotipo IFRO - Ariquemes.pdf`), então são a marca de
verdade. O símbolo isolado (`if-mark.svg`) foi reconstruído com a geometria
medida nesse mesmo arquivo: grade 3×4, célula 100, vão 20, canto com 9,7% do
lado.

Cores oficiais: verde `#39A048`, vermelho `#CD2027`.

---

## Segurança

O que está ligado quando `DEBUG=0`:

- senhas com o hasher do Django (PBKDF2) e os validadores padrão;
- sessão por cookie, com `Secure` e CSRF em todo formulário;
- HTTPS obrigatório, atrás do proxy do Railway (`X-Forwarded-Proto`);
- HSTS por 30 dias, `nosniff`, `X-Frame-Options: DENY`;
- `ALLOWED_HOSTS` fechado: requisição com outro `Host` recebe 400;
- autorização no servidor, e não em esconder botões;
- conta desativada não entra.

`manage.py check --deploy` passa com um aviso só, o de `SECURE_HSTS_PRELOAD`.
Está desligado de propósito: entrar na lista de preload dos navegadores é
difícil de desfazer, e não vale para um site de uma semana de evento.
