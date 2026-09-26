from django.db import migrations, models
#
# Uma atividade pode ter inscrição só dela. Campo novo e em branco: todo
# evento que já está no banco continua usando o link do curso/área, que é
# exatamente o que ele fazia antes desta migração.


class Migration(migrations.Migration):

    dependencies = [
        ("eventos", "0007_documentos_da_submissao"),
    ]

    operations = [
        migrations.AddField(
            model_name="evento",
            name="link_inscricao",
            field=models.URLField(
                blank=True,
                help_text="Só quando esta atividade tem inscrição separada. Em "
                "branco, o cronograma usa o link do curso/área — o mesmo do "
                "cartão da página inicial.",
                max_length=300,
                verbose_name="link de inscrição",
            ),
        ),
    ]
