from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, ExpressionWrapper, F, fields
from django.shortcuts import render

from casos.models import Caso
from usuarios.permissions import escopo_casos


@login_required
def painel(request):
    casos = escopo_casos(
        request.user,
        Caso.objects.select_related("estudante__escola").prefetch_related("evolucoes"),
    )

    total = casos.count()
    aguardando = casos.filter(situacao=Caso.Situacao.AGUARDANDO).count()
    em_acompanhamento = casos.filter(situacao=Caso.Situacao.EM_ACOMPANHAMENTO).count()
    encerrados = casos.filter(situacao=Caso.Situacao.ENCERRADO).count()
    ativos = aguardando + em_acompanhamento

    tempo_medio = (
        casos.filter(data_atendimento__isnull=False)
        .annotate(
            espera=ExpressionWrapper(
                F("data_atendimento") - F("data_encaminhamento"),
                output_field=fields.DurationField(),
            )
        )
        .aggregate(media=Avg("espera"))["media"]
    )
    tempo_medio_dias = tempo_medio.days if tempo_medio else None

    casos_criticos = sum(
        1 for c in casos.exclude(situacao=Caso.Situacao.ENCERRADO) if c.nivel_alerta == "critico"
    )
    casos_graves = casos.exclude(situacao=Caso.Situacao.ENCERRADO).filter(
        gravidade__in=[Caso.Gravidade.ALTA, Caso.Gravidade.URGENTE]
    ).count()

    por_escola = (
        casos.values("estudante__escola__nome")
        .annotate(total=Count("id"))
        .order_by("-total")
    )

    contexto = {
        "total": total,
        "ativos": ativos,
        "aguardando": aguardando,
        "em_acompanhamento": em_acompanhamento,
        "encerrados": encerrados,
        "tempo_medio_dias": tempo_medio_dias,
        "casos_criticos": casos_criticos,
        "casos_graves": casos_graves,
        "por_escola": por_escola,
        # Listas Python cruas — o template usa |json_script para serializar
        # com escape correto (não usar |safe com json.dumps aqui: um nome de
        # escola cadastrado com "</script>" quebraria o bloco de script).
        "grafico_labels": [p["estudante__escola__nome"] for p in por_escola],
        "grafico_valores": [p["total"] for p in por_escola],
    }
    return render(request, "indicadores/painel.html", contexto)
