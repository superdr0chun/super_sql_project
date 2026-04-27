from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db import connection, connections
from django.conf import settings
import json

@api_view(['GET'])
def get_tables_list(request):
    with connection.cursor() as cursor:
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE 'django_%' AND name != 'db_connections'")
            tables = [row[0] for row in cursor.fetchall()]
            return Response(tables)
        except Exception:
            try:
                cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name")
                tables = [row[0] for row in cursor.fetchall()]
                return Response(tables)
            except Exception:
                return Response([])

@api_view(['GET'])
def get_table_structure(request, table_name):
    with connection.cursor() as cursor:
        try:
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            result = [{'name': col[1], 'type': col[2], 'nullable': col[3]} for col in columns]
            return Response(result)
        except Exception:
            try:
                cursor.execute("SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = %s ORDER BY ordinal_position", [table_name])
                columns = cursor.fetchall()
                result = [{'name': col[0], 'type': col[1], 'nullable': col[2]} for col in columns]
                return Response(result)
            except Exception:
                return Response({'error': 'Не удалось загрузить структуру'})

@api_view(['GET'])
def get_table_data(request, table_name):
    limit = request.GET.get('limit', 100)
    with connection.cursor() as cursor:
        try:
            cursor.execute(f"SELECT * FROM {table_name} LIMIT %s", [limit])
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            result = [dict(zip(columns, row)) for row in rows]
            return Response(result)
        except Exception as e:
            return Response({'error': str(e)}, status=500)

@api_view(['POST'])
def execute_raw_sql(request):
    sql_text = request.data.get('sql', '').strip()
    if not sql_text:
        return Response({"error": "Нет SQL"}, status=400)

    queries = [q.strip() for q in sql_text.split(';') if q.strip()]
    last_select_data = None

    with connection.cursor() as cursor:
        for query in queries:
            try:
                cursor.execute(query)
                if cursor.description:
                    columns = [col[0] for col in cursor.description]
                    rows = cursor.fetchall()
                    last_select_data = [dict(zip(columns, row)) for row in rows]
            except Exception as e:
                return Response({"error": f"Ошибка в запросе:\n{query}\n\nДетали: {str(e)}"}, status=500)

    if last_select_data is not None:
        return Response(last_select_data)
    else:
        return Response({"message": f"Успешно выполнено запросов: {len(queries)}"})

@api_view(['GET'])
def get_connections(request):
    from .models import DatabaseConnection
    connections_list = DatabaseConnection.objects.all().values('id', 'name', 'db_type', 'host', 'port', 'database_name', 'created_at')
    return Response(list(connections_list))

@api_view(['POST'])
def create_connection(request):
    from .models import DatabaseConnection
    name = request.data.get('name')
    db_type = request.data.get('db_type', 'sqlite')
    host = request.data.get('host', '')
    port = request.data.get('port')
    database_name = request.data.get('database_name')
    username = request.data.get('username', '')
    password = request.data.get('password', '')
    
    if not name or not database_name:
        return Response({"error": "name и database_name обязательны"}, status=400)
    
    conn = DatabaseConnection.objects.create(
        name=name,
        db_type=db_type,
        host=host or None,
        port=port,
        database_name=database_name,
        username=username or None,
        password=password or None
    )
    return Response({"id": conn.id, "message": "Соединение создано"})

@api_view(['DELETE'])
def delete_connection(request, pk):
    from .models import DatabaseConnection
    try:
        conn = DatabaseConnection.objects.get(pk=pk)
        conn.delete()
        return Response({"message": "Соединение удалено"})
    except DatabaseConnection.DoesNotExist:
        return Response({"error": "Соединение не найдено"}, status=404)

@api_view(['POST'])
def switch_connection(request, pk):
    from .models import DatabaseConnection
    try:
        conn = DatabaseConnection.objects.get(pk=pk)
        
        new_settings = dict(settings.DATABASES['default'])
        
        if conn.db_type == 'sqlite':
            new_settings['ENGINE'] = 'django.db.backends.sqlite3'
            new_settings['NAME'] = conn.database_name
        else:
            new_settings['ENGINE'] = 'django.db.backends.postgresql'
            new_settings['HOST'] = conn.host
            new_settings['PORT'] = conn.port or 5432
            new_settings['NAME'] = conn.database_name
            new_settings['USER'] = conn.username
            new_settings['PASSWORD'] = conn.password
        
        new_settings['ATOMIC_REQUESTS'] = False
        new_settings['AUTOCOMMIT'] = True
        new_settings['CONN_MAX_AGE'] = 0
        
        settings.DATABASES['default'] = new_settings
        connections['default'].close()
        
        return Response({"message": f"Переключено на {conn.name}"})
    except DatabaseConnection.DoesNotExist:
        return Response({"error": "Соединение не найдено"}, status=404)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(['GET'])
def get_all_records(request): 
    return Response([])

@api_view(['POST'])
def create_record(request): 
    return Response({'message': 'Используйте SQL'}, status=200)

@api_view(['DELETE'])
def delete_record(request, pk): 
    return Response({'message': 'Используйте SQL'}, status=200)
