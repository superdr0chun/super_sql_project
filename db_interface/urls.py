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
    path('connections/', views.get_connections, name='connections-list'),
    path('connections/create/', views.create_connection, name='connection-create'),
    path('connections/<int:pk>/delete/', views.delete_connection, name='connection-delete'),
    path('connections/<int:pk>/switch/', views.switch_connection, name='connection-switch'),
]