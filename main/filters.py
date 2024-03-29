import django_filters
from main.all_models.match import AmateurMatch

class AmateurMatchFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(lookup_expr='icontains')
    address = django_filters.CharFilter(lookup_expr='icontains')  # Фильтр по адресу с частичным соответствием
    
    enter_price = django_filters.NumberFilter()
    enter_price__gt = django_filters.NumberFilter(field_name='enter_price', lookup_expr='gt')
    enter_price__lt = django_filters.NumberFilter(field_name='enter_price', lookup_expr='lt')

    sport = django_filters.NumberFilter(field_name='sport__id')
    sport_name = django_filters.CharFilter(field_name='sport__name', lookup_expr='icontains')

    start_after = django_filters.DateTimeFilter(field_name='start', lookup_expr='gt')
    start_before = django_filters.DateTimeFilter(field_name='start', lookup_expr='lt')

    class Meta:
        model = AmateurMatch
        fields = ['name', 'address', 'sport', 'enter_price', 'start']
