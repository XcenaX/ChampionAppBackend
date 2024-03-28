from rest_framework import serializers
from main.models import *


class UserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()
    degree = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'surname', 'role', 'degree', 'rating', 'google', 'phone', 'active_subscription', 'date_payment', 'created_at')

    def get_role(self, obj):
        return obj.get_role_display()

    def get_degree(self, obj):
        return obj.get_degree_display()