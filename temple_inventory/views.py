from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from temple_auth.models import Temple
from .models import InventoryItem
from .forms import InventoryItemForm



@method_decorator(login_required, name='dispatch')
class InventoryItemView(View):
    template_name = 'inventory/inventory.html'

    def get(self, request, *args, **kwargs):
        temple_id = request.session.get('selected_temple_id')
        temple = get_object_or_404(Temple, id=temple_id)
        items = InventoryItem.objects.filter(temple=temple).order_by('name')
        context = {'items': items, 'temple': temple}
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        form = InventoryItemForm(request.POST)
        temple_id = request.session.get('selected_temple_id')
        temple = get_object_or_404(Temple, id=temple_id)

        if form.is_valid():
            item = form.save(commit=False)
            item.temple = temple
            if InventoryItem.objects.filter(name=item.name, temple=item.temple).exists():
                messages.error(request, f"Item '{item.name}' already exists in the temple.")
            else:
                item.save()
                messages.success(request, f"'{item.name}' successfully added.")
        else:
            messages.error(request, "Form is not valid.")
        return redirect('inventory_list')


@method_decorator(login_required, name='dispatch')
class InventoryItemDeleteView(View):
    def post(self, request, *args, **kwargs):
        temple_id = request.session.get('selected_temple_id')
        temple = get_object_or_404(Temple, id=temple_id)
        item = get_object_or_404(InventoryItem, id=kwargs.get('pk'), temple=temple)
        item.delete()
        messages.success(request, f"Item '{item.name}' successfully deleted.")
        return redirect('inventory_list')


@method_decorator(login_required, name='dispatch')
class InventoryItemUpdateView(View):
    template_name = 'inventory/edit_item.html'

    def get(self, request, *args, **kwargs):
        temple_id = request.session.get('selected_temple_id')
        temple = get_object_or_404(Temple, id=temple_id)
        item = get_object_or_404(InventoryItem, id=kwargs.get('pk'), temple=temple)
        form = InventoryItemForm(instance=item)
        context = {'form': form, 'item': item, 'temple': temple}
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        temple_id = request.session.get('selected_temple_id')
        temple = get_object_or_404(Temple, id=temple_id)
        item = get_object_or_404(InventoryItem, id=kwargs.get('pk'), temple=temple)
        form = InventoryItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, f"Item '{item.name}' successfully updated.")
        else:
            messages.error(request, "Invalid data, please correct the errors.")
        return redirect('inventory_list')
