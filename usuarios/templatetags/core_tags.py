from django import template

register = template.Library()


@register.simple_tag
def replace_query_param(request, field, value):
    """Monta a querystring atual trocando/adicionando `field=value`.

    Usado na paginação: preserva os filtros já aplicados (escola, situação,
    busca por nome etc.) ao trocar só o número da página.
    """
    query = request.GET.copy()
    query[field] = value
    return query.urlencode()
