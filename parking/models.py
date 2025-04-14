from django.db import models

class ParkingSpace(models.Model):
    name = models.CharField(max_length=100)
    latitude = models.FloatField()
    longitude = models.FloatField()
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return self.name
