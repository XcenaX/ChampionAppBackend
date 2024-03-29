from rest_framework import serializers
from main.models import User
from django.core.exceptions import ObjectDoesNotExist


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


class AmateurMatchUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('degree', 'rating', 'phone', 'surname', 'first_name')


class UserField(serializers.RelatedField):
    queryset = User.objects.all()
    
    def to_representation(self, value):
        return value.id

    def to_internal_value(self, data):
        try:
            return User.objects.get(id=data)
        except ObjectDoesNotExist:
            raise serializers.ValidationError('Пользователь с таким ID не найден.')
        except TypeError:
            raise serializers.ValidationError('ID должен быть целым числом.')

