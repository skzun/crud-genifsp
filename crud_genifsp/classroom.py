"""Function views and URLs in the layout of the My Tennis Club lessons."""


def list_view_name(app, model):
    reserved = {
        model, model + "Form", "Paginator", "get_object_or_404", "redirect", "render",
        "ProtectedError", "RestrictedError", "require_safe", "require_POST",
        "require_http_methods", "details", "add", "addrecord", "delete", "update", "updaterecord",
    }
    return "list_records" if app in reserved else app


def urls_source(app, model):
    listing = list_view_name(app, model)
    return f'''from django.urls import path
from . import views

app_name = '{app}'

urlpatterns = [
    path('{app}/', views.{listing}, name='{app}'),
    path('{app}/details/<int:id>', views.details, name='details'),
    path('{app}/add/', views.add, name='add'),
    path('{app}/add/addrecord/', views.addrecord, name='addrecord'),
    path('{app}/delete/<int:id>', views.delete, name='delete'),
    path('{app}/update/<int:id>', views.update, name='update'),
    path('{app}/update/updaterecord/<int:id>', views.updaterecord, name='updaterecord'),
]
'''


def views_source(app, model):
    listing = list_view_name(app, model)
    return f'''from django.core.paginator import Paginator
from django.db.models.deletion import ProtectedError, RestrictedError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST, require_safe

from .forms import {model}Form
from .models import {model}


@require_safe
def {listing}(request):
    records = {model}.objects.order_by('id')
    page_obj = Paginator(records, 20).get_page(request.GET.get('page'))
    context = {{'object_list': page_obj, 'page_obj': page_obj}}
    return render(request, '{app}/all_{app}.html', context)


@require_safe
def details(request, id):
    record = get_object_or_404({model}, pk=id)
    return render(request, '{app}/details.html', {{'object': record}})


@require_safe
def add(request):
    form = {model}Form()
    return render(request, '{app}/add.html', {{'form': form}})


@require_POST
def addrecord(request):
    form = {model}Form(request.POST, request.FILES)
    if form.is_valid():
        form.save()
        return redirect('{app}:{app}')
    return render(request, '{app}/add.html', {{'form': form}})


@require_http_methods(['GET', 'HEAD', 'POST'])
def delete(request, id):
    record = get_object_or_404({model}, pk=id)
    context = {{'object': record}}
    if request.method == 'POST':
        try:
            record.delete()
        except (ProtectedError, RestrictedError):
            context['error'] = 'Este registro possui vínculos. Exclua os registros relacionados primeiro.'
            return render(request, '{app}/confirm_delete.html', context, status=409)
        return redirect('{app}:{app}')
    return render(request, '{app}/confirm_delete.html', context)


@require_safe
def update(request, id):
    record = get_object_or_404({model}, pk=id)
    context = {{'object': record, 'form': {model}Form(instance=record)}}
    return render(request, '{app}/update.html', context)


@require_POST
def updaterecord(request, id):
    record = get_object_or_404({model}, pk=id)
    form = {model}Form(request.POST, request.FILES, instance=record)
    if form.is_valid():
        form.save()
        return redirect('{app}:{app}')
    return render(request, '{app}/update.html', {{'object': record, 'form': form}})
'''
