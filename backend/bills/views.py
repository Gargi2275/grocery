from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .catalog import adjustment_catalog, grocery_catalog, load_live_prices
from .custom_products import (
    UNITS,
    add_custom_product,
    delete_custom_product,
    update_custom_product,
)
from .models import Bill
from .prices import refresh_live_prices
from .serializers import (
    BillListSerializer,
    BillSerializer,
    CustomProductSerializer,
    GenerateBillSerializer,
    LoginSerializer,
)
from .services import generate_bills


def _serialize_sku(item):
    return {
        "name": item["name"],
        "unit": item["unit"],
        "unit_price": str(item["unit_price"]),
        "qty_options": item.get("qty_options") or ["1", "2", "3"],
        "price_source": item.get("price_source"),
        "custom": bool(item.get("custom")),
    }


def catalog_payload():
    cache = load_live_prices()
    return {
        "grocery": [_serialize_sku(item) for item in grocery_catalog()],
        "adjustments": [_serialize_sku(item) for item in adjustment_catalog()],
        "prices_updated_at": cache.get("updated_at"),
        "units": list(UNITS),
    }


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]

        if username != settings.ADMIN_USERNAME or password != settings.ADMIN_PASSWORD:
            return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)

        user, _created = User.objects.get_or_create(
            username=settings.ADMIN_USERNAME,
            defaults={"is_staff": True},
        )
        if not user.check_password(settings.ADMIN_PASSWORD):
            user.set_password(settings.ADMIN_PASSWORD)
            user.is_staff = True
            user.save(update_fields=["password", "is_staff"])

        token = RefreshToken.for_user(user)
        return Response({"token": str(token.access_token)})


class GenerateBillView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = GenerateBillSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        count = int(data.get("count") or 1)
        try:
            with transaction.atomic():
                bills = generate_bills(
                    count=count,
                    shop_name=data["shop_name"],
                    gst_number=data.get("gst_number") or "",
                    customer_name=data["customer_name"],
                    max_amount=Decimal(data["max_amount"]),
                    date_mode=data["date_mode"],
                    bill_date=data.get("bill_date"),
                    date_range_start=data.get("date_range_start"),
                    date_range_end=data.get("date_range_end"),
                    product_mode=data.get("product_mode", "random"),
                    selected_products=data.get("selected_products"),
                    gst_percent=Decimal(data.get("gst_percent") or 0),
                    shop_address=data.get("shop_address") or "",
                    customer_address=data.get("customer_address") or "",
                    shop_phone=data.get("shop_phone") or "",
                    customer_phone=data.get("customer_phone") or "",
                    payment_mode=data.get("payment_mode") or "cash",
                    receipt_template=data.get("receipt_template") or "invoice",
                )
        except (ValueError, InvalidOperation) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        ids = [bill.pk for bill in bills]
        saved = list(Bill.objects.prefetch_related("items").filter(pk__in=ids))
        saved.sort(key=lambda bill: ids.index(bill.pk))
        return Response(
            {"count": len(saved), "bills": BillSerializer(saved, many=True).data},
            status=status.HTTP_201_CREATED,
        )


class CatalogView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(catalog_payload())


class CustomProductView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CustomProductSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        orig_name = (data.get("original_name") or "").strip()
        try:
            if orig_name:
                update_custom_product(
                    orig_name,
                    data["name"],
                    data["unit"],
                    data["unit_price"],
                    data.get("item_type") or "grocery",
                )
            else:
                add_custom_product(
                    data["name"],
                    data["unit"],
                    data["unit_price"],
                    data.get("item_type") or "grocery",
                )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(catalog_payload(), status=status.HTTP_201_CREATED)

    def put(self, request):
        serializer = CustomProductSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        orig_name = (data.get("original_name") or data["name"]).strip()
        try:
            update_custom_product(
                orig_name,
                data["name"],
                data["unit"],
                data["unit_price"],
                data.get("item_type") or "grocery",
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(catalog_payload())

    def patch(self, request):
        return self.put(request)

    def delete(self, request):
        name = (request.data.get("name") if isinstance(request.data, dict) else None) or request.query_params.get("name")
        if not name or not delete_custom_product(name):
            return Response({"detail": "Product not found or could not be removed."}, status=status.HTTP_404_NOT_FOUND)
        return Response(catalog_payload())


class RefreshPricesView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            payload = refresh_live_prices()
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        data = catalog_payload()
        data["updated_count"] = payload.get("updated_count", 0)
        data["prices_updated_at"] = payload.get("updated_at")
        return Response(data)


class BillListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = BillListSerializer

    def get_queryset(self):
        qs = Bill.objects.all()
        params = self.request.query_params
        query = (params.get("q") or "").strip()
        if query:
            qs = qs.filter(
                Q(bill_number__icontains=query)
                | Q(customer_name__icontains=query)
                | Q(shop_name__icontains=query)
                | Q(customer_address__icontains=query)
                | Q(shop_address__icontains=query)
            )
        customer = (params.get("customer") or "").strip()
        if customer:
            qs = qs.filter(customer_name__icontains=customer)
        shop = (params.get("shop") or "").strip()
        if shop:
            qs = qs.filter(shop_name__icontains=shop)
        date_from = (params.get("date_from") or "").strip()
        if date_from:
            try:
                qs = qs.filter(bill_date__gte=date_from)
            except (ValueError, TypeError):
                pass
        date_to = (params.get("date_to") or "").strip()
        if date_to:
            try:
                qs = qs.filter(bill_date__lte=date_to)
            except (ValueError, TypeError):
                pass
        min_total = (params.get("min_total") or "").strip()
        if min_total:
            try:
                qs = qs.filter(grand_total__gte=Decimal(min_total))
            except (InvalidOperation, ValueError, TypeError):
                pass
        max_total = (params.get("max_total") or "").strip()
        if max_total:
            try:
                qs = qs.filter(grand_total__lte=Decimal(max_total))
            except (InvalidOperation, ValueError, TypeError):
                pass
        gst = (params.get("gst") or "all").strip().lower()
        if gst == "yes":
            qs = qs.filter(gst_percent__gt=0)
        elif gst == "no":
            qs = qs.filter(gst_percent=0)
        return qs


class BillDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = BillSerializer
    queryset = Bill.objects.prefetch_related("items")
