from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from temple_auth.models import Temple
from django.views.generic import View
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.views import View
from .forms import VazhipaduOfferingForm
from .models import VazhipaduOffering
from django.utils.decorators import method_decorator
from django.contrib.auth.mixins import LoginRequiredMixin
from billing_manager.decorators import check_temple_session


@method_decorator(check_temple_session, name='dispatch')
class VazhipaduOfferingView(LoginRequiredMixin, View):
    template_name = 'offering_services/offering_list.html'

    def get(self, request, *args, **kwargs):
        temple_id = request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)

        is_billing_assistant = request.user.groups.filter(name='Billing Assistant').exists()


        offerings = VazhipaduOffering.objects.filter(temple=temple, is_deleted=False).order_by('order')
        is_central_admin = self.request.user.groups.filter(name='Central Admin').exists()
        context = {
            'offerings': offerings, 'temple': temple, 'is_billing_assistant': is_billing_assistant,
            'is_central_admin': is_central_admin
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        form = VazhipaduOfferingForm(request.POST)
        temple_id = request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)

        if form.is_valid():
            offering = form.save(commit=False)
            offering.temple = temple
            current_temple_vazhipadu = VazhipaduOffering.objects.filter(temple=temple)
            order_num = current_temple_vazhipadu.last().order + 1 if current_temple_vazhipadu.last() else 1
            offering.order = order_num
            if VazhipaduOffering.objects.filter(name=offering.name, temple=offering.temple).exists():
                messages.error(request, f"Offering '{offering.name}' already exists in the temple.")
            else:
                offering.save()
                messages.success(request, f"'{offering.name}' successfully added.")
        else:
            messages.error(request, "Form is not valid.")
        return redirect('offerings-list')


@method_decorator(check_temple_session, name='dispatch')
class VazhipaduOfferingDeleteView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        temple_id = request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)
        offering = get_object_or_404(VazhipaduOffering, id=kwargs.get('pk'), temple=temple)
        offering.is_deleted = True
        deleted_order = offering.order
        offering_list = VazhipaduOffering.objects.filter(temple=temple, is_deleted=False, order__gt=offering.order)
        for offg in offering_list:
            offg.order -= 1
            offg.save() 
        offering.order = 0
        offering.save()
        messages.success(request, f"Offering '{offering.name}' successfully deleted.")
        return redirect('offerings-list')


@method_decorator(check_temple_session, name='dispatch')
class VazhipaduOfferingUpdateView(LoginRequiredMixin, View):
    template_name = 'offering_services/offering_edit.html'

    def get(self, request, *args, **kwargs):
        temple_id = request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)
        offering = get_object_or_404(VazhipaduOffering, id=kwargs.get('pk'), temple=temple)
        form = VazhipaduOfferingForm(instance=offering)
        is_central_admin = self.request.user.groups.filter(name='Central Admin').exists()
        context = {'form': form, 'offering': offering, 'temple': temple, 'is_central_admin': is_central_admin}
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
@check_temple_session
def offering_main_view(request):
    temple_id = request.session.get('temple_id')
    if not temple_id:
        return redirect('temple_selection')

    temple = get_object_or_404(Temple, id=temple_id)
    return render(request, 'offering_services/offering_main.html', {'temple': temple})



@method_decorator(csrf_exempt, name='dispatch')
@method_decorator(check_temple_session, name='dispatch')
class UpdateOrderView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        import json
        from django.http import JsonResponse

        try:
            data = json.loads(request.body)

            if not isinstance(data, list):
                return JsonResponse({'success': False, 'error': 'Invalid data format. Expected a list.'})

            for item in data:
                if item['id'] == item['order']:
                    return JsonResponse({'success': False, 'error': 'ID and Order cannot be the same'})

            # Bulk update (optimized)
            updates = [
                VazhipaduOffering(id=item['id'], order=item['order'])
                for item in data
            ]
            VazhipaduOffering.objects.bulk_update(updates, ['order'])

            return JsonResponse({'success': True})

        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})