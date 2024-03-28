from django.contrib import admin
from main.models import *
# Register your models here.

# User Group
admin.site.register(User)
admin.site.register(Sport)

# Subscription Group
admin.site.register(Subscription)
admin.site.register(Plan)
admin.site.register(Transaction)

# Tournament Group
admin.site.register(Tournament)
admin.site.register(TournamentPlace)
admin.site.register(TournamentStage)
admin.site.register(MatchParticipant)
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
admin.site.register(TeamMemberRole)
admin.site.register(TeamMember)