from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from temple_auth.models import Temple
from django.views.generic import View
from .models import InventoryItem
from .forms import InventoryItemForm



@method_decorator(login_required, name='dispatch')
class InventoryItemView(View):
    template_name = 'temple_inventory/inventory_list.html'

    def get(self, request, *args, **kwargs):
        temple_id = request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)
        items = InventoryItem.objects.filter(temple=temple).order_by('id')
        context = {'items': items, 'temple': temple}
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        form = InventoryItemForm(request.POST)
        temple_id = request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)

        if form.is_valid():
            item = form.save(commit=False)
            item.temple = temple
            if InventoryItem.objects.filter(name=item.name, temple=item.temple).exists():
                messages.error(request, f"ഐറ്റം '{item.name}' ക്ഷേത്രത്തിൽ ഇതിനകം നിലവിലുണ്ട്.")
            else:
                item.save()
                messages.success(request, f"ഐറ്റം '{item.name}' ചേർത്തിരിക്കുന്നു.")
        else:
            import ipdb;ipdb.set_trace()
            messages.error(request, "കൊടുതിരിക്കുന്നേ വിഷദാആംശം ശരി അല്ലാ.")
        return redirect('inventory-list')


@method_decorator(login_required, name='dispatch')
class InventoryItemDeleteView(View):
    def post(self, request, *args, **kwargs):
        temple_id = request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)
        item = get_object_or_404(InventoryItem, id=kwargs.get('pk'), temple=temple)
        item.delete()
        messages.success(request, f"ഐറ്റം '{item.name}' നീക്കം ചെയ്‌തിരിക്കുന്നു.")
        return redirect('inventory-list')


@method_decorator(login_required, name='dispatch')
class InventoryItemUpdateView(View):
    template_name = 'temple_inventory/inventory_edit.html'

    def get(self, request, *args, **kwargs):
        temple_id = request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)
        item = get_object_or_404(InventoryItem, id=kwargs.get('pk'), temple=temple)
        form = InventoryItemForm(instance=item)
        context = {'form': form, 'item': item, 'temple': temple}
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        temple_id = request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)
        item = get_object_or_404(InventoryItem, id=kwargs.get('pk'), temple=temple)
        form = InventoryItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, f"ഐറ്റം '{item.name}' അപ്ഡേറ്റ് ചെയ്‌തിരിക്കുന്നു.")
        else:
            messages.error(request, "കൊടുതിരിക്കുന്നേ വിഷദാആംശം ശരി അല്ലാ.")
        return redirect('inventory-list')
