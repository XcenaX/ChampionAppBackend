from rest_framework import serializers
from main.all_models.match import AmateurMatch
from django.core.exceptions import ObjectDoesNotExist
from main.serializers.user import AmateurMatchUserSerializer
from main.serializers.sport import SportField

class AmateurMatchSerializer(serializers.ModelSerializer):
    #owner = UserField(many=False, read_only=False, required=True)
    #opponent = UserField(many=False, read_only=False, required=False)
    owner = serializers.SerializerMethodField()
    opponent = serializers.SerializerMethodField()
    sport = SportField(many=False, read_only=False, required=True)
    lat = serializers.FloatField(required=False, allow_null=True)
    lon = serializers.FloatField(required=False, allow_null=True)

    class Meta:
        model = AmateurMatch
        fields = ['name', 'start', 'address', 'lat', 'lon', 'owner', 'opponent', 'enter_price', 'sport']

    def get_owner(self, obj):
        serializer = AmateurMatchUserSerializer(obj.owner)
        return serializer.data

    def get_opponent(self, obj):
        if obj.opponent:
            serializer = AmateurMatchUserSerializer(obj.opponent)
            return serializer.data
        return None