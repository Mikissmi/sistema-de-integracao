import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from usuarios.models import LogAuditoria
from usuarios.permissions import escopo_estudantes

from .forms import BuscaCPFForm, EstudanteForm, EstudanteImportForm
from .importacao import COLUNAS_ESPERADAS, processar_csv
from .models import Estudante


@login_required
def buscar(request):
    """Busca por CPF antes de cadastrar, para evitar duplicidade de registro."""
    resultado = None
    cpf = request.GET.get("cpf", "")
    form = BuscaCPFForm(request.GET or None, initial={"cpf": cpf})
    if cpf:
        resultado = Estudante.buscar_por_cpf(cpf)
    return render(
        request,
        "estudantes/buscar.html",
        {"form": form, "resultado": resultado, "cpf_pesquisado": cpf},
    )


@login_required
def novo(request):
    cpf_inicial = request.GET.get("cpf", "")
    if request.method == "POST":
        form = EstudanteForm(request.POST, usuario=request.user)
        if form.is_valid():
            try:
                estudante = form.save()
            except IntegrityError:
                # Defesa em profundidade contra corrida entre a checagem de
                # duplicidade do clean_cpf e o INSERT (dois cadastros do
                # mesmo CPF quase simultâneos). A constraint unique do banco
                # (cpf_hash) sempre foi a garantia final — só faltava tratar
                # o erro dela de forma amigável em vez de estourar um 500.
                form.add_error(
                    "cpf", "Já existe um estudante cadastrado com este CPF."
                )
            else:
                LogAuditoria.objects.create(
                    usuario=request.user, acao="criar_estudante", objeto=str(estudante)
                )
                messages.success(
                    request, f'Estudante "{estudante.nome}" cadastrado com sucesso.'
                )
                return redirect("casos:novo", estudante_id=estudante.pk)
    else:
        form = EstudanteForm(initial={"cpf": cpf_inicial}, usuario=request.user)
    return render(request, "estudantes/form.html", {"form": form})


@login_required
def detalhe(request, pk):
    estudante = get_object_or_404(escopo_estudantes(request.user, Estudante.objects.all()), pk=pk)
    LogAuditoria.objects.create(
        usuario=request.user, acao="visualizar_estudante", objeto=str(estudante)
    )
    casos = estudante.casos.select_related("servico_encaminhado").prefetch_related("evolucoes")
    return render(request, "estudantes/detalhe.html", {"estudante": estudante, "casos": casos})


@login_required
def lista(request):
    termo = request.GET.get("q", "")
    estudantes = escopo_estudantes(request.user, Estudante.objects.select_related("escola"))
    if termo:
        estudantes = estudantes.filter(nome__icontains=termo)
    pagina = Paginator(estudantes, 25).get_page(request.GET.get("page"))
    return render(request, "estudantes/lista.html", {"estudantes": pagina, "termo": termo})


@login_required
def importar_csv(request):
    if request.method == "POST":
        form = EstudanteImportForm(request.POST, request.FILES, usuario=request.user)
        if form.is_valid():
            escola = form.cleaned_data["escola"]
            try:
                importados, erros = processar_csv(form.cleaned_data["arquivo"], escola, request.user)
            except ValidationError as e:
                form.add_error("arquivo", e.message if hasattr(e, "message") else str(e))
            else:
                LogAuditoria.objects.create(
                    usuario=request.user,
                    acao="importar_csv_lote",
                    objeto=f"{escola} — {importados} importado(s), {len(erros)} erro(s)",
                )
                if importados:
                    messages.success(request, f"{importados} estudante(s) importado(s) com sucesso.")
                if erros:
                    messages.warning(
                        request, f"{len(erros)} linha(s) não foram importadas — veja os detalhes abaixo."
                    )
                return render(
                    request,
                    "estudantes/importar_resultado.html",
                    {"importados": importados, "erros": erros, "escola": escola},
                )
    else:
        form = EstudanteImportForm(usuario=request.user)
    return render(request, "estudantes/importar.html", {"form": form})


@login_required
def modelo_csv(request):
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="modelo_importacao_estudantes.csv"'
    writer = csv.writer(response)
    writer.writerow(COLUNAS_ESPERADAS)
    writer.writerow(
        [
            "Maria Exemplo da Silva",
            "111.444.777-35",
            "15/03/2015",
            "João Exemplo da Silva",
            "(51) 99999-8888",
            "5º ano",
            "ESF Centro",
        ]
    )
    return response
