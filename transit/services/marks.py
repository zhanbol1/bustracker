"""Business rules for marks. Views call MarkService instead of saving marks directly."""

from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from ..models import Mark
from .geo import distance_m


class MarkService:
    DAILY_LIMIT = 10          # rule 1: at most 10 marks per day
    DUPLICATE_RADIUS_M = 20   # rule 2: no own mark of the same category within 20 m

    def __init__(self, user):
        self.user = user

    def _check_daily_limit(self):
        since = timezone.now() - timedelta(days=1)
        if Mark.objects.filter(owner=self.user, created_at__gte=since).count() >= self.DAILY_LIMIT:
            raise ValidationError(f"You can create at most {self.DAILY_LIMIT} marks per day.")

    def _check_duplicate(self, mark):
        own = Mark.objects.filter(owner=self.user, category=mark.category).exclude(pk=mark.pk)
        for other in own:
            if distance_m(mark.lat, mark.lng, other.lat, other.lng) < self.DUPLICATE_RADIUS_M:
                raise ValidationError(
                    f"You already have a mark of this category nearby: \"{other.title}\"."
                )

    def create(self, mark):
        if not self.user.is_authenticated:
            raise PermissionDenied
        mark.owner = self.user
        self._check_daily_limit()
        mark.full_clean()          # rule 3: point must be inside the city (Mark.clean)
        self._check_duplicate(mark)
        mark.save()
        return mark

    def update(self, mark):
        if not mark.can_edit(self.user):
            raise PermissionDenied
        mark.full_clean()
        self._check_duplicate(mark)
        mark.save()
        return mark

    def delete(self, mark):
        if not mark.can_edit(self.user):
            raise PermissionDenied
        mark.delete()
