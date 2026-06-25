from django.contrib import admin
from .models import SequenceCounter


@admin.register(SequenceCounter)
class SequenceCounterAdmin(admin.ModelAdmin):
    list_display = ("prefix", "year", "last_value")
    list_filter = ("prefix", "year")
