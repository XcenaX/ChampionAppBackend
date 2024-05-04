import django_filters
from main.all_models.match import AmateurMatch
from main.all_models.tournament import Tournament, Team
from main.models import User
from django.db.models import Q

class AmateurMatchFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    address = django_filters.CharFilter(lookup_expr='icontains')
    city = django_filters.CharFilter(lookup_expr='icontains')
    
    enter_price = django_filters.NumberFilter()
    enter_price__gt = django_filters.NumberFilter(field_name='enter_price', lookup_expr='gt')
    enter_price__lt = django_filters.NumberFilter(field_name='enter_price', lookup_expr='lt')

    sport = django_filters.NumberFilter(field_name='sport__id')
    sport_name = django_filters.CharFilter(field_name='sport__name', lookup_expr='icontains')

    start_after = django_filters.DateTimeFilter(field_name='start', lookup_expr='gt')
    start_before = django_filters.DateTimeFilter(field_name='start', lookup_expr='lt')

    class Meta:
        model = AmateurMatch
        fields = ['name', 'address', 'city', 'sport', 'enter_price', 'start']


class TournamentFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    # city = django_filters.CharFilter(lookup_expr='icontains')
    
    enter_price = django_filters.NumberFilter()
    enter_price__gt = django_filters.NumberFilter(field_name='enter_price', lookup_expr='gt')
    enter_price__lt = django_filters.NumberFilter(field_name='enter_price', lookup_expr='lt')

    sport = django_filters.NumberFilter(field_name='sport__id')
    sport_name = django_filters.CharFilter(field_name='sport__name', lookup_expr='icontains')

    start_after = django_filters.DateTimeFilter(field_name='start', lookup_expr='gt')
    start_before = django_filters.DateTimeFilter(field_name='start', lookup_expr='lt')

    class Meta:
        model = Tournament
        fields = ['name', 'sport', 'enter_price', 'start']


class TeamFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')

    sport = django_filters.NumberFilter(field_name='sport__id')
    sport_name = django_filters.CharFilter(field_name='sport__name', lookup_expr='icontains')

    class Meta:
        model = Team
        fields = ['name', 'sport']

class UserFilter(django_filters.FilterSet):
    fullname = django_filters.CharFilter(method='filter_fullname')

    class Meta:
        model = User
        fields = []

    def filter_fullname(self, queryset, name, value):
        """
        Custom filter method to search users by splitting the input 'fullname' into parts and
        searching these parts across first_name, surname, and last_name fields.
        """
        name_parts = value.split()
        queries = [Q(first_name__icontains=part) | Q(surname__icontains=part) | Q(last_name__icontains=part) for part in name_parts]

        query = queries.pop()
        for item in queries:
            query |= item

        return queryset.filter(query)
