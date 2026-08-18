from django import forms
from django.contrib.auth.forms import PasswordChangeForm, PasswordResetForm, SetPasswordForm


class BootstrapFormMixin:
    """Aplica a classe 'form-control' (ou 'form-check-input' para checkboxes) a todos os campos."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault("class", "form-check-input")
            else:
                field.widget.attrs.setdefault("class", "form-control")


class BootstrapPasswordResetForm(BootstrapFormMixin, PasswordResetForm):
    pass


class BootstrapSetPasswordForm(BootstrapFormMixin, SetPasswordForm):
    pass


class BootstrapPasswordChangeForm(BootstrapFormMixin, PasswordChangeForm):
    pass
