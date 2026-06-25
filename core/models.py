from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SequenceCounter(models.Model):
    prefix = models.CharField(max_length=20)
    year = models.IntegerField()
    last_value = models.BigIntegerField(default=0)

    class Meta:
        unique_together = ("prefix", "year")

    def __str__(self):
        return f"{self.prefix}-{self.year}: {self.last_value}"
