from django.db import models


class Licence(models.Model):
    """Clé d'activation enregistrée sur ce poste. Exclue des sauvegardes : restaurer une sauvegarde ne change pas la licence."""
    cle = models.TextField()
    active_le = models.DateTimeField(auto_now_add=True)
    derniere_date = models.DateField(null=True, blank=True, help_text="Dernier jour vu : empêche de prolonger en reculant l'horloge")

    class Meta:
        ordering = ["-active_le", "-pk"]
