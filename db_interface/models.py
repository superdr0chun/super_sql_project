from django.db import models

class DatabaseConnection(models.Model):
    name = models.CharField(max_length=100)
    db_type = models.CharField(max_length=20, default='sqlite')
    host = models.CharField(max_length=200, blank=True, null=True)
    port = models.IntegerField(blank=True, null=True)
    database_name = models.CharField(max_length=200)
    username = models.CharField(max_length=100, blank=True, null=True)
    password = models.CharField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'db_connections'
