from __future__ import annotations

from django.db import models


class AModel(models.Model):
    name = models.CharField(max_length=100)
    value = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Test Model ({self.name})"
