from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify


class Area(models.Model):
    """Curso ou área que tem eventos na semana.

    A área é também a unidade de permissão: uma conta de coordenação
    administra os eventos das áreas ligadas a ela em `gestores`.
    """

    nome = models.CharField("nome", max_length=80, unique=True)
    slug = models.SlugField(
        "endereço curto",
        max_length=80,
        unique=True,
        blank=True,
        help_text="Preenchido automaticamente a partir do nome.",
    )
    ativo = models.BooleanField(
        "ativo",
        default=True,
        help_text="Desmarque para esconder a área sem apagar os eventos dela.",
    )
    # Inscrição: é por área, e quem controla é a organização, pelo /admin/.
    # Ficam aqui e não no HTML porque mudam durante a semana e o site roda em
    # container — mexer no template exigiria reconstruir e reimplantar.
    inscricoes_abertas = models.BooleanField(
        "inscrições abertas",
        default=False,
        help_text="Desmarcado, a página mostra “Inscrições em breve”.",
    )
    link_inscricao = models.URLField(
        "link de inscrição",
        max_length=300,
        blank=True,
        help_text="Endereço da inscrição no SUAP. Sem ele não aparece botão, "
        "mesmo com as inscrições marcadas como abertas.",
    )

    gestores = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name="quem pode administrar",
        related_name="areas_geridas",
        blank=True,
    )

    class Meta:
        verbose_name = "curso/área"
        verbose_name_plural = "cursos/áreas"
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nome)[:80]
        super().save(*args, **kwargs)

    @property
    def mostra_botao_inscricao(self):
        """Só há botão quando as inscrições estão abertas e há para onde ir."""
        return bool(self.inscricoes_abertas and self.link_inscricao)

    @property
    def situacao_inscricao(self):
        """O que o cartão desta área mostra hoje na página inicial.

        Fica no modelo porque o /admin/ e o painel dizem a mesma coisa, e
        dizer diferente seria pior que não dizer.
        """
        if self.mostra_botao_inscricao:
            return "botão “Inscreva-se”"
        if self.inscricoes_abertas:
            return "marcada como aberta, mas sem link — nenhum botão aparece"
        return "“Inscrições em breve”"


class EventoQuerySet(models.QuerySet):
    def publicos(self):
        """O que aparece no cronograma do site."""
        return self.filter(area__ativo=True).select_related("area")


class Evento(models.Model):
    titulo = models.CharField("título", max_length=160)
    descricao = models.TextField(
        "descrição",
        blank=True,
        help_text="Uma ou duas frases sobre a atividade.",
    )
    data = models.DateField("data")
    hora_inicio = models.TimeField("horário de início")
    hora_fim = models.TimeField("horário de término", null=True, blank=True)
    local = models.CharField("local", max_length=120, blank=True)
    area = models.ForeignKey(
        Area,
        verbose_name="curso/área",
        on_delete=models.PROTECT,
        related_name="eventos",
    )

    criado_em = models.DateTimeField("cadastrado em", auto_now_add=True)
    atualizado_em = models.DateTimeField("última alteração", auto_now=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="cadastrado por",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="eventos_criados",
    )

    objects = EventoQuerySet.as_manager()

    class Meta:
        verbose_name = "evento"
        verbose_name_plural = "eventos"
        ordering = ["data", "hora_inicio", "titulo"]
        indexes = [models.Index(fields=["data", "hora_inicio"])]

    def __str__(self):
        return f"{self.data:%d/%m} {self.hora_inicio:%H:%M} — {self.titulo}"

    def clean(self):
        if self.hora_fim and self.hora_inicio and self.hora_fim <= self.hora_inicio:
            raise ValidationError(
                {"hora_fim": "O horário de término tem que ser depois do de início."}
            )

    @property
    def horario(self):
        """"14:00 às 16:00" ou apenas "14:00" quando não há término."""
        inicio = self.hora_inicio.strftime("%H:%M")
        if not self.hora_fim:
            return inicio
        return f"{inicio} às {self.hora_fim:%H:%M}"


class Submissao(models.Model):
    """Submissão de trabalhos: uma só para a semana inteira.

    Não é por evento nem por área — é um link único, o mesmo para todo mundo.
    Por isso existe uma linha só, criada pela migração e carregada por
    `Submissao.atual()`. Mora no banco, e não no HTML, pela mesma razão das
    inscrições: o endereço e o prazo mudam depois de o site já estar no ar.
    """

    aberta = models.BooleanField(
        "submissão aberta",
        default=False,
        help_text="Desmarcada, a página mostra “A submissão abre em breve”.",
    )
    link = models.URLField(
        "link da submissão",
        max_length=300,
        blank=True,
        help_text="Endereço do formulário de envio. Sem ele não aparece botão, "
        "mesmo com a submissão marcada como aberta.",
    )
    prazo = models.DateField(
        "prazo de envio",
        null=True,
        blank=True,
        help_text="Opcional. Sem data preenchida, a página não fala em prazo.",
    )

    class Meta:
        verbose_name = "submissão de trabalhos"
        verbose_name_plural = "submissão de trabalhos"

    def __str__(self):
        return "Submissão de trabalhos"

    def save(self, *args, **kwargs):
        # Uma linha só: qualquer save escreve sempre na mesma.
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def atual(cls):
        """A configuração da submissão, mesmo que a linha ainda não exista.

        Devolver um objeto vazio em vez de None deixa o template simples: ele
        pergunta `submissao.mostra_botao` e pronto, sem checar nulo antes.
        """
        return cls.objects.first() or cls()

    @property
    def mostra_botao(self):
        """Só há botão quando a submissão está aberta e há para onde ir."""
        return bool(self.aberta and self.link)

    @property
    def situacao(self):
        """O que a página inicial mostra hoje na seção de trabalhos."""
        if self.mostra_botao:
            return "botão “Enviar meu trabalho”"
        if self.aberta:
            return "marcada como aberta, mas sem link — nenhum botão aparece"
        return "“A submissão abre em breve”"


class Cartao(models.Model):
    """Um dos cartões de evento da página inicial.

    O que aparece no cartão era HTML fixo no template. Virou dado porque o
    site roda em container num servidor que a organização não administra:
    trocar um título ou um responsável exigiria reconstruir a imagem. Aqui,
    é um formulário no painel.

    O estado da inscrição continua vindo da área (`Area.inscricoes_abertas` e
    `link_inscricao`) — é a coordenação que mexe nisso, e não muda aqui.
    """

    area = models.ForeignKey(
        Area,
        verbose_name="curso/área",
        on_delete=models.PROTECT,
        related_name="cartoes",
        help_text="De onde vêm o botão de inscrição e o link do cronograma.",
    )
    trilha = models.CharField(
        "etiqueta",
        max_length=60,
        blank=True,
        help_text="O selo verde no alto do cartão. Em branco, usa o nome do "
        "curso/área.",
    )
    titulo = models.CharField("título", max_length=160)
    responsavel = models.CharField(
        "responsável",
        max_length=120,
        blank=True,
        help_text="Em branco, o cartão mostra “a confirmar”.",
    )
    coordenacao = models.CharField(
        "coordenação",
        max_length=160,
        blank=True,
        help_text="Vem depois do responsável, ex.: “Coordenação de Biologia”.",
    )
    descricao = models.TextField(
        "descrição",
        help_text="Duas ou três frases sobre o evento.",
    )
    programacao_rotulo = models.CharField(
        "data da programação",
        max_length=40,
        blank=True,
        help_text="Como aparece no cartão, ex.: “27/10” ou “29 e 30/10”.",
    )
    programacao = models.TextField(
        "programação",
        blank=True,
        help_text="Um item por linha. Sem nenhum, o cartão não mostra a lista.",
    )
    ordem = models.PositiveSmallIntegerField(
        "ordem",
        default=0,
        help_text="Menor primeiro. Em empate, vale o título.",
    )
    publicado = models.BooleanField(
        "publicado",
        default=True,
        help_text="Desmarque para tirar o cartão do site sem apagá-lo.",
    )

    class Meta:
        verbose_name = "cartão da página inicial"
        verbose_name_plural = "cartões da página inicial"
        ordering = ["ordem", "titulo"]

    def __str__(self):
        return self.titulo

    @property
    def etiqueta(self):
        """O selo do alto. Sem etiqueta própria, é o nome do curso/área."""
        return self.trilha or self.area.nome

    @property
    def itens_programacao(self):
        """A programação como lista, uma linha por item."""
        return [linha.strip() for linha in self.programacao.splitlines() if linha.strip()]


def areas_do_usuario(user):
    """Áreas que este usuário pode administrar.

    É a única fonte de verdade das permissões — as views e os formulários
    todos passam por aqui, para que a regra não fique espalhada.
    """
    if not user.is_authenticated:
        return Area.objects.none()
    if user.is_superuser:
        return Area.objects.filter(ativo=True)
    return user.areas_geridas.filter(ativo=True)
