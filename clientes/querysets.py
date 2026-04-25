from django.db import models


class ClienteQuerySet(models.QuerySet):
    def activos(self):
        return self.filter(estado=1)

    def de_baja(self):
        return self.filter(estado=9)

    def con_dni(self):
        return self.filter(tipo_doc="DNI")

    def buscar(self, termino):
        """
        Búsqueda por nombre, apellido
        o número de documento
        """
        return self.filter(
            models.Q(nombres__icontains=termino)
            | models.Q(apellidos__icontains=termino)
            | models.Q(nro_doc__icontains=termino)
        )
