from django.contrib import admin
from django.urls import path

from bills.views import (
    BillDetailView,
    BillListView,
    CatalogView,
    GenerateBillView,
    LoginView,
    RefreshPricesView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/login/", LoginView.as_view()),
    path("api/catalog/", CatalogView.as_view()),
    path("api/catalog/refresh-prices/", RefreshPricesView.as_view()),
    path("api/generate-bill/", GenerateBillView.as_view()),
    path("api/bills/", BillListView.as_view()),
    path("api/bills/<int:pk>/", BillDetailView.as_view()),
]
