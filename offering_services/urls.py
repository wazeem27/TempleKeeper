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
from offering_services.views import (
    offering_main_view, VazhipaduOfferingView, VazhipaduOfferingDeleteView,
    VazhipaduOfferingUpdateView, UpdateOrderView
)


urlpatterns = [
    path('main/', offering_main_view, name='ofering_main'),
    # VazhipaduOffering URLs
    path('offerings/', VazhipaduOfferingView.as_view(), name='offerings-list'),
    path('offerings/delete/<uuid:pk>/', VazhipaduOfferingDeleteView.as_view(), name='offerings-delete'),
    path('offerings/edit/<uuid:pk>/', VazhipaduOfferingUpdateView.as_view(), name='offerings-edit'),
    path('update-order/', UpdateOrderView.as_view(), name='update_order'),

]
