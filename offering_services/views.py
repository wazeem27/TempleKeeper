import csv

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
from django.db import transaction
from django.db.models import F


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

        # Mark the offering as deleted
        offering.is_deleted = True
        offering.name = offering.name + "_" + str(offering.id) + "-deleted"
        # adding id as well to allow to delete multiple offering with same name
        deleted_order = offering.order
        
        # Update all offerings with order > deleted offering's order in bulk
        VazhipaduOffering.objects.filter(
            temple=temple,
            is_deleted=False,
            order__gt=deleted_order
        ).update(order=F('order') - 1)

        # Reset the deleted offering's order
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



class ImportVazhipaduOfferingView(View):

    def post(self, request, *args, **kwargs):
        # Check if a file is in the request
        temple_id = request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)
        if 'csv_file' not in request.FILES:
            messages.error(request, "No file uploaded.")
            return redirect('offerings-list')
        
        csv_file = request.FILES['csv_file']
        
        if not csv_file.name.endswith('.csv'):
            messages.error(request, "Please upload a CSV file.")
            return redirect('offerings-list')

        try:
            # Process the CSV file
            decoded_file = csv_file.read().decode('utf-8').splitlines()
            reader = csv.reader(decoded_file)

            # Skip the header row
            next(reader)
            
            # Loop through the CSV data and import offerings
            added_count = 0
            for row in reader:
                # Assuming CSV format is: Name, Price, Description
                name, price, allow_multiple = row
                order_num = VazhipaduOffering.objects.filter(temple=temple).last().order
                
                # Check if the offering already exists
                if not VazhipaduOffering.objects.filter(name=name, temple=temple).exists():
                    # Create the new offering
                    VazhipaduOffering.objects.create(
                        temple=temple,  # Adjust as per your user's temple info
                        name=name,
                        price=price,
                        allow_multiple=allow_multiple,
                        order=order_num+1
                    )
                    added_count += 1
                else:
                    # Skip if offering exists
                    continue

            # Display success message
            messages.success(request, f"Imported {added_count} new offerings successfully.")
        except Exception as e:
            messages.error(request, f"An error occurred: Please make sure the csv file has only name,price and description")

        return redirect('offerings-list')