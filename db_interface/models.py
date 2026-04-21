from django.db import models

class MyTable(models.Model):
    name = models.CharField(max_length=100)
    value = models.IntegerField()
    
    class Meta:
        db_table = 'my_table'