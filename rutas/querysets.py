from django.db import models


class RutaQuerySet(models.QuerySet):
    def activas(self):
        return self.filter(estado=1)

    def por_origen(self, ciudad):
        return self.filter(origen__icontains=ciudad)

    def por_destino(self, ciudad):
        return self.filter(destino__icontains=ciudad)
