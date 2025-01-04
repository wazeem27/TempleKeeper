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
from temple_inventory.views import InventoryItemView, InventoryItemDeleteView, InventoryItemUpdateView


urlpatterns = [
    path('list/', InventoryItemView.as_view(), name='inventory-list'),
    path('delete/<uuid:pk>/', InventoryItemDeleteView.as_view(), name='inventory-delete'),
    path('edit/<uuid:pk>/', InventoryItemUpdateView.as_view(), name='inventory-edit'),
    

]
