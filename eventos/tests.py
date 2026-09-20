"""Testes do que não pode dar errado: quem pode mexer em quê.

Todo teste de permissão aqui bate direto na URL, com POST de verdade. Esconder
o botão na tela não conta — o que conta é o servidor recusar.
"""

from datetime import date, time

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse, reverse_lazy

from .models import Area, Cartao, Evento, Submissao


class Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        # As migrações semeiam as áreas reais da semana e os cartões da página
        # inicial. Os testes montam o próprio cenário, então começam do zero
        # para não depender delas. Os cartões saem primeiro: a área é
        # PROTECT, e é para ser assim — apagar um curso não pode levar junto,
        # em silêncio, o cartão que fala dele.
        Cartao.objects.all().delete()
        Area.objects.all().delete()

        cls.ads = Area.objects.create(nome="ADS", slug="ads")
        cls.info = Area.objects.create(nome="Informática", slug="informatica")
        cls.eletro = Area.objects.create(nome="Eletrotécnica", slug="eletrotecnica")

        cls.admin = User.objects.create_superuser("admin", password="senha-de-teste-123")

        # coord_ads cuida de uma área
        cls.coord_ads = User.objects.create_user("coord_ads", password="senha-de-teste-123")
        cls.ads.gestores.add(cls.coord_ads)

        # coord_duas cuida de duas
        cls.coord_duas = User.objects.create_user("coord_duas", password="senha-de-teste-123")
        cls.info.gestores.add(cls.coord_duas)
        cls.eletro.gestores.add(cls.coord_duas)

        # conta desativada
        cls.inativo = User.objects.create_user(
            "inativo", password="senha-de-teste-123", is_active=False
        )
        cls.ads.gestores.add(cls.inativo)

        # sem nenhuma área
        cls.sem_area = User.objects.create_user("sem_area", password="senha-de-teste-123")

        cls.ev_ads = Evento.objects.create(
            titulo="Palestra sobre Inteligência Artificial",
            data=date(2026, 10, 28),
            hora_inicio=time(14, 0),
            local="Auditório",
            area=cls.ads,
        )
        cls.ev_info = Evento.objects.create(
            titulo="Workshop de Flutter",
            data=date(2026, 10, 29),
            hora_inicio=time(16, 0),
            local="Laboratório 03",
            area=cls.info,
        )

    def entrar(self, usuario):
        ok = self.client.login(username=usuario, password="senha-de-teste-123")
        self.assertTrue(ok, f"{usuario} deveria conseguir entrar")

    def dados(self, **troca):
        base = {
            "titulo": "Evento de teste",
            "data": "2026-10-30",
            "hora_inicio": "09:00",
            "hora_fim": "",
            "local": "Sala 1",
            "descricao": "",
        }
        base.update(troca)
        return base


class SitePublico(Base):
    def test_home_abre_sem_login(self):
        r = self.client.get(reverse("home"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Semana Nacional de Ciência e Tecnologia")

    def test_cronograma_abre_sem_login_e_mostra_eventos(self):
        r = self.client.get(reverse("cronograma"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Palestra sobre Inteligência Artificial")
        self.assertContains(r, "Workshop de Flutter")

    def test_cronograma_filtra_por_area(self):
        r = self.client.get(reverse("cronograma"), {"area": "ads"})
        self.assertContains(r, "Palestra sobre Inteligência Artificial")
        self.assertNotContains(r, "Workshop de Flutter")

    def test_filtro_de_area_sem_evento_nao_mostra_o_cronograma_inteiro(self):
        """Os cartões da home linkam para áreas que ainda não têm atividade."""
        r = self.client.get(reverse("cronograma"), {"area": "eletrotecnica"})
        self.assertContains(r, "Nenhuma atividade")
        self.assertContains(r, "Eletrotécnica")
        self.assertNotContains(r, "Palestra sobre Inteligência Artificial")
        self.assertNotContains(r, "Workshop de Flutter")

    def test_filtro_de_area_desativada_e_ignorado(self):
        self.eletro.ativo = False
        self.eletro.save()
        r = self.client.get(reverse("cronograma"), {"area": "eletrotecnica"})
        self.assertContains(r, "Palestra sobre Inteligência Artificial")

    def test_slug_inexistente_mostra_tudo(self):
        r = self.client.get(reverse("cronograma"), {"area": "nao-existe"})
        self.assertContains(r, "Palestra sobre Inteligência Artificial")
        self.assertContains(r, "Workshop de Flutter")

    def test_cartoes_da_home_apontam_para_o_cronograma_da_propria_area(self):
        for area in [self.ads, self.info, self.eletro]:
            Cartao.objects.create(area=area, titulo=f"Cartão {area.nome}", descricao="x")

        r = self.client.get(reverse("home"))
        for area in [self.ads, self.info, self.eletro]:
            with self.subTest(slug=area.slug):
                self.assertContains(r, f'href="/cronograma/?area={area.slug}"')

    def test_area_desativada_nao_aparece_no_publico(self):
        self.ads.ativo = False
        self.ads.save()
        r = self.client.get(reverse("cronograma"))
        self.assertNotContains(r, "Palestra sobre Inteligência Artificial")

    def test_alteracao_no_painel_aparece_no_cronograma(self):
        self.entrar("coord_ads")
        self.client.post(
            reverse("painel:editar", args=[self.ev_ads.pk]),
            self.dados(titulo=self.ev_ads.titulo, hora_inicio="15:00", area=self.ads.pk),
        )
        self.client.logout()

        r = self.client.get(reverse("cronograma"))
        self.assertContains(r, "15:00")
        self.assertNotContains(r, "14:00")


class InscricaoNaHome(Base):
    """A inscrição é dado, não HTML: a organização abre e fecha pelo /admin/."""

    def setUp(self):
        # o estado da inscrição aparece no cartão daquela área
        self.cieec = Area.objects.create(nome="CIEEC", slug="cieec")
        Cartao.objects.create(
            area=self.cieec, titulo="Feira do CIEEC", descricao="Uma feira."
        )

    def test_sem_link_mostra_em_breve(self):
        r = self.client.get(reverse("home"))
        self.assertContains(r, "Inscrições em breve")

    def test_com_link_e_aberta_mostra_o_botao(self):
        self.cieec.inscricoes_abertas = True
        self.cieec.link_inscricao = "https://suap.ifro.edu.br/eventos/inscricao/1/999/"
        self.cieec.save()

        r = self.client.get(reverse("home"))
        self.assertContains(r, "https://suap.ifro.edu.br/eventos/inscricao/1/999/")
        self.assertContains(r, "Inscreva-se")
        self.assertContains(r, "Inscrições abertas")

    def test_aberta_sem_link_nao_gera_botao_vazio(self):
        self.cieec.inscricoes_abertas = True
        self.cieec.save()

        r = self.client.get(reverse("home"))
        self.assertContains(r, "Inscrições abertas")     # o selo aparece
        self.assertNotContains(r, 'href=""')             # mas sem botão quebrado
        self.assertIs(self.cieec.mostra_botao_inscricao, False)

    def test_link_sem_estar_aberta_nao_vaza(self):
        self.cieec.link_inscricao = "https://suap.ifro.edu.br/eventos/inscricao/1/999/"
        self.cieec.save()

        r = self.client.get(reverse("home"))
        self.assertNotContains(r, "inscricao/1/999")
        self.assertNotContains(r, "Inscrições abertas")

    def test_area_desativada_nao_mostra_inscricao(self):
        self.cieec.inscricoes_abertas = True
        self.cieec.link_inscricao = "https://suap.ifro.edu.br/eventos/inscricao/1/999/"
        self.cieec.ativo = False
        self.cieec.save()

        r = self.client.get(reverse("home"))
        self.assertNotContains(r, "inscricao/1/999")


class InscricaoPeloPainel(Base):
    """Quem abre e fecha a inscrição é a coordenação, no painel."""

    def url(self, area):
        return reverse("painel:inscricao", args=[area.slug])

    def test_coordenacao_abre_a_inscricao_da_propria_area(self):
        self.entrar("coord_ads")
        r = self.client.post(
            self.url(self.ads),
            {"inscricoes_abertas": "on",
             "link_inscricao": "https://suap.ifro.edu.br/eventos/inscricao/1/777/"},
        )
        self.assertRedirects(r, reverse("painel:lista"))

        self.ads.refresh_from_db()
        self.assertTrue(self.ads.inscricoes_abertas)
        self.assertTrue(self.ads.mostra_botao_inscricao)

    def test_coordenacao_fecha_a_inscricao(self):
        self.ads.inscricoes_abertas = True
        self.ads.link_inscricao = "https://suap.ifro.edu.br/eventos/inscricao/1/777/"
        self.ads.save()

        self.entrar("coord_ads")
        self.client.post(self.url(self.ads), {"link_inscricao": self.ads.link_inscricao})

        self.ads.refresh_from_db()
        self.assertFalse(self.ads.inscricoes_abertas)

    def test_link_sem_esquema_vira_https(self):
        self.entrar("coord_ads")
        self.client.post(
            self.url(self.ads),
            {"inscricoes_abertas": "on", "link_inscricao": "suap.ifro.edu.br/eventos/inscricao/1/9/"},
        )
        self.ads.refresh_from_db()
        self.assertTrue(self.ads.link_inscricao.startswith("https://"))

    def test_link_invalido_e_recusado(self):
        self.entrar("coord_ads")
        r = self.client.post(self.url(self.ads), {"link_inscricao": "isso não é um link"})
        self.assertEqual(r.status_code, 200)
        self.ads.refresh_from_db()
        self.assertEqual(self.ads.link_inscricao, "")

    # ---------------------------------------------------------- o que não pode

    def test_nao_abre_a_tela_de_area_alheia(self):
        self.entrar("coord_ads")
        self.assertEqual(self.client.get(self.url(self.info)).status_code, 404)

    def test_nao_altera_area_alheia_por_post_direto(self):
        self.entrar("coord_ads")
        r = self.client.post(
            self.url(self.info),
            {"inscricoes_abertas": "on", "link_inscricao": "https://exemplo.invalid/x/"},
        )
        self.assertEqual(r.status_code, 404)
        self.info.refresh_from_db()
        self.assertFalse(self.info.inscricoes_abertas)
        self.assertEqual(self.info.link_inscricao, "")

    def test_exige_login(self):
        self.assertEqual(self.client.get(self.url(self.ads)).status_code, 302)

    def test_administrador_altera_qualquer_area(self):
        self.entrar("admin")
        r = self.client.post(
            self.url(self.eletro),
            {"inscricoes_abertas": "on",
             "link_inscricao": "https://suap.ifro.edu.br/eventos/inscricao/1/555/"},
        )
        self.assertRedirects(r, reverse("painel:lista"))
        self.eletro.refresh_from_db()
        self.assertTrue(self.eletro.mostra_botao_inscricao)

    def test_a_lista_do_painel_mostra_o_estado_e_o_link_de_alterar(self):
        self.entrar("coord_ads")
        r = self.client.get(reverse("painel:lista"))
        self.assertContains(r, "estado--breve")
        self.assertContains(r, self.url(self.ads))
        self.assertNotContains(r, self.url(self.info))

    def test_a_lista_mostra_o_estado_certo_em_cada_caso(self):
        self.entrar("coord_ads")

        self.ads.inscricoes_abertas = True
        self.ads.save()
        r = self.client.get(reverse("painel:lista"))
        self.assertContains(r, "estado--falta")
        self.assertContains(r, "Nenhum botão aparece no site sem o link")

        self.ads.link_inscricao = "https://suap.ifro.edu.br/eventos/inscricao/1/1/"
        self.ads.save()
        r = self.client.get(reverse("painel:lista"))
        self.assertContains(r, "estado--aberta")
        self.assertNotContains(r, "Nenhum botão aparece")

    def test_abrir_no_painel_muda_a_pagina_inicial(self):
        """O ciclo inteiro: coordenação abre no painel, visitante vê o botão."""
        cieec = Area.objects.create(nome="CIEEC", slug="cieec")
        cieec.gestores.add(self.coord_ads)
        Cartao.objects.create(area=cieec, titulo="Feira do CIEEC", descricao="Uma feira.")

        self.entrar("coord_ads")
        self.client.post(
            reverse("painel:inscricao", args=["cieec"]),
            {"inscricoes_abertas": "on",
             "link_inscricao": "https://suap.ifro.edu.br/eventos/inscricao/1/321/"},
        )
        self.client.logout()

        r = self.client.get(reverse("home"))
        self.assertContains(r, "inscricao/1/321/")
        self.assertContains(r, "Inscreva-se")


class SubmissaoNaHome(Base):
    """A submissão de trabalhos é uma só, e é dado — não HTML."""

    def test_fechada_mostra_em_breve_e_nao_vaza_link(self):
        s = Submissao.atual()
        s.link = "https://forms.exemplo.invalid/trabalhos"
        s.save()

        r = self.client.get(reverse("home"))
        self.assertContains(r, "Em breve")
        self.assertNotContains(r, "forms.exemplo.invalid")
        self.assertNotContains(r, "Enviar meu trabalho")

    def test_aberta_com_link_mostra_o_botao(self):
        s = Submissao.atual()
        s.aberta = True
        s.link = "https://forms.exemplo.invalid/trabalhos"
        s.save()

        r = self.client.get(reverse("home"))
        self.assertContains(r, "https://forms.exemplo.invalid/trabalhos")
        self.assertContains(r, "Enviar meu trabalho")
        # sem prazo marcado, o lugar grande do cartão diz o estado
        self.assertContains(r, "Aberta")

    def test_aberta_sem_link_nao_gera_botao_vazio(self):
        s = Submissao.atual()
        s.aberta = True
        s.save()

        r = self.client.get(reverse("home"))
        self.assertContains(r, "Em breve")
        self.assertNotContains(r, "Enviar meu trabalho")
        self.assertNotContains(r, 'href=""')
        self.assertIs(s.mostra_botao, False)

    def test_prazo_so_aparece_quando_preenchido(self):
        s = Submissao.atual()
        s.aberta = True
        s.link = "https://forms.exemplo.invalid/trabalhos"
        s.save()
        self.assertNotContains(self.client.get(reverse("home")), "Envios at\u00e9")

        s.prazo = date(2026, 10, 10)
        s.save()
        r = self.client.get(reverse("home"))
        self.assertContains(r, "Prazo de envio")
        self.assertContains(r, "de outubro")

    def test_a_secao_aparece_antes_da_programacao(self):
        # a submissão é a primeira seção da página, e é isso que o pedido era
        html = self.client.get(reverse("home")).content.decode()
        self.assertLess(html.index('id="trabalhos"'), html.index('id="programacao"'))

    def test_como_se_inscrever_fica_acima_dos_cartoes_e_sempre_aberto(self):
        html = self.client.get(reverse("home")).content.decode()
        self.assertIn('id="inscrever"', html)
        self.assertIn("Como se inscrever", html)
        # acima da grade, e não recolhido num <details>
        self.assertLess(html.index('id="inscrever"'), html.index('class="grade-eventos"'))
        self.assertIn("Escolha o evento", html)


class SubmissaoPeloPainel(Base):
    """Quem mexe na submissão é a organização: ela vale para o evento inteiro."""

    url = reverse_lazy("painel:submissao")

    def test_administrador_abre_a_submissao(self):
        self.entrar("admin")
        r = self.client.post(
            self.url,
            {"aberta": "on", "link": "https://forms.exemplo.invalid/trabalhos", "prazo": ""},
        )
        self.assertEqual(r.status_code, 302)

        s = Submissao.atual()
        self.assertTrue(s.aberta)
        self.assertEqual(s.link, "https://forms.exemplo.invalid/trabalhos")

    def test_link_sem_esquema_vira_https(self):
        self.entrar("admin")
        self.client.post(
            self.url, {"aberta": "on", "link": "forms.exemplo.invalid/trabalhos", "prazo": ""}
        )
        self.assertEqual(
            Submissao.atual().link, "https://forms.exemplo.invalid/trabalhos"
        )

    def test_link_invalido_e_recusado(self):
        self.entrar("admin")
        r = self.client.post(self.url, {"aberta": "on", "link": "isto não é um link", "prazo": ""})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Submissao.atual().aberta)

    def test_coordenacao_nao_abre_a_tela(self):
        self.entrar("coord_ads")
        self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_coordenacao_nao_altera_por_post_direto(self):
        self.entrar("coord_ads")
        r = self.client.post(
            self.url, {"aberta": "on", "link": "https://invasao.exemplo.invalid/", "prazo": ""}
        )
        self.assertEqual(r.status_code, 404)
        self.assertFalse(Submissao.atual().aberta)
        self.assertEqual(Submissao.atual().link, "")

    def test_o_bloco_so_aparece_para_o_administrador(self):
        self.entrar("admin")
        self.assertContains(self.client.get(reverse("painel:lista")), "Submissão de trabalhos")

        self.client.logout()
        self.entrar("coord_ads")
        r = self.client.get(reverse("painel:lista"))
        self.assertNotContains(r, "Submissão de trabalhos")

    def test_abrir_no_painel_muda_a_pagina_inicial(self):
        self.assertContains(self.client.get(reverse("home")), "Em breve")

        self.entrar("admin")
        self.client.post(
            self.url,
            {"aberta": "on", "link": "https://forms.exemplo.invalid/t", "prazo": "2026-10-10"},
        )

        self.client.logout()
        r = self.client.get(reverse("home"))
        self.assertContains(r, "https://forms.exemplo.invalid/t")
        self.assertContains(r, "Prazo de envio")
        self.assertContains(r, "de outubro")

    def test_e_sempre_a_mesma_linha(self):
        # o modelo é de uma linha só: salvar de novo não cria uma segunda
        Submissao.atual().save()
        Submissao(aberta=True, link="https://forms.exemplo.invalid/x").save()
        self.assertEqual(Submissao.objects.count(), 1)
        self.assertTrue(Submissao.atual().aberta)


class CartoesNaHome(Base):
    """Os cartões da página inicial são dados, e o texto sai escapado."""

    def setUp(self):
        self.cartao = Cartao.objects.create(
            area=self.ads,
            trilha="Abertura oficial",
            titulo="Abertura no laboratório",
            coordenacao="Comissão organizadora",
            descricao="Cerimônia de abertura no Campus.",
            programacao_rotulo="28/10",
            programacao="Cerimônia\nMostras dos cursos\n\n  ",
            ordem=0,
        )

    def test_o_cartao_aparece_com_o_que_foi_cadastrado(self):
        r = self.client.get(reverse("home"))
        self.assertContains(r, "Abertura no laboratório")
        self.assertContains(r, "Abertura oficial")
        self.assertContains(r, "Comissão organizadora")
        self.assertContains(r, "Programação · 28/10")
        self.assertContains(r, "<li>Cerimônia</li>", html=False)

    def test_linhas_vazias_da_programacao_nao_viram_item(self):
        self.assertEqual(self.cartao.itens_programacao, ["Cerimônia", "Mostras dos cursos"])

    def test_sem_responsavel_mostra_a_confirmar(self):
        self.assertContains(self.client.get(reverse("home")), "a confirmar")

        self.cartao.responsavel = "Eudóxia Moura"
        self.cartao.save()
        r = self.client.get(reverse("home"))
        self.assertContains(r, "Eudóxia Moura")

    def test_etiqueta_em_branco_usa_o_nome_do_curso(self):
        self.cartao.trilha = ""
        self.cartao.save()
        self.assertEqual(self.cartao.etiqueta, "ADS")
        self.assertContains(self.client.get(reverse("home")), "ADS")

    def test_cartao_despublicado_some_do_site(self):
        self.cartao.publicado = False
        self.cartao.save()
        self.assertNotContains(self.client.get(reverse("home")), "Abertura no laboratório")

    def test_cartao_de_area_desativada_some_do_site(self):
        self.ads.ativo = False
        self.ads.save()
        self.assertNotContains(self.client.get(reverse("home")), "Abertura no laboratório")

    def test_html_digitado_no_painel_sai_como_texto(self):
        self.cartao.descricao = '<script>alert(1)</script> e <b>negrito</b>'
        self.cartao.save()
        r = self.client.get(reverse("home"))
        self.assertNotContains(r, "<script>")
        self.assertNotContains(r, "<b>negrito</b>")
        self.assertContains(r, "&lt;script&gt;")

    def test_a_palavra_campus_sai_em_italico(self):
        self.assertContains(self.client.get(reverse("home")), "no <i>Campus</i>")

    def test_ver_horarios_leva_ao_cronograma_por_padrao(self):
        self.assertEqual(self.cartao.url_horarios, "/cronograma/?area=ads")
        self.assertIs(self.cartao.horarios_fora, False)

        r = self.client.get(reverse("home"))
        self.assertContains(r, 'href="/cronograma/?area=ads"')

    def test_link_proprio_tira_o_ver_horarios_do_site(self):
        # um curso que publica a programação em página própria
        self.cartao.link_horarios = "https://exemplo.invalid/horarios/"
        self.cartao.save()

        self.assertEqual(self.cartao.url_horarios, "https://exemplo.invalid/horarios/")
        self.assertIs(self.cartao.horarios_fora, True)

        r = self.client.get(reverse("home"))
        self.assertContains(r, 'href="https://exemplo.invalid/horarios/"')
        self.assertNotContains(r, 'href="/cronograma/?area=ads"')
        # link para fora abre em outra aba, e sem passar o referenciador
        self.assertContains(r, 'rel="noopener"')

    def test_o_link_proprio_e_so_daquele_cartao(self):
        self.cartao.link_horarios = "https://exemplo.invalid/horarios/"
        self.cartao.save()
        outro = Cartao.objects.create(area=self.info, titulo="Outro", descricao="x")

        r = self.client.get(reverse("home"))
        self.assertContains(r, 'href="https://exemplo.invalid/horarios/"')
        self.assertContains(r, f'href="/cronograma/?area={outro.area.slug}"')

    def test_a_inscricao_continua_vindo_da_area(self):
        # o cartão não guarda link de inscrição: quem manda nisso é a área
        self.ads.inscricoes_abertas = True
        self.ads.link_inscricao = "https://suap.exemplo.invalid/1/"
        self.ads.save()

        r = self.client.get(reverse("home"))
        self.assertContains(r, "https://suap.exemplo.invalid/1/")
        self.assertContains(r, "Inscreva-se")

    def test_ordem_manda_na_sequencia(self):
        Cartao.objects.create(
            area=self.info, titulo="Primeiro de todos", descricao="x", ordem=-0
        )
        segundo = Cartao.objects.get(pk=self.cartao.pk)
        segundo.ordem = 5
        segundo.save()

        html = self.client.get(reverse("home")).content.decode()
        self.assertLess(html.index("Primeiro de todos"), html.index("Abertura no laboratório"))


class CartoesPeloPainel(Base):
    """Só o administrador edita os cartões — no GET e no POST."""

    def setUp(self):
        self.cartao = Cartao.objects.create(
            area=self.ads, titulo="Cartão de teste", descricao="Texto.", ordem=0
        )

    def dados_do_cartao(self, **troca):
        base = {
            "titulo": "Cartão de teste",
            "area": self.ads.pk,
            "trilha": "",
            "responsavel": "",
            "coordenacao": "",
            "descricao": "Texto.",
            "programacao_rotulo": "",
            "programacao": "",
            "link_horarios": "",
            "ordem": 0,
            "publicado": "on",
        }
        base.update(troca)
        return base

    def test_administrador_cria_edita_e_exclui(self):
        self.entrar("admin")

        r = self.client.post(
            reverse("painel:cartao_novo"), self.dados_do_cartao(titulo="Novo cartão")
        )
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Cartao.objects.filter(titulo="Novo cartão").exists())

        r = self.client.post(
            reverse("painel:cartao_editar", args=[self.cartao.pk]),
            self.dados_do_cartao(titulo="Título trocado"),
        )
        self.assertEqual(r.status_code, 302)
        self.cartao.refresh_from_db()
        self.assertEqual(self.cartao.titulo, "Título trocado")

        r = self.client.post(reverse("painel:cartao_excluir", args=[self.cartao.pk]))
        self.assertEqual(r.status_code, 302)
        self.assertFalse(Cartao.objects.filter(pk=self.cartao.pk).exists())

    def test_coordenacao_nao_abre_nenhuma_das_telas(self):
        self.entrar("coord_ads")
        urls = [
            reverse("painel:cartoes"),
            reverse("painel:cartao_novo"),
            reverse("painel:cartao_editar", args=[self.cartao.pk]),
            reverse("painel:cartao_excluir", args=[self.cartao.pk]),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)

    def test_coordenacao_nao_edita_por_post_direto(self):
        self.entrar("coord_ads")
        r = self.client.post(
            reverse("painel:cartao_editar", args=[self.cartao.pk]),
            self.dados_do_cartao(titulo="Invadido"),
        )
        self.assertEqual(r.status_code, 404)
        self.cartao.refresh_from_db()
        self.assertEqual(self.cartao.titulo, "Cartão de teste")

    def test_coordenacao_nao_exclui_por_post_direto(self):
        self.entrar("coord_ads")
        r = self.client.post(reverse("painel:cartao_excluir", args=[self.cartao.pk]))
        self.assertEqual(r.status_code, 404)
        self.assertTrue(Cartao.objects.filter(pk=self.cartao.pk).exists())

    def test_get_nao_exclui(self):
        self.entrar("admin")
        self.client.get(reverse("painel:cartao_excluir", args=[self.cartao.pk]))
        self.assertTrue(Cartao.objects.filter(pk=self.cartao.pk).exists())

    def test_o_atalho_so_aparece_para_o_administrador(self):
        self.entrar("admin")
        self.assertContains(self.client.get(reverse("painel:lista")), "Cartões da página inicial")

        self.client.logout()
        self.entrar("coord_ads")
        r = self.client.get(reverse("painel:lista"))
        self.assertNotContains(r, "Cartões da página inicial")

    def test_editar_no_painel_muda_a_pagina_inicial(self):
        self.entrar("admin")
        self.client.post(
            reverse("painel:cartao_editar", args=[self.cartao.pk]),
            self.dados_do_cartao(titulo="Aparece no site", descricao="Descrição nova."),
        )
        self.client.logout()

        r = self.client.get(reverse("home"))
        self.assertContains(r, "Aparece no site")
        self.assertContains(r, "Descrição nova.")


class Saude(Base):
    def test_responde_ok(self):
        r = self.client.get(reverse("saude"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.content, b"ok\n")


class Acesso(Base):
    def test_painel_exige_login(self):
        r = self.client.get(reverse("painel:lista"))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("painel:entrar"), r.url)

    def test_todas_as_paginas_do_painel_exigem_login(self):
        urls = [
            reverse("painel:lista"),
            reverse("painel:novo"),
            reverse("painel:inscricao", args=[self.ads.slug]),
            reverse("painel:submissao"),
            reverse("painel:cartoes"),
            reverse("painel:cartao_novo"),
            reverse("painel:editar", args=[self.ev_ads.pk]),
            reverse("painel:excluir", args=[self.ev_ads.pk]),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 302)

    def test_usuario_inativo_nao_entra(self):
        ok = self.client.login(username="inativo", password="senha-de-teste-123")
        self.assertFalse(ok)
        self.assertEqual(self.client.get(reverse("painel:lista")).status_code, 302)

    def test_coordenacao_nao_entra_no_django_admin(self):
        self.entrar("coord_ads")
        r = self.client.get("/admin/", follow=True)
        # o admin manda para a tela de login dele em vez de abrir
        self.assertNotContains(r, "Administração do site", status_code=200)

    def test_conta_sem_area_ve_explicacao_em_vez_de_formulario(self):
        self.entrar("sem_area")
        r = self.client.get(reverse("painel:lista"))
        self.assertContains(r, "ainda não tem curso/área")
        r = self.client.get(reverse("painel:novo"))
        self.assertContains(r, "ainda não tem curso/área")


class PermissoesDaCoordenacao(Base):
    def test_ve_somente_os_proprios_eventos(self):
        self.entrar("coord_ads")
        r = self.client.get(reverse("painel:lista"))
        self.assertContains(r, "Palestra sobre Inteligência Artificial")
        self.assertNotContains(r, "Workshop de Flutter")

    def test_cria_evento_na_propria_area(self):
        self.entrar("coord_ads")
        r = self.client.post(reverse("painel:novo"), self.dados(area=self.ads.pk))
        self.assertRedirects(r, reverse("painel:lista"))
        self.assertTrue(Evento.objects.filter(titulo="Evento de teste", area=self.ads).exists())

    def test_evento_criado_guarda_quem_criou(self):
        self.entrar("coord_ads")
        self.client.post(reverse("painel:novo"), self.dados(area=self.ads.pk))
        evento = Evento.objects.get(titulo="Evento de teste")
        self.assertEqual(evento.criado_por, self.coord_ads)

    def test_edita_evento_da_propria_area(self):
        self.entrar("coord_ads")
        r = self.client.post(
            reverse("painel:editar", args=[self.ev_ads.pk]),
            self.dados(titulo="Título novo", area=self.ads.pk),
        )
        self.assertRedirects(r, reverse("painel:lista"))
        self.ev_ads.refresh_from_db()
        self.assertEqual(self.ev_ads.titulo, "Título novo")

    def test_exclui_evento_da_propria_area(self):
        self.entrar("coord_ads")
        r = self.client.post(reverse("painel:excluir", args=[self.ev_ads.pk]))
        self.assertRedirects(r, reverse("painel:lista"))
        self.assertFalse(Evento.objects.filter(pk=self.ev_ads.pk).exists())

    # ---------------------------------------------------------- o que não pode

    def test_nao_cria_evento_em_area_alheia(self):
        self.entrar("coord_ads")
        r = self.client.post(reverse("painel:novo"), self.dados(area=self.info.pk))
        self.assertEqual(r.status_code, 200)  # volta com erro, não redireciona
        self.assertFalse(Evento.objects.filter(titulo="Evento de teste").exists())

    def test_nao_abre_edicao_de_evento_alheio(self):
        self.entrar("coord_ads")
        r = self.client.get(reverse("painel:editar", args=[self.ev_info.pk]))
        self.assertEqual(r.status_code, 404)

    def test_nao_edita_evento_alheio_por_post_direto(self):
        self.entrar("coord_ads")
        r = self.client.post(
            reverse("painel:editar", args=[self.ev_info.pk]),
            self.dados(titulo="Invadido", area=self.ads.pk),
        )
        self.assertEqual(r.status_code, 404)
        self.ev_info.refresh_from_db()
        self.assertEqual(self.ev_info.titulo, "Workshop de Flutter")

    def test_nao_exclui_evento_alheio_por_post_direto(self):
        self.entrar("coord_ads")
        r = self.client.post(reverse("painel:excluir", args=[self.ev_info.pk]))
        self.assertEqual(r.status_code, 404)
        self.assertTrue(Evento.objects.filter(pk=self.ev_info.pk).exists())

    def test_nao_move_evento_proprio_para_area_alheia(self):
        self.entrar("coord_ads")
        r = self.client.post(
            reverse("painel:editar", args=[self.ev_ads.pk]),
            self.dados(titulo=self.ev_ads.titulo, area=self.info.pk),
        )
        self.assertEqual(r.status_code, 200)
        self.ev_ads.refresh_from_db()
        self.assertEqual(self.ev_ads.area, self.ads)

    def test_get_nao_exclui(self):
        self.entrar("coord_ads")
        r = self.client.get(reverse("painel:excluir", args=[self.ev_ads.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Excluir evento?")
        self.assertTrue(Evento.objects.filter(pk=self.ev_ads.pk).exists())


class DuasAreas(Base):
    def test_ve_as_duas_areas_e_nao_a_terceira(self):
        self.entrar("coord_duas")
        r = self.client.get(reverse("painel:lista"))
        self.assertContains(r, "Workshop de Flutter")
        self.assertNotContains(r, "Palestra sobre Inteligência Artificial")

    def test_pode_escolher_entre_as_duas_no_formulario(self):
        self.entrar("coord_duas")
        r = self.client.get(reverse("painel:novo"))
        opcoes = r.context["form"].fields["area"].queryset
        self.assertCountEqual(list(opcoes), [self.info, self.eletro])

    def test_uma_area_dispensa_a_escolha(self):
        self.entrar("coord_ads")
        r = self.client.get(reverse("painel:novo"))
        self.assertEqual(r.context["form"].area_unica, self.ads)


class Administrador(Base):
    def test_ve_eventos_de_todas_as_areas(self):
        self.entrar("admin")
        r = self.client.get(reverse("painel:lista"))
        self.assertContains(r, "Palestra sobre Inteligência Artificial")
        self.assertContains(r, "Workshop de Flutter")

    def test_edita_qualquer_evento(self):
        self.entrar("admin")
        r = self.client.post(
            reverse("painel:editar", args=[self.ev_info.pk]),
            self.dados(titulo="Editado pelo admin", area=self.info.pk),
        )
        self.assertRedirects(r, reverse("painel:lista"))
        self.ev_info.refresh_from_db()
        self.assertEqual(self.ev_info.titulo, "Editado pelo admin")

    def test_exclui_qualquer_evento(self):
        self.entrar("admin")
        self.client.post(reverse("painel:excluir", args=[self.ev_info.pk]))
        self.assertFalse(Evento.objects.filter(pk=self.ev_info.pk).exists())

    def test_cria_evento_em_qualquer_area(self):
        self.entrar("admin")
        r = self.client.post(reverse("painel:novo"), self.dados(area=self.eletro.pk))
        self.assertRedirects(r, reverse("painel:lista"))
        self.assertTrue(Evento.objects.filter(area=self.eletro).exists())

    def test_entra_no_django_admin(self):
        self.entrar("admin")
        self.assertEqual(self.client.get("/admin/").status_code, 200)

    def test_gerencia_usuarios_e_areas_pelo_admin(self):
        self.entrar("admin")
        for url in ["/admin/auth/user/", "/admin/eventos/area/", "/admin/eventos/evento/"]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_define_areas_de_um_usuario_pelo_admin(self):
        self.entrar("admin")
        r = self.client.post(
            f"/admin/auth/user/{self.coord_ads.pk}/change/",
            {
                "username": "coord_ads",
                "first_name": "",
                "last_name": "",
                "email": "",
                "is_active": "on",
                "areas": [self.ads.pk, self.info.pk],
                "last_login_0": "",
                "last_login_1": "",
                "date_joined_0": "2026-01-01",
                "date_joined_1": "00:00:00",
            },
        )
        self.assertEqual(r.status_code, 302, "o admin deveria salvar e redirecionar")
        self.assertCountEqual(
            list(self.coord_ads.areas_geridas.all()), [self.ads, self.info]
        )


class RegrasDoEvento(Base):
    def test_termino_antes_do_inicio_e_recusado(self):
        self.entrar("coord_ads")
        r = self.client.post(
            reverse("painel:novo"),
            self.dados(area=self.ads.pk, hora_inicio="16:00", hora_fim="14:00"),
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "depois do de início")
        self.assertFalse(Evento.objects.filter(titulo="Evento de teste").exists())

    def test_termino_e_opcional(self):
        self.entrar("coord_ads")
        r = self.client.post(reverse("painel:novo"), self.dados(area=self.ads.pk, hora_fim=""))
        self.assertRedirects(r, reverse("painel:lista"))
        self.assertIsNone(Evento.objects.get(titulo="Evento de teste").hora_fim)

    def test_horario_formatado(self):
        evento = Evento(hora_inicio=time(14, 0), hora_fim=time(16, 30))
        self.assertEqual(evento.horario, "14:00 às 16:30")
        evento.hora_fim = None
        self.assertEqual(evento.horario, "14:00")

    def test_slug_sai_do_nome(self):
        area = Area.objects.create(nome="Medicina Veterinária")
        self.assertEqual(area.slug, "medicina-veterinaria")

    def test_area_com_evento_nao_e_apagada_por_acidente(self):
        from django.db.models import ProtectedError

        with self.assertRaises(ProtectedError):
            self.ads.delete()
