from django.contrib import admin
from main.models import *
from main.all_models.court import *
from main.all_models.match import *
from main.all_models.sport import *
from main.all_models.subscription import *
from main.all_models.team import *
from main.all_models.tournament import *
from main.all_models.user import *
# Register your models here.

# User Group
class UserAdmin(admin.ModelAdmin):
    list_display = ['email', 'first_name', 'last_name', 'surname']
    search_fields = ['email', 'first_name', 'last_name', 'surname']
    filter_horizontal = ['interested_sports']

admin.site.register(User, UserAdmin)
admin.site.register(Sport)

# Subscription Group

admin.site.register(Subscription)
admin.site.register(Plan)
admin.site.register(Transaction)

# Tournament Group
class TournamentAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'sport', 'start', 'end']
    search_fields = ['name', 'city', 'description', 'surname', 'start', 'end', 'sport__name', 'enter_prize', 'prize_pool']
    filter_horizontal = ['users_requests', 'teams_requests', 'moderators']

class TournamentStageAdmin(admin.ModelAdmin):
    list_display = ['name', 'tournament', 'start', 'end']
    search_fields = ['name', 'tournament__name', 'start', 'end']

class MatchAdmin(admin.ModelAdmin):
    list_display = ['participant1', 'participant2', 'stage']
    search_fields = ['stage__name']

admin.site.register(Tournament, TournamentAdmin)
admin.site.register(TournamentStage, TournamentStageAdmin)
admin.site.register(StageResult)
admin.site.register(Match, MatchAdmin)
admin.site.register(MatchPhoto)
admin.site.register(Participant)
admin.site.register(New)

# Private Match Group
admin.site.register(AmateurMatch)

# Court Group
admin.site.register(CourtFacility)
admin.site.register(Court)
admin.site.register(CourtReview)
admin.site.register(CourtBook)

# Teams Group
admin.site.register(Team)
# admin.site.register(TeamMemberRole)
# admin.site.register(TeamMember)