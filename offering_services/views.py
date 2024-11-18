from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from temple_auth.models import Temple
from django.views.generic import View
from .forms import VazhipaduOfferingForm
from .models import VazhipaduOffering


@method_decorator(login_required, name='dispatch')
class VazhipaduOfferingView(View):
    template_name = 'offering_services/offering_list.html'

    def get(self, request, *args, **kwargs):
        temple_id = request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)
        offerings = VazhipaduOffering.objects.filter(temple=temple).order_by('id')
        context = {'offerings': offerings, 'temple': temple}
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        form = VazhipaduOfferingForm(request.POST)
        temple_id = request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)

        if form.is_valid():
            offering = form.save(commit=False)
            offering.temple = temple
            if VazhipaduOffering.objects.filter(name=offering.name, temple=offering.temple).exists():
                messages.error(request, f"Offering '{offering.name}' already exists in the temple.")
            else:
                offering.save()
                messages.success(request, f"'{offering.name}' successfully added.")
        else:
            messages.error(request, "Form is not valid.")
        return redirect('offerings-list')


@method_decorator(login_required, name='dispatch')
class VazhipaduOfferingDeleteView(View):
    def post(self, request, *args, **kwargs):
        temple_id = request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)
        offering = get_object_or_404(VazhipaduOffering, id=kwargs.get('pk'), temple=temple)
        offering.delete()
        messages.success(request, f"Offering '{offering.name}' successfully deleted.")
        return redirect('offerings-list')


@method_decorator(login_required, name='dispatch')
class VazhipaduOfferingUpdateView(View):
    template_name = 'offering_services/offering_edit.html'

    def get(self, request, *args, **kwargs):
        temple_id = request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)
        offering = get_object_or_404(VazhipaduOffering, id=kwargs.get('pk'), temple=temple)
        form = VazhipaduOfferingForm(instance=offering)
        context = {'form': form, 'offering': offering, 'temple': temple}
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        temple_id = request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)
        offering = get_object_or_404(VazhipaduOffering, id=kwargs.get('pk'), temple=temple)
        form = VazhipaduOfferingForm(request.POST, instance=offering)
        if form.is_valid():
            form.save()
            messages.success(request, f"Offering '{offering.name}' successfully updated.")
        else:
            messages.error(request, "Invalid data, please correct the errors.")
        return redirect('offerings-list')


@login_required
def offering_main_view(request):
    temple_id = request.session.get('temple_id')
    if not temple_id:
        return redirect('temple_selection')

    temple = get_object_or_404(Temple, id=temple_id)
    return render(request, 'offering_services/offering_main.html', {'temple': temple})