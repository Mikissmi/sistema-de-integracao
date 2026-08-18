"""Escopo de dados por perfil de usuário.

- Educação: vê só a própria escola.
- Saúde: se tiver Território/ESF definido, vê só aquele território; se o
  campo ficar em branco, vê todas as escolas/territórios (perfil do
  profissional que acompanha todos os encaminhamentos da rede de saúde).
- Gestão / superusuário: vê tudo.
- Sem perfil vinculado: não vê nada (fail-closed). Antes, um usuário
  autenticado sem PerfilUsuario associado enxergava tudo — o mesmo nível de
  acesso de "Gestão" só por estar sem configuração. Um perfil ausente deve
  ser tratado como um cadastro incompleto, não como acesso total.
"""


def escopo_casos(user, queryset):
    if user.is_superuser:
        return queryset
    perfil = getattr(user, "perfil", None)
    if perfil is None:
        return queryset.none()
    if perfil.perfil == "gestao":
        return queryset
    if perfil.perfil == "educacao":
        return queryset.filter(estudante__escola=perfil.escola)
    if perfil.perfil == "saude":
        if perfil.territorio_esf:
            return queryset.filter(estudante__territorio_esf=perfil.territorio_esf)
        return queryset
    return queryset.none()


def escopo_estudantes(user, queryset):
    if user.is_superuser:
        return queryset
    perfil = getattr(user, "perfil", None)
    if perfil is None:
        return queryset.none()
    if perfil.perfil == "gestao":
        return queryset
    if perfil.perfil == "educacao":
        return queryset.filter(escola=perfil.escola)
    if perfil.perfil == "saude":
        if perfil.territorio_esf:
            return queryset.filter(territorio_esf=perfil.territorio_esf)
        return queryset
    return queryset.none()
