from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from usuarios.forms import (
    BootstrapPasswordChangeForm,
    BootstrapPasswordResetForm,
    BootstrapSetPasswordForm,
)
from usuarios.views import limpar_log_auditoria_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("tasks/limpar-log-auditoria/", limpar_log_auditoria_view, name="limpar_log_auditoria"),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path(
        "password_reset/",
        auth_views.PasswordResetView.as_view(
            template_name="registration/password_reset_form.html",
            form_class=BootstrapPasswordResetForm,
        ),
        name="password_reset",
    ),
    path(
        "password_reset/concluido/",
        auth_views.PasswordResetDoneView.as_view(template_name="registration/password_reset_done.html"),
        name="password_reset_done",
    ),
    path(
        "resetar-senha/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="registration/password_reset_confirm.html",
            form_class=BootstrapSetPasswordForm,
        ),
        name="password_reset_confirm",
    ),
    path(
        "resetar-senha/concluido/",
        auth_views.PasswordResetCompleteView.as_view(template_name="registration/password_reset_complete.html"),
        name="password_reset_complete",
    ),
    path(
        "trocar-senha/",
        auth_views.PasswordChangeView.as_view(
            template_name="registration/password_change_form.html",
            form_class=BootstrapPasswordChangeForm,
        ),
        name="password_change",
    ),
    path(
        "trocar-senha/concluido/",
        auth_views.PasswordChangeDoneView.as_view(template_name="registration/password_change_done.html"),
        name="password_change_done",
    ),
    path("", include("indicadores.urls")),
    path("casos/", include("casos.urls")),
    path("estudantes/", include("estudantes.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
