from rest_framework import serializers
from main.models import Sport
from django.core.exceptions import ObjectDoesNotExist


class SportField(serializers.RelatedField):
    queryset = Sport.objects.all()
    
    def to_representation(self, value):
        return {
            "id": value.id,
            "name": value.name,
            "image": value.image.url if value.image else None,
            "icon": value.icon.url if value.icon else None
        }

    def to_internal_value(self, data):
        try:
            return Sport.objects.get(id=data)
        except ObjectDoesNotExist:
            raise serializers.ValidationError('Такой вид спорта не найден.')
        except TypeError:
            raise serializers.ValidationError('Неправильный формат данных для вида спорта.')


class SportSerializer(serializers.ModelSerializer):
    image = serializers.FileField(use_url=True)
    icon = serializers.FileField(use_url=True, allow_null=True, required=False)

    class Meta:
        model = Sport
        fields = ['id', 'name', 'image', 'icon']


class AmateurMatchSportSerializer(serializers.ModelSerializer):
    icon = serializers.FileField(use_url=True)

    class Meta:
        model = Sport
        fields = ['icon', 'name']

class TournamentListSportSerializer(serializers.ModelSerializer):
    icon = serializers.FileField(use_url=True)

    class Meta:
        model = Sport
        fields = ['icon']