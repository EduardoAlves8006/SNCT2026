from django import forms
from django.conf import settings

from .models import Anexo, Area, Cartao, Evento, Submissao, areas_do_usuario


class EventoForm(forms.ModelForm):
    """Formulário de evento do painel.

    A lista de áreas é reduzida às áreas do usuário no __init__. Isso não é
    só cosmético: é essa mesma queryset que o Django usa para validar o POST,
    então um envio manual com o id de outra área é recusado.
    """

    link_inscricao = forms.URLField(
        label="Link de inscrição desta atividade",
        required=False,
        # Sem isso, colar o endereço sem o "https://" viraria http.
        assume_scheme="https",
        widget=forms.URLInput(attrs={"placeholder": "https://suap.ifro.edu.br/..."}),
        help_text="Só quando esta atividade tem inscrição separada. Em branco, "
        "o cronograma usa o link do curso/área.",
    )

    class Meta:
        model = Evento
        fields = [
            "titulo",
            "area",
            "data",
            "hora_inicio",
            "hora_fim",
            "local",
            "descricao",
            "link_inscricao",
        ]
        # Curtos porque os três ficam lado a lado numa linha só: os rótulos
        # longos quebravam em duas linhas e desalinhavam os campos.
        labels = {"hora_inicio": "Início", "hora_fim": "Término"}
        widgets = {
            # type="date" e type="time" fazem o navegador (e o celular) abrirem
            # o seletor nativo; o format é o que o input espera receber de volta.
            "data": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "hora_inicio": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "hora_fim": forms.TimeInput(attrs={"type": "time"}, format="%H:%M"),
            "titulo": forms.TextInput(attrs={"placeholder": "Ex.: Palestra sobre Inteligência Artificial"}),
            "local": forms.TextInput(attrs={"placeholder": "Ex.: Auditório"}),
            "descricao": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        areas = areas_do_usuario(user)
        campo_area = self.fields["area"]
        campo_area.queryset = areas

        # Quem cuida de uma única área não precisa escolher nada: o campo vira
        # oculto e o template mostra o nome da área como texto.
        self.area_unica = areas[0] if len(areas) == 1 else None
        if self.area_unica:
            campo_area.initial = self.area_unica
            campo_area.widget = forms.HiddenInput()
        else:
            campo_area.empty_label = "Escolha o curso/área"


class InscricaoDaAreaForm(forms.ModelForm):
    """Os dois campos da inscrição, para a coordenação mexer pelo painel.

    Quem pode mexer em qual área é decidido na view, não aqui: este formulário
    sempre recebe uma área que já passou pela checagem de permissão.
    """

    link_inscricao = forms.URLField(
        label="Link de inscrição",
        required=False,
        # Sem isso, colar "suap.ifro.edu.br/..." sem o "https://" viraria http.
        assume_scheme="https",
        widget=forms.URLInput(
            attrs={"placeholder": "https://suap.ifro.edu.br/eventos/inscricao/1/0000/"}
        ),
        help_text="Cole aqui o endereço da inscrição no SUAP.",
    )

    class Meta:
        model = Area
        fields = ["inscricoes_abertas", "link_inscricao"]
        labels = {"inscricoes_abertas": "Inscrições abertas"}
        help_texts = {
            "inscricoes_abertas": "Desmarcado, o site mostra “Inscrições em breve”.",
        }


class SubmissaoForm(forms.ModelForm):
    """Submissão de trabalhos, no painel.

    Quem pode mexer é decidido na view: a submissão é uma só para o evento
    inteiro, então ela é da organização, não de uma coordenação.
    """

    link = forms.URLField(
        label="Link da submissão",
        required=False,
        # Sem isso, colar o endereço sem o "https://" viraria http.
        assume_scheme="https",
        widget=forms.URLInput(attrs={"placeholder": "https://forms.gle/..."}),
        help_text="Cole aqui o endereço do formulário de envio dos trabalhos.",
    )

    class Meta:
        model = Submissao
        fields = ["aberta", "link", "prazo"]
        labels = {"aberta": "Submissão aberta", "prazo": "Prazo de envio"}
        help_texts = {
            "aberta": "Desmarcada, o site mostra “A submissão abre em breve”.",
            "prazo": "Opcional. Em branco, a página não fala em prazo.",
        }
        widgets = {
            # type="date" abre o seletor nativo, inclusive no celular.
            "prazo": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }


class CartaoForm(forms.ModelForm):
    """Um cartão da página inicial. Só o administrador chega aqui.

    O texto é gravado como texto puro: o template escapa tudo na hora de
    mostrar, então digitar HTML aqui não vira marcação no site.
    """

    class Meta:
        model = Cartao
        fields = [
            "titulo",
            "area",
            "trilha",
            "responsavel",
            "coordenacao",
            "descricao",
            "programacao_rotulo",
            "programacao",
            "link_horarios",
            "ordem",
            "publicado",
        ]
        widgets = {
            "titulo": forms.TextInput(
                attrs={"placeholder": "Ex.: Biologia — Oficinas e Demonstrações"}
            ),
            "trilha": forms.TextInput(attrs={"placeholder": "Ex.: Abertura oficial"}),
            "responsavel": forms.TextInput(attrs={"placeholder": "Nome do professor"}),
            "coordenacao": forms.TextInput(
                attrs={"placeholder": "Ex.: Coordenação de Biologia"}
            ),
            "descricao": forms.Textarea(attrs={"rows": 4}),
            "programacao_rotulo": forms.TextInput(attrs={"placeholder": "29 e 30/10"}),
            "programacao": forms.Textarea(
                attrs={"rows": 6, "placeholder": "Oficinas práticas\nDemonstrações\nVisitações"}
            ),
            "link_horarios": forms.URLInput(
                attrs={"placeholder": "https://exemplo.github.io/pagina-do-curso/"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["area"].queryset = Area.objects.filter(ativo=True)
        self.fields["area"].empty_label = "Escolha o curso/área"


class AnexoForm(forms.ModelForm):
    """Um documento da página de submissão. Só o administrador chega aqui."""

    link = forms.URLField(
        label="Link",
        required=False,
        # Sem isso, colar o endereço sem o "https://" viraria http.
        assume_scheme="https",
        widget=forms.URLInput(attrs={"placeholder": "https://drive.google.com/..."}),
        help_text="Para um documento que já está publicado em outro lugar. "
        "Deixe em branco se enviou um arquivo.",
    )

    class Meta:
        model = Anexo
        fields = ["titulo", "descricao", "arquivo", "link", "texto", "ordem", "publicado"]
        widgets = {
            "titulo": forms.TextInput(attrs={"placeholder": "Ex.: Regulamento"}),
            "descricao": forms.TextInput(
                attrs={"placeholder": "Ex.: Regras de formatação e critérios de avaliação"}
            ),
            "texto": forms.Textarea(
                attrs={
                    "rows": 16,
                    "placeholder": "## Das disposições gerais\n\n"
                    "Escreva aqui o texto do documento.\n\n"
                    "- um item de lista\n- outro item",
                }
            ),
        }

    def clean_arquivo(self):
        arquivo = self.cleaned_data.get("arquivo")
        # `size` só existe no arquivo recém-enviado; no que já está gravado o
        # campo volta como FieldFile e não há nada para conferir.
        tamanho = getattr(arquivo, "size", None)
        if tamanho and tamanho > settings.TAMANHO_MAXIMO_ANEXO:
            limite = settings.TAMANHO_MAXIMO_ANEXO // (1024 * 1024)
            raise forms.ValidationError(
                f"O arquivo tem {tamanho / (1024 * 1024):.1f} MB e o limite é "
                f"{limite} MB. Comprima o PDF ou publique em outro lugar e use o link."
            )
        return arquivo
