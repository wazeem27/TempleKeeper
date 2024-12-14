from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpRequest
from django.views.generic import TemplateView, ListView, DetailView, View
from django.db import transaction
from django.contrib import messages
from django.urls import reverse
from .models import WalletCollection
from decimal import Decimal
import csv
import re
from django.urls import reverse_lazy
from django.views.generic.edit import FormView
from django.http import JsonResponse, Http404
from .forms import WalletCollectionForm
from .services import WalletService
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.http import HttpResponseForbidden
from django.core.exceptions import ValidationError
from datetime import datetime, time
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from temple_inventory.models import InventoryItem
from offering_services.models import VazhipaduOffering, Star
from temple_auth.models import Temple
from collections import defaultdict
from django.utils.timezone import localtime
from billing_manager.models import Bill, BillOther, BillVazhipaduOffering, PersonDetail
from typing import Dict, Any
from temple_auth.models import UserProfile


subreceipt_ids = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p']

class BillingView(LoginRequiredMixin, TemplateView):
    template_name = "billing_manager/create_bill.html"

    def get_inventory_queryset(self, temple: Temple) -> Any:
        return InventoryItem.objects.filter(temple=temple)

    def get_vazhipadu_queryset(self, temple: Temple) -> Any:
        return VazhipaduOffering.objects.filter(temple=temple).order_by('order')

    def get_star_queryset(self) -> Any:
        return Star.objects.all().order_by('id')

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        
        temple_id = self.request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)
        
        context['vazhipadu_items'] = self.get_vazhipadu_queryset(temple)
        context['inventory_items'] = self.get_inventory_queryset(temple)
        context['star_items'] = self.get_star_queryset()
        context['temple'] = temple

        multi_support_vazhipadu = [
            vazhipadu.name for vazhipadu in
            VazhipaduOffering.objects.filter(temple=temple, allow_multiple=True)
        ]
        context['multi_support_vazhipadu'] = multi_support_vazhipadu
        return context

class BillListView(LoginRequiredMixin, ListView):
    model = Bill
    template_name = 'billing_manager/bill_list.html'
    context_object_name = 'bills'
    paginate_by = 100


    def get_queryset(self):
        """
        Returns a filtered queryset for the bills. This method is used to provide the base
        queryset for filtering but we will manually construct and paginate the dataset.
        """
        temple_id = self.request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)

        # Get the filter parameters from the GET request
        start_date_str = self.request.GET.get('start_date', '')
        end_date_str = self.request.GET.get('end_date', '')
        requested_biller = self.request.GET.getlist('req_biller')


        start_date = parse_date(start_date_str) if start_date_str else None
        end_date = parse_date(end_date_str) if end_date_str else None
        
        is_billing_assistant = self.request.user.groups.filter(name='Billing Assistant').exists()
        
        # Convert to timezone-aware datetime if needed
        if start_date:
            start_date = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))  # 00:00:00
        if end_date:
            # Set end_date to the last moment of the day (23:59:59)
            end_date = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))  # 23:59:59

        if is_billing_assistant:
            # Only bills related to the current user (Billing Assistant)
            bills = Bill.objects.filter(temple=temple, user=self.request.user).order_by('id')
            if start_date:
                bills = bills.filter(created_at__gte=start_date)
            if end_date:
                bills = bills.filter(created_at__lte=end_date)

        else:
            # All bills if not a Billing Assistant
            bills = Bill.objects.filter(temple=temple).order_by('id')
            if requested_biller:
                bills = bills.filter(user__username=requested_biller[0])

            if start_date:
                bills = bills.filter(created_at__gte=start_date)
            if end_date:
                bills = bills.filter(created_at__lte=end_date)

        return bills


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get temple details
        temple_id = self.request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)
        context['temple'] = temple

        # Use paginated bills for the current page
        bill_dataset = []
        bills = []
        is_billing_assistant = self.request.user.groups.filter(name='Billing Assistant').exists()
        context['is_billing_assistant'] = is_billing_assistant

        
        for bill in context['bills']:
            vazhipadu_list = bill.bill_vazhipadu_offerings.all()
            sub_receipt_counter = "abcdefghijklmnopqrstuvwxyz"
            counter = 0

            # Construct the dataset
            for vazhipadu_bill in vazhipadu_list:
                subreceipt = '-' if len(vazhipadu_list) == 1 else sub_receipt_counter[counter]

                bill_entry = {
                    'receipt': bill.id,
                    'sub_receipt': subreceipt,
                    'created_at': localtime(bill.created_at).strftime("%a, %d %b %Y, %-I:%M %p"),
                    'created_by': bill.user.username,
                    'vazhipadu_name': vazhipadu_bill.vazhipadu_offering.name,
                    'name': ",".join([vazhipadu.person_name for vazhipadu in vazhipadu_bill.person_details.all()]),
                    'star': ",".join([vazhipadu.person_star.name for vazhipadu in vazhipadu_bill.person_details.all()]),
                    'amount': vazhipadu_bill.price,
                    'is_cancelled': bill.is_cancelled,
                    'payment_method': bill.payment_method,
                    'cancel_reason': bill.cancel_reason
                }
                bill_dataset.append(bill_entry)
                counter +=1
            other_list = bill.bill_other_items.all()
            # Construct the dataset
            for other_bill in other_list:
                subreceipt = '-' if len(vazhipadu_list) == 1 else sub_receipt_counter[counter]

                bill_entry = {
                    'receipt': bill.id,
                    'sub_receipt': subreceipt,
                    'created_at': localtime(bill.created_at).strftime("%a, %d %b %Y, %-I:%M %p"),
                    'created_by': bill.user.username,
                    'vazhipadu_name': other_bill.vazhipadu,
                    'name': other_bill.person_name,
                    'star': other_bill.person_star.name if other_bill.person_star.name else "",
                    'amount': other_bill.price,
                    'is_cancelled': bill.is_cancelled,
                    'cancel_reason': bill.cancel_reason,
                    'payment_method': bill.payment_method

                }
                bill_dataset.append(bill_entry)       
                counter += 1     

        # Add paginated dataset and filters to the context
        req_vazhipadu = self.request.GET.getlist('req_vazhipadu')
        if req_vazhipadu:
            bill_dataset = [bill for bill in bill_dataset if bill["vazhipadu_name"] == req_vazhipadu[0]]

        vazhipadu_items = VazhipaduOffering.objects.filter(temple=temple).order_by('order')
        context["vazhipadu_items"] = [i.name for i in vazhipadu_items]


        context['bills'] = bill_dataset
        user_profiles = UserProfile.objects.filter(temples__id=temple_id)
        context['user_list'] = [usr_prof.user.username for usr_prof in user_profiles]
        context['search_query'] = self.request.GET.get('q', '')
        context['start_date'] = self.request.GET.get('start_date', '')
        context['req_vazhipadu'] = req_vazhipadu[0] if req_vazhipadu else ""
        context['end_date'] = self.request.GET.get('end_date', '')

        return context


def parse_nested_querydict(querydict):
    data = querydict.dict()  # Converts QueryDict to a dictionary
    result = {
        "parents": [],
        "payment_method": querydict.get("payment_method", ""),
        "gap_amount": querydict.get("gap_amount", ""),
    }

    # Regex to identify parent keys and child keys
    parent_regex = re.compile(r"parent\[(\d+)\]\[([^\]]+)\]")  # e.g., parent[1][name]
    child_regex = re.compile(r"parent\[(\d+)\]\[children\]\[(\d+)\]\[([^\]]+)\]")  # e.g., parent[1][children][2][name]

    # Containers for parent and child data
    parents = defaultdict(dict)
    children = defaultdict(lambda: defaultdict(dict))  # {parent_id: {child_id: {child_data}}}

    for key, value in data.items():
        # Match parent fields
        parent_match = parent_regex.match(key)
        if parent_match:
            parent_id, field = parent_match.groups()
            parents[parent_id][field] = value

        # Match child fields
        child_match = child_regex.match(key)
        if child_match:
            parent_id, child_id, field = child_match.groups()
            children[parent_id][child_id][field] = value

    # Combine parents and their respective children
    for parent_id, parent_data in parents.items():
        parent_data["children"] = list(children[parent_id].values())
        result["parents"].append(parent_data)

    return result





class SubmitBill(LoginRequiredMixin, View):
    template_name = "bill/create_bill.html"

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        try:
            # Parse and validate input data
            data = parse_nested_querydict(request.POST)
            temple = self._get_temple(request.session)
            parents = self._validate_parents_data(data)

            # Calculate total price
            total_price = sum(float(parent["price"]) for parent in parents)

            user_profile = get_object_or_404(UserProfile, user=request.user, temples__id=temple.id)

            if user_profile.is_split_bill:
                person_details = []  # Collect all PersonDetail objects for bulk creation
                # Create separate bills for each offering or item
                bill_objects = []

                for parent in parents:
                    bill = self._create_bill(request, temple, float(parent.get('price')), data.get("payment_method", "cash"))
                    bill.save()
                    bill_objects.append(bill)
                    # Save BillVazhipaduOffering (cannot use bulk_create due to unsaved related object)
                    vazhipadu_offering = get_object_or_404(
                        VazhipaduOffering, name=parent["pooja"], temple=temple
                    )
                    # Save vazhipadu offering
                    vazhipadu_bill = BillVazhipaduOffering.objects.create(
                        bill=bill,
                        vazhipadu_offering=vazhipadu_offering,
                        quantity=1,
                        price=parent["price"]
                    )
                    # Add parent person detail
                    person_details.append(
                        PersonDetail(
                            bill_vazhipadu_offering=vazhipadu_bill,
                            person_name=parent["name"],
                            person_star=get_object_or_404(Star, name=parent["nakshatram"])
                        )
                    )

                    # Add child person details
                    for child in parent.get("children", []):
                        person_details.append(
                            PersonDetail(
                                bill_vazhipadu_offering=vazhipadu_bill,
                                person_name=child["name"],
                                person_star=get_object_or_404(Star, name=child["nakshatram"])
                            )
                        )  
                    # Bulk create PersonDetail objects
                    PersonDetail.objects.bulk_create(person_details)

                bill_ids = ",".join([str(bill.id) for bill in bill_objects])
                for bill in bill_objects:
                    bill.related_bills = bill_ids
                    bill.save()

                query_string = f"ids={'&'.join(map(str, [bill.id for bill in bill_objects]))}"
                url = f"{reverse('view_multi_receipt')}?{query_string}"
                return redirect(url)
                
            else:
                # Step 1: Create the main bill
                bill = self._create_bill(request, temple, total_price, data.get("payment_method", "cash"))
                bill.save()

                # Step 2: Process VazhipaduOfferings and PersonDetails
                person_details = []  # Collect all PersonDetail objects for bulk creation
                for parent in parents:
                    vazhipadu_offering = get_object_or_404(
                        VazhipaduOffering, name=parent["pooja"], temple=temple
                    )

                    # Save BillVazhipaduOffering (cannot use bulk_create due to unsaved related object)
                    vazhipadu_bill = BillVazhipaduOffering.objects.create(
                        bill=bill,
                        vazhipadu_offering=vazhipadu_offering,
                        quantity=1,
                        price=parent["price"]
                    )

                    # Add parent person detail
                    person_details.append(
                        PersonDetail(
                            bill_vazhipadu_offering=vazhipadu_bill,
                            person_name=parent["name"],
                            person_star=get_object_or_404(Star, name=parent["nakshatram"])
                        )
                    )

                    # Add child person details
                    for child in parent.get("children", []):
                        person_details.append(
                            PersonDetail(
                                bill_vazhipadu_offering=vazhipadu_bill,
                                person_name=child["name"],
                                person_star=get_object_or_404(Star, name=child["nakshatram"])
                            )
                        )

                # Bulk create PersonDetail objects
                PersonDetail.objects.bulk_create(person_details)

                # Return success response
                return redirect(reverse('receipt', kwargs={'pk': bill.id}))

        except ValidationError as e:
            return JsonResponse({"status": "failure", "error": str(e)}, status=400)
        except ObjectDoesNotExist as e:
            return JsonResponse({"status": "failure", "error": f"Data not found: {str(e)}"}, status=404)
        except Exception as e:
            # Log error for internal debugging
            return JsonResponse({"status": "failure", "error": f"An unexpected error occurred: {str(e)}"}, status=500)

    def _get_temple(self, session):
        temple_id = session.get("temple_id")
        if not temple_id:
            raise ValidationError("Temple ID is missing from the session.")
        return get_object_or_404(Temple, id=temple_id)

    def _validate_parents_data(self, data):
        parents = data.get("parents", [])
        if not parents:
            raise ValidationError("Parents data is required to create a bill.")
        for parent in parents:
            if "pooja" not in parent or "price" not in parent or "name" not in parent or "nakshatram" not in parent:
                raise ValidationError("Each parent must include 'pooja', 'price', 'name', and 'nakshatram' fields.")
            if "children" in parent:
                for child in parent["children"]:
                    if "name" not in child or "nakshatram" not in child:
                        raise ValidationError("Each child must include 'name' and 'nakshatram' fields.")
        return parents

    def _create_bill(self, request, temple, total_price, payment_method):
        if total_price <= 0:
            raise ValidationError("Total price must be greater than zero.")
        return Bill(
            user=request.user,
            temple=temple,
            total_amount=Decimal(total_price),
            payment_method=payment_method
        )

# @login_required
# def submit_billing(request: HttpRequest) -> HttpResponse:
#     """Handle billing submission and create associated records for the specified temple."""
#     if request.method == 'POST':
#         # Retrieve temple from the session
        
#         temple_id = request.session.get('temple_id')
#         temple = get_object_or_404(Temple, id=temple_id)
#         data = parse_nested_querydict(request.POST)

#         # Calculate total price
#         total_price = sum(float(parent['price']) for parent in data['parents'])
#         payment_method = data.get("payment_method", "cash")

#         import ipdb;ipdb.set_trace()


#         # Retrieve user profile for split bill preference
#         user_profile = get_object_or_404(UserProfile, user=request.user, temples__id=temple_id)

#         # Begin transaction to ensure atomicity
#         try:
#             with transaction.atomic():
#                 if user_profile.is_split_bill:
#                     # Create separate bills for each offering or item
#                     bill_objects = []

#                     if request.POST.getlist('pooja[]'):
#                         names = request.POST.getlist('name[]')
#                         vazhipadu_list = request.POST.getlist('pooja[]')
#                         stars = request.POST.getlist('nakshatram[]')
#                         vazhipadu_prices = request.POST.getlist('pooja_price[]')
                        
#                         for index, vazhipadu_name in enumerate(vazhipadu_list):
#                             if vazhipadu_name.strip():
#                                 vazhipadu_offering = get_object_or_404(
#                                     VazhipaduOffering, name=vazhipadu_name, temple=temple)
#                                 price = Decimal(vazhipadu_prices[index])
#                                 customer_star = get_object_or_404(Star, name=stars[index])

#                                 # Create a new bill for this offering
#                                 bill = Bill.objects.create(
#                                     user=request.user,
#                                     temple=temple,
#                                     total_amount=price,
#                                     payment_method=payment_method
#                                 )
#                                 bill_objects.append(bill)

#                                 # Create associated BillVazhipaduOffering record
#                                 BillVazhipaduOffering.objects.create(
#                                     bill=bill,
#                                     vazhipadu_offering=vazhipadu_offering,
#                                     person_name=names[index],
#                                     person_star=customer_star,
#                                     quantity=1,
#                                     price=price
#                                 )

#                     if request.POST.getlist('other_name[]'):
#                         other_names = request.POST.getlist('other_name[]')
#                         other_stars = request.POST.getlist('other_nakshatram[]')
#                         other_vazhipadugal = request.POST.getlist('other_vazhipadu[]')
#                         other_prices = request.POST.getlist('other_price[]')

#                         for index, other_name in enumerate(other_names):
#                             if other_name.strip():
#                                 other_star = get_object_or_404(Star, name=other_stars[index])
#                                 vazhipadu = other_vazhipadugal[index]
#                                 price = Decimal(other_prices[index])

#                                 # Create a new bill for this inventory item
#                                 bill = Bill.objects.create(
#                                     user=request.user,
#                                     temple=temple,
#                                     total_amount=price
#                                 )
#                                 bill_objects.append(bill)

#                                 # Create associated BillInventoryItem record
#                                 BillOther.objects.create(
#                                     bill=bill,
#                                     person_name=other_name,
#                                     person_star=other_star,
#                                     vazhipadu=vazhipadu,
#                                     price=price
#                                 )
#                     bill_ids = ",".join([str(bill.id) for bill in bill_objects])
#                     for bill in bill_objects:
#                         bill.related_bills = bill_ids
#                         bill.save()

#                     messages.success(request, "Separate bills have been successfully recorded.")
#                     query_string = f"ids={'&'.join(map(str, [bill.id for bill in bill_objects]))}"
#                     url = f"{reverse('view_multi_receipt')}?{query_string}"
#                     return redirect(url)

#                 else:
#                     # Create a single consolidated bill
#                     total_pooja_price = total_price
#                     bill = Bill.objects.create(
#                         user=request.user,
#                         temple=temple,
#                         total_amount=Decimal(total_pooja_price),
#                         payment_method=payment_method
#                     )


#                     # New way of Implementation here...............................

#                     for vazhipadu_detail in data.get("parents", []):
#                         vazhipadu_offering = get_object_or_404(
#                             VazhipaduOffering, name=vazhipadu_detail.get('pooja'), temple=temple
#                         )
#                         vazhipadu_bill = BillVazhipaduOffering.objects.create(
#                             bill=bill,
#                             vazhipadu_offering=vazhipadu_offering,
#                             quantity=1,
#                             price=vazhipadu_detail.get('price')
#                         )

#                         # Vazhipadu Bill created now add person details to vazhipadu
#                         person_detail = PersonDetail.objects.create(
#                             bill_vazhipadu_offering=vazhipadu_bill,
#                             person_name=vazhipadu_detail.get('name'),
#                             star=get_object_or_404(Star, name=vazhipadu_detail.get('nakshatram')),
#                         )
#                         for other_person in vazhipadu_detail.get('children'):
#                             person_detail = PersonDetail.objects.create(
#                                 bill_vazhipadu_offering=vazhipadu_bill,
#                                 person_name=other_person.get('name'),
#                                 star=get_object_or_404(Star, name=other_person.get('nakshatram')),
#                             )

                        

                    # End #########################################################



                    # # Add offerings to the single bill
                    # if request.POST.getlist('pooja[]'):
                    #     names = request.POST.getlist('name[]')
                    #     vazhipadu_list = request.POST.getlist('pooja[]')
                    #     stars = request.POST.getlist('nakshatram[]')
                    #     vazhipadu_prices = request.POST.getlist('pooja_price[]')

                    #     for index, vazhipadu_name in enumerate(vazhipadu_list):
                    #         if vazhipadu_name.strip():
                    #             vazhipadu_offering = get_object_or_404(
                    #                 VazhipaduOffering, name=vazhipadu_name, temple=temple)
                    #             price = Decimal(vazhipadu_prices[index])
                    #             customer_star = get_object_or_404(Star, name=stars[index])

                    #             BillVazhipaduOffering.objects.create(
                    #                 bill=bill,
                    #                 vazhipadu_offering=vazhipadu_offering,
                    #                 person_name=names[index],
                    #                 person_star=customer_star,
                    #                 quantity=1,
                    #                 price=price
                    #             )

                    # # Add inventory items to the single bill
                    # if request.POST.getlist('other_name[]'):
                    #     other_names = request.POST.getlist('other_name[]')
                    #     other_stars = request.POST.getlist('other_nakshatram[]')
                    #     other_vazhipadugal = request.POST.getlist('other_vazhipadu[]')
                    #     other_prices = request.POST.getlist('other_price[]')

                    #     for index, other_name in enumerate(other_names):
                    #         if other_name.strip():
                    #             other_star = get_object_or_404(Star, name=other_stars[index])
                    #             vazhipadu = other_vazhipadugal[index]
                    #             price = Decimal(other_prices[index])

                    #             BillOther.objects.create(
                    #                 bill=bill,
                    #                 person_name=other_name,
                    #                 person_star=other_star,
                    #                 vazhipadu=vazhipadu,
                    #                 price=price,
                    #                 payment_method=payment_method
                    #             )

    #                 messages.success(request, "Billing details have been successfully recorded.")
    #                 return redirect(reverse('receipt', kwargs={'pk': bill.id}))

    #     except Exception as e:
    #         # Rollback transaction on error
    #         messages.error(request, f"An error occurred while processing the billing: {e}")
    #         return redirect('add-bill')

    # messages.error(request, "Invalid request method.")
    # return redirect('add-bill')




class BillDetailView(LoginRequiredMixin, DetailView):
    model = Bill
    template_name = "billing_manager/bill_detail.html"
    context_object_name = "bill"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add any additional data if necessary
        temple_id = self.request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)
        context['temple'] = temple
        return context


class ReceiptView(LoginRequiredMixin, DetailView):
    model = Bill
    context_object_name = "bill"

    def get_template_names(self):
        # Retrieve the current user profile
        user_profile = UserProfile.objects.filter(user=self.request.user)[0]
        if user_profile.is_split_bill:
            # If the user has selected split billing, return the split receipt template
            return ["billing_manager/receipt.html"]
        else:
            # Otherwise, return the standard receipt template
            return ["billing_manager/receipt.html"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Retrieve the current temple from the session
        temple_id = self.request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)
        context["temple"] = temple

        bill_detail = {"total_amount": self.get_object().total_amount, "vazhipadu_list": []}
        
        for vazhipadu in self.get_object().bill_vazhipadu_offerings.all():
            vazhipadu_detail = {
                "vazhipadu": vazhipadu.vazhipadu_offering.name,
                "price": vazhipadu.vazhipadu_offering.price,
                "primary_person": None,
                "other_persons": []
            }
            
            # Retrieve all person details for the current vazhipadu
            persons = vazhipadu.person_details.all()
            
            # Separate the first person from the rest
            if persons.exists():
                first_person = persons[0]
                vazhipadu_detail["primary_person"] = {
                    "name": first_person.person_name,
                    "star": first_person.person_star.name
                }
                
                # Handle the remaining persons
                for person in persons[1:]:
                    vazhipadu_detail["other_persons"].append({
                        "name": person.person_name,
                        "star": person.person_star.name
                    })
            
            bill_detail["vazhipadu_list"].append(vazhipadu_detail)
        
        context["bill_detail"] = bill_detail
        return context



class ViewMultiReceipt(LoginRequiredMixin, TemplateView):
    template_name = "billing_manager/new_bill_receipt.html"

def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)

    # Fetch the temple based on session data
    temple_id = self.request.session.get('temple_id')
    temple = get_object_or_404(Temple, id=temple_id)
    context['temple'] = temple

    # Get the list of bill IDs from query parameters
    query_string = self.request.META.get('QUERY_STRING', '')
    bill_ids = query_string.split('=')[1].split(',') if '=' in query_string else []

    # Fetch bills belonging to the temple
    bills = Bill.objects.filter(id__in=bill_ids, temple_id=temple_id)
    bill_list = []

    for bill in bills:
        bill_dict = {
            "id": bill.id,
            "date": bill.created_at,
            "vazhipadu_list": []
        }

        # Add vazhipadu offerings for the bill
        for vazhipadu in bill.bill_vazhipadu_offerings.all():
            vazhipadu_detail = {
                "vazhipadu": vazhipadu.vazhipadu_offering.name,
                "price": vazhipadu.vazhipadu_offering.price,
                "primary_person": None,
                "other_persons": []
            }

            # Fetch person details
            persons = vazhipadu.person_details.all()
            if persons.exists():
                # Separate the first person
                first_person = persons[0]
                vazhipadu_detail["primary_person"] = {
                    "name": first_person.person_name,
                    "star": first_person.person_star.name
                }
                # Add remaining persons
                for person in persons[1:]:
                    vazhipadu_detail["other_persons"].append({
                        "name": person.person_name,
                        "star": person.person_star.name
                    })

            bill_dict["vazhipadu_list"].append(vazhipadu_detail)

        # If no vazhipadu offerings, handle other items
        if not bill.bill_vazhipadu_offerings.exists():
            for other_item in bill.bill_other_items.all():
                other_detail = {
                    "vazhipadu": other_item.vazhipadu,
                    "price": other_item.price,
                    "primary_person": {
                        "name": other_item.person_name,
                        "star": other_item.person_star.name
                    },
                    "other_persons": []
                }
                bill_dict["vazhipadu_list"].append(other_detail)

        bill_list.append(bill_dict)

    context['bills'] = bill_list
    return context


class BillExportView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        # Get filter parameters from the request
        start_date_str = request.GET.get('start_date', '')
        end_date_str = request.GET.get('end_date', '')
        search_query = request.GET.get('q', '')

        start_date = parse_date(start_date_str) if start_date_str else None
        end_date = parse_date(end_date_str) if end_date_str else None

        # Filter bills based on the same logic as the get_queryset method
        temple_id = request.session.get('temple_id')
        temple = get_object_or_404(Temple, id=temple_id)

        is_billing_assistant = request.user.groups.filter(name='Billing Assistant').exists()
        
        bills = Bill.objects.all().order_by('id')

        if is_billing_assistant:
            bills = bills.filter(user=request.user)
        
        if start_date:
            bills = bills.filter(created_at__gte=start_date)
        if end_date:
            end_date = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))  # 23:59:59
            bills = bills.filter(created_at__lte=end_date)

        # Prepare the CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="bills_export.csv"'

        writer = csv.writer(response)
        
        # Write the header row
        writer.writerow([
            'Receipt ID', 'Sub Receipt', 'Created At', 'Created By', 
            'Vazhipadu Name', 'Name', 'Star', 'Amount'
        ])

        # Write the data rows
        sub_receipt_counter = "abcdefghijklmnopqrstuvwxyz"
        for bill in bills:
            counter = 0
            vazhipadu_list = bill.bill_vazhipadu_offerings.all()
            
            for vazhipadu_bill in vazhipadu_list:
                subreceipt = '-' if len(vazhipadu_list) == 1 else sub_receipt_counter[counter]
                writer.writerow([
                    bill.id,
                    subreceipt,
                    localtime(bill.created_at).strftime("%a, %d %b %Y, %-I:%M %p"),
                    bill.user.username,
                    vazhipadu_bill.vazhipadu_offering.name,
                    vazhipadu_bill.person_name,
                    vazhipadu_bill.person_star.name if vazhipadu_bill.person_star else "",
                    vazhipadu_bill.price,
                ])
                counter += 1

            other_list = bill.bill_other_items.all()
            for other_bill in other_list:
                subreceipt = '-' if len(vazhipadu_list) == 1 else sub_receipt_counter[counter]
                writer.writerow([
                    bill.id,
                    subreceipt,
                    localtime(bill.created_at).strftime("%a, %d %b %Y, %-I:%M %p"),
                    bill.user.username,
                    other_bill.vazhipadu,
                    other_bill.person_name,
                    other_bill.person_star.name if other_bill.person_star else "",
                    other_bill.price,
                ])
                counter += 1

        return response


@login_required
def cancel_bill(request, bill_id):
    if request.method == "POST":
        bill_id = int(request.POST.get('bill_id'))
        reason = request.POST.get("reason")
        if not request.user.groups.filter(name='Temple Admin').exists() and not request.user.groups.filter(name='Central Admin').exists() :
            messages.error(request, "You dont have privilege to cancel the bill.")
            return redirect("bill-list")

        try:
            bill = Bill.objects.get(id=bill_id)

            # Update the cancellation status and reason
            bill.is_cancelled = True
            bill.cancel_reason = reason if reason else ""
            bill.save()

            messages.success(request, f"Bill with Rceipt No: {bill.id} was successfully cancelled.")

        except Bill.DoesNotExist:
            messages.error(request, "The bill does not exist.")

    return redirect("bill-list")  # Replace with the desired redirect URL


@login_required
def update_payment_method(request):
    """
    Update the payment method for a bill.
    Accepts either 'cash' or 'gpay' as valid payment methods.
    Ensures that if the payment method is 'gpay', the amount must equal the bill's total amount.
    """
    # Get the bill object by receipt number

    # Only process the form if it's a POST request
    if request.method == 'POST':
        bill_id = int(request.POST.get('bill_id'))
        bill = get_object_or_404(Bill, id=bill_id)
        # Get the new payment method from the POST data
        new_payment_method = request.POST.get('payment_method')
        online_payment_amount = request.POST.get('online_payment_amount')  # Assuming online amount is passed

        # Validate the payment method
        if new_payment_method not in ['Cash', 'Online']:
            raise ValidationError("Invalid payment method selected.")
        
        # If the payment method is 'gpay', validate that the online payment amount matches the total bill amount
        # if new_payment_method == 'Online'
        #     try:
        #         online_payment_amount = float(online_payment_amount)
        #     except ValueError:
        #         raise ValidationError("Invalid online payment amount.")

        #     if online_payment_amount != bill.total_amount:
        #         raise ValidationError("For Online method, the Online amount must equal the total amount.")

        # Update the bill's payment method and save the bill
        bill.payment_method = new_payment_method

        # If the payment method is 'gpay', save the online payment amount
        # if new_payment_method == 'Online':
            # bill.online_payment_amount = online_payment_amount

        bill.save()

        # Display success message and redirect to the receipt page
        messages.success(request, f"Payment method successfully updated to {new_payment_method.capitalize()}.")
        return redirect('bill-list')

    # If the request is not POST, just redirect to the bill's receipt page
    return redirect('receipt', receipt=bill.id)


class WalletCalendar(LoginRequiredMixin, TemplateView):
    template_name = "billing_manager/wallet_calendar.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        temple_id = self.request.session.get('temple_id')
        collections = WalletCollection.objects.filter(user_id=self.request.user.id, temple_id=temple_id)
        wallet_dataset = []
        for collec in collections:
            data = {}
            data['start'] = collec.date.strftime("%Y-%m-%d")
            data['title'] = str(collec.counter_cash)
            wallet_dataset.append(data)
        
        context['events'] = wallet_dataset
        return context


class WalletCollectionCreateView(View):
    def get(self, request, *args, **kwargs):
        # Get the 'date' query parameter
        date = request.GET.get('date')

        try:
            date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise Http404("Invalid date format")
        if not date:
            raise Http404("Date parameter is required")

        # Try to retrieve the existing WalletCollection for the provided date
        wallet_collection = WalletCollection.objects.filter(date=date).first()

        # If a WalletCollection exists for that date, populate the form with its data
        if wallet_collection:
            form = WalletCollectionForm(instance=wallet_collection)
        else:
            # Otherwise, create an empty form with default values
            form = WalletCollectionForm(initial={
                'counter_cash': 0,
                'coin_counts': {'1': 0, '2': 0, '5': 0, '10': 0, '20': 0},
                'note_counts': {'10': 0, '5': 0, '20': 0}
            })
        
        return render(request, 'billing_manager/interim.html', {'form': form, 'date': date})

    def post(self, request, *args, **kwargs):
        # Get the 'date' query parameter
        date = request.GET.get('date')
        temple_id = request.session.get('temple_id')
        if not date:
            raise Http404("Date parameter is required")

        try:
            date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise Http404("Invalid date format")

        # Check if the WalletCollection for this date already exists
        wallet_collection = WalletCollection.objects.filter(date=date).first()

        # If a WalletCollection exists for that date, update it; otherwise, create a new one
        if wallet_collection:
            form = WalletCollectionForm(request.POST or None, instance=wallet_collection)
        else:
            form = WalletCollectionForm(request.POST or None)

        if request.method == 'POST':
            if form.is_valid():
                # Set the date explicitly on the form instance (whether it's a new or updated form)
                wallet_collection = form.save(commit=False)
                wallet_collection.date = date  # Ensure date is saved as well
                wallet_collection.temple_id = temple_id
                wallet_collection.user_id = request.user.id
                wallet_collection.save()
                return redirect('wallet-info')  # Redirect to the same page after saving, or you can redirect to another view

        return render(request, 'billing_manager/wallet_calendar.html', {'form': form, 'date': date})