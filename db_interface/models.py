from django.db import models

class DatabaseServer(models.Model):
    name = models.CharField(max_length=100, unique=True)
    host = models.CharField(max_length=200, default='localhost')
    port = models.IntegerField(default=5432)
    username = models.CharField(max_length=100, default='postgres')
    password = models.CharField(max_length=200, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'db_servers'
        ordering = ['name']

class Database(models.Model):
    server = models.ForeignKey(DatabaseServer, on_delete=models.CASCADE, related_name='databases')
    name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'db_databases'
        unique_together = ['server', 'name']
        ordering = ['name']
