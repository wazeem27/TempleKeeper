"""
URL configuration for TempleKeeper project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from billing_manager.views import BillingView, submit_billing, BillListView, BillDetailView, ReceiptView, ViewMultiReceipt, BillExportView, cancel_bill, update_payment_method


urlpatterns = [
    path('add_bill/', BillingView.as_view(), name='add-bill'),
    path('submit_billing/', submit_billing, name='submit-billing'),
    path('bill_list/', BillListView.as_view(), name='bill-list'),
    path("bill/<int:pk>/", BillDetailView.as_view(), name="bill-detail"),
    path("receipt/<int:pk>/", ReceiptView.as_view(), name="receipt"),
    path('view-multi-receipt/', ViewMultiReceipt.as_view(), name='view_multi_receipt'),
    path('export_csv/', BillExportView.as_view(), name='export-csv'),
    path('cancel_bill/<int:bill_id>/', cancel_bill, name='cancel-bill'),
    path('update-payment-method/', update_payment_method, name='update-payment-method'),

    # path('offerings/edit/<int:pk>/', VazhipaduOfferingUpdateView.as_view(), name='offerings-edit'),

]
