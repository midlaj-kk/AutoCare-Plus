from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import SparePart
from .serializers import (
    SparePartSerializer, AddStockSerializer,
    ReduceStockSerializer, StockMovementSerializer,
)
from core.permissions import IsAdmin, IsAdminStaffOrReadOnly
from .services import create_spare_part, update_spare_part, add_stock, reduce_stock
from .selectors import get_spare_parts, get_low_stock_parts, get_stock_history


class SparePartViewSet(viewsets.ModelViewSet):
    queryset = SparePart.objects.all()
    serializer_class = SparePartSerializer
    permission_classes = [IsAdminStaffOrReadOnly]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["name", "part_number"]
    ordering_fields = ["name", "stock_quantity"]
    ordering = ["name"]

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [IsAdmin()]
        return super().get_permissions()

    @action(detail=True, methods=["post"])
    def add_stock(self, request, pk=None):
        part = self.get_object()
        serializer = AddStockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated_part = add_stock(
            part.id, serializer.validated_data["quantity"],
            "purchase", None, request.user,
        )
        return Response({
            "success": True,
            "message": "Stock added successfully.",
            "data": SparePartSerializer(updated_part).data,
        })

    @action(detail=True, methods=["post"])
    def reduce_stock(self, request, pk=None):
        part = self.get_object()
        serializer = ReduceStockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            updated_part = reduce_stock(
                part.id, serializer.validated_data["quantity"],
                serializer.validated_data["reason"], request.user,
            )
            return Response({
                "success": True,
                "message": "Stock reduced successfully.",
                "data": SparePartSerializer(updated_part).data,
            })
        except Exception as e:
            return Response({"success": False, "message": str(e)}, status=400)

    @action(detail=True, methods=["get"])
    def stock_history(self, request, pk=None):
        movements = get_stock_history(pk)
        serializer = StockMovementSerializer(movements, many=True)
        return Response({"success": True, "data": serializer.data})

    @action(detail=False, methods=["get"])
    def low_stock(self, request):
        parts = get_low_stock_parts()
        serializer = SparePartSerializer(parts, many=True)
        return Response({"success": True, "data": serializer.data})
