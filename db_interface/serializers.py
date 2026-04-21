from rest_framework import serializers
from .models import MyTable

class MyTableSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyTable
        fields = '__all__'