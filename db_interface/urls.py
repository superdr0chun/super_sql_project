from django.urls import path
from . import views

urlpatterns = [
    path('servers/', views.get_servers, name='servers-list'),
    path('servers/create/', views.create_server, name='server-create'),
    path('servers/<int:pk>/delete/', views.delete_server, name='server-delete'),
    path('servers/<int:server_id>/databases/', views.get_databases, name='databases-list'),
    path('servers/<int:server_id>/databases/create/', views.create_database, name='database-create'),
    path('servers/<int:server_id>/databases/<int:db_id>/delete/', views.delete_database, name='database-delete'),
    path('servers/<int:server_id>/databases/<int:db_id>/connect/', views.connect_to_database, name='database-connect'),
    path('tables/', views.get_tables_list, name='tables-list'),
    path('tables/<str:table_name>/structure/', views.get_table_structure, name='table-structure'),
    path('tables/<str:table_name>/data/', views.get_table_data, name='table-data'),
    path('records/', views.get_all_records, name='get-all'),
    path('records/create/', views.create_record, name='create-record'),
    path('records/<int:pk>/delete/', views.delete_record, name='delete-record'),
    path('raw-sql/', views.execute_raw_sql, name='raw-sql'),
]