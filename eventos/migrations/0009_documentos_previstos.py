from django.db import migrations
#
# Os três documentos da submissão que a organização já anunciou: o
# regulamento e os dois modelos de trabalho. Entram sem arquivo — nenhum
# deles estava pronto quando esta migração foi escrita —, e a página de
# submissão os mostra como "em breve" até alguém enviar o arquivo pelo
# painel. Assim quem visita já sabe o que vai precisar.
#
# O cronograma de avaliação não está aqui de propósito: ele mora no próprio
# site, em /cronograma/, e não num PDF para baixar.

DOCUMENTOS = [
    {
        "titulo": "Regulamento",
        "slug": "regulamento",
        "descricao": "Regras de participação, formatação e avaliação dos trabalhos.",
        "ordem": 0,
    },
    {
        "titulo": "Template de Trabalho Completo",
        "slug": "template-de-trabalho-completo",
        "descricao": "Modelo para quem vai enviar o trabalho na íntegra.",
        "ordem": 1,
    },
    {
        "titulo": "Template de Resumo Simples",
        "slug": "template-de-resumo-simples",
        "descricao": "Modelo para quem vai enviar apenas o resumo.",
        "ordem": 2,
    },
]


def cria_os_documentos(apps, schema_editor):
    Anexo = apps.get_model("eventos", "Anexo")
    # Se já houver documento cadastrado, esta migração não tem o que fazer:
    # quem está no banco veio do painel e manda.
    if Anexo.objects.exists():
        return
    for documento in DOCUMENTOS:
        Anexo.objects.create(**documento)


def apaga_os_documentos(apps, schema_editor):
    # Só os três que esta migração criou, e só se ninguém tiver mexido neles:
    # um documento com arquivo enviado é trabalho de alguém.
    Anexo = apps.get_model("eventos", "Anexo")
    Anexo.objects.filter(
        slug__in=[d["slug"] for d in DOCUMENTOS], arquivo="", link="", texto=""
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("eventos", "0008_inscricao_por_evento"),
    ]

    operations = [
        migrations.RunPython(cria_os_documentos, apaga_os_documentos),
    ]
