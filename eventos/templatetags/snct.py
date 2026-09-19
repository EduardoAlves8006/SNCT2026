import re

from django import template
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(needs_autoescape=True)
def campus(texto, autoescape=True):
    """Põe *Campus* em itálico, como manda a convenção do IFRO.

    O texto vem do banco e é escapado normalmente aqui; só a palavra Campus
    vira marcação. Assim ninguém precisa digitar HTML no painel para manter a
    grafia certa — e nenhum HTML digitado lá chega ao site.
    """
    escapar = conditional_escape if autoescape else (lambda x: x)
    return mark_safe(re.sub(r"\bCampus\b", "<i>Campus</i>", escapar(texto or "")))
