from rest_framework import serializers
from main.models import Sport
from django.core.exceptions import ObjectDoesNotExist


class SportField(serializers.RelatedField):
    queryset = Sport.objects.all()
    
    def to_representation(self, value):
        return value.name

    def to_internal_value(self, data):
        try:
            return Sport.objects.get(id=data)
        except ObjectDoesNotExist:
            raise serializers.ValidationError('Такой вид спорта не найден.')
        except TypeError:
            raise serializers.ValidationError('Неправильный формат данных для вида спорта.')



class SportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sport
        fields = ['id', 'name', 'image', 'icon']