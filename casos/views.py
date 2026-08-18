import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from atendimentos.models import TipoAtendimento
from escolas.models import Escola
from estudantes.models import Estudante
from territorios.models import Territorio
from usuarios.models import LogAuditoria
from usuarios.permissions import escopo_casos, escopo_estudantes

from .forms import CasoForm, CasoSituacaoForm, EvolucaoForm
from .models import Caso


@login_required
def novo(request, estudante_id):
    estudante = get_object_or_404(
        escopo_estudantes(request.user, Estudante.objects.all()), pk=estudante_id
    )
    if request.method == "POST":
        form = CasoForm(request.POST, request.FILES)
        if form.is_valid():
            caso = form.save(commit=False)
            caso.estudante = estudante
            caso.save()
            LogAuditoria.objects.create(
                usuario=request.user, acao="criar_caso", objeto=str(caso)
            )
            messages.success(request, "Encaminhamento registrado com sucesso.")
            return redirect("casos:detalhe", pk=caso.pk)
    else:
        form = CasoForm()
    return render(request, "casos/form.html", {"form": form, "estudante": estudante})


@login_required
def lista(request):
    casos = escopo_casos(
        request.user,
        Caso.objects.select_related("estudante", "estudante__escola").prefetch_related(
            "evolucoes"
        ),
    )

    escola_id = request.GET.get("escola")
    situacao = request.GET.get("situacao")
    territorio_id = request.GET.get("territorio")
    tipo_atendimento_id = request.GET.get("tipo_atendimento")
    gravidade = request.GET.get("gravidade")
    termo = request.GET.get("q")

    if escola_id:
        casos = casos.filter(estudante__escola_id=escola_id)
    if situacao:
        casos = casos.filter(situacao=situacao)
    if territorio_id:
        casos = casos.filter(estudante__territorio_esf_id=territorio_id)
    if tipo_atendimento_id:
        casos = casos.filter(servico_encaminhado_id=tipo_atendimento_id)
    if gravidade:
        casos = casos.filter(gravidade=gravidade)
    if termo:
        casos = casos.filter(estudante__nome__icontains=termo)

    pagina = Paginator(casos, 25).get_page(request.GET.get("page"))

    return render(
        request,
        "casos/lista.html",
        {
            "casos": pagina,
            "situacoes": Caso.Situacao.choices,
            "gravidades": Caso.Gravidade.choices,
            "escolas": Escola.objects.filter(ativo=True),
            "territorios": Territorio.objects.filter(ativo=True),
            "tipos_atendimento": TipoAtendimento.objects.filter(ativo=True),
            "filtros": request.GET,
        },
    )


@login_required
def detalhe(request, pk):
    caso = get_object_or_404(escopo_casos(request.user, Caso.objects.all()), pk=pk)

    if request.method == "POST":
        form = EvolucaoForm(request.POST)
        if form.is_valid():
            evolucao = form.save(commit=False)
            evolucao.caso = caso
            evolucao.registrado_por = request.user
            evolucao.save()
            LogAuditoria.objects.create(
                usuario=request.user, acao="registrar_evolucao", objeto=str(caso)
            )
            messages.success(request, "Evolução registrada com sucesso.")
            return redirect("casos:detalhe", pk=caso.pk)
    else:
        form = EvolucaoForm()

    LogAuditoria.objects.create(usuario=request.user, acao="visualizar_caso", objeto=str(caso))
    evolucoes = caso.evolucoes.order_by("data_movimentacao", "criado_em")
    situacao_form = CasoSituacaoForm(instance=caso)
    return render(
        request,
        "casos/detalhe.html",
        {"caso": caso, "evolucoes": evolucoes, "form": form, "situacao_form": situacao_form},
    )


@login_required
def atualizar_situacao(request, pk):
    caso = get_object_or_404(escopo_casos(request.user, Caso.objects.all()), pk=pk)
    if request.method == "POST":
        form = CasoSituacaoForm(request.POST, instance=caso)
        if form.is_valid():
            form.save()
            LogAuditoria.objects.create(
                usuario=request.user, acao="atualizar_situacao_caso", objeto=str(caso)
            )
            messages.success(request, "Situação do caso atualizada.")
        else:
            messages.error(request, "Não foi possível atualizar a situação do caso.")
    return redirect("casos:detalhe", pk=pk)


@login_required
def exportar_csv(request):
    casos = escopo_casos(
        request.user, Caso.objects.select_related("estudante", "estudante__escola")
    )
    escola_id = request.GET.get("escola")
    if escola_id:
        casos = casos.filter(estudante__escola_id=escola_id)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="casos.csv"'
    writer = csv.writer(response)
    writer.writerow(
        [
            "Escola",
            "Estudante",
            "Serviço Encaminhado",
            "Data do Encaminhamento",
            "Data do Atendimento",
            "Situação",
            "Gravidade",
            "Dias sem Retorno",
            "Nível de Alerta",
        ]
    )
    for caso in casos:
        writer.writerow(
            [
                caso.estudante.escola,
                caso.estudante.nome,
                caso.servico_encaminhado,
                caso.data_encaminhamento,
                caso.data_atendimento or "",
                caso.get_situacao_display(),
                caso.get_gravidade_display(),
                caso.dias_sem_retorno if caso.dias_sem_retorno is not None else "",
                caso.nivel_alerta,
            ]
        )
    return response
