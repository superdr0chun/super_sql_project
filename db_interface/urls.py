from django.urls import path
from . import views

urlpatterns = [
    path('tables/', views.get_tables_list, name='tables-list'),
    path('tables/<str:table_name>/structure/', views.get_table_structure, name='table-structure'),
    path('tables/<str:table_name>/data/', views.get_table_data, name='table-data'),
    path('records/', views.get_all_records, name='get-all'),
    path('records/create/', views.create_record, name='create-record'),
    path('records/<int:pk>/delete/', views.delete_record, name='delete-record'),
    path('raw-sql/', views.execute_raw_sql, name='raw-sql'),
]