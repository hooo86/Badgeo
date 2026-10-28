from django.db import models


class OrgUnit(models.Model):
    class Kind(models.TextChoices):
        STRUCTURE = "structure", "Structure"
        DIRECTION = "direction", "Direction"
        SERVICE = "service", "Service"
        DEPARTMENT = "department", "Département"

    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="children")
    kind = models.CharField(max_length=16, choices=Kind.choices)
    name = models.CharField(max_length=150)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["parent", "name"], name="uniq_orgunit_name_per_parent")]

    def __str__(self):
        return self.name

    @staticmethod
    def with_descendants(unit_ids):
        """ids of the given units plus all their descendants."""
        seen, frontier = set(unit_ids), set(unit_ids)
        while frontier:
            frontier = set(OrgUnit.objects.filter(parent_id__in=frontier).values_list("id", flat=True)) - seen
            seen |= frontier
        return seen
