from rest_framework import serializers
from main.all_models.team import Team

from main.models import User
from main.serializers.sport import SportField, TournamentListSportSerializer


from main.serializers.user import UserSerializer

from django.db import transaction

from main.services.img_functions import _decode_photo


class TeamListSerializer(serializers.ModelSerializer):
    members = serializers.SerializerMethodField()
    sport = TournamentListSportSerializer(many=False)
    logo = serializers.SerializerMethodField()
    
    class Meta:
        model = Team
        fields = ['id', 'name', 'sport', 'logo', 'members']

    def get_logo(self, obj):
        try:
            return obj.logo.url
        except:
            return ""
    
    def get_members(self, obj):
        members = obj.members.all()
        return UserSerializer(members, many=True).data
    

class TeamSerializer(serializers.ModelSerializer):
    members = UserSerializer(many=True, read_only=True)
    members_to_add =  serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False)
    
    sport = SportField(many=False, read_only=False, required=True)
    logo = serializers.SerializerMethodField()
    logo_base64 = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = Team
        fields = ['id', 'name', 'sport', 'logo', 'logo_base64', 'members', 'members_to_add']

    @transaction.atomic
    def create(self, validated_data):
        members = validated_data.pop('members_to_add', [])
        logo_base64 = validated_data.pop('logo_base64', None)
        
        team = Team.objects.create(**validated_data)

        logo = None if not logo_base64 else _decode_photo(logo_base64)

        if not logo:
            sport = validated_data.get('sport')
            validated_data['photos'] = sport.image
        else:
            team.logo = logo

        for user_id in members:
            try:
                user = User.objects.get(id=user_id)
                team.members.add(user)
            except:
                pass
        
        team.save()
        return team

    def get_logo(self, obj):
        try:
            return obj.logo.url
        except:
            return ""