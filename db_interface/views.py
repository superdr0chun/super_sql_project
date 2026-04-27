from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db import connection, connections
from django.conf import settings
import json

@api_view(['GET'])
def get_servers(request):
    from .models import DatabaseServer
    servers = DatabaseServer.objects.all().values('id', 'name', 'host', 'port', 'username', 'created_at')
    return Response(list(servers))

@api_view(['POST'])
def create_server(request):
    from .models import DatabaseServer
    name = request.data.get('name')
    host = request.data.get('host', 'localhost')
    port = request.data.get('port', 5432)
    username = request.data.get('username', 'postgres')
    password = request.data.get('password', '')
    
    if not name:
        return Response({"error": "Имя сервера обязательно"}, status=400)
    
    try:
        server = DatabaseServer.objects.create(
            name=name,
            host=host,
            port=port,
            username=username,
            password=password
        )
        return Response({"id": server.id, "message": "Сервер создан"})
    except Exception as e:
        return Response({"error": str(e)}, status=400)

@api_view(['DELETE'])
def delete_server(request, pk):
    from .models import DatabaseServer
    try:
        server = DatabaseServer.objects.get(pk=pk)
        server.delete()
        return Response({"message": "Сервер удален"})
    except DatabaseServer.DoesNotExist:
        return Response({"error": "Сервер не найден"}, status=404)

@api_view(['GET'])
def get_databases(request, server_id):
    from .models import Database, DatabaseServer
    try:
        server = DatabaseServer.objects.get(pk=server_id)
        databases = server.databases.all().values('id', 'name', 'created_at')
        return Response(list(databases))
    except DatabaseServer.DoesNotExist:
        return Response({"error": "Сервер не найден"}, status=404)

@api_view(['POST'])
def create_database(request, server_id):
    from .models import Database, DatabaseServer
    name = request.data.get('name')
    
    if not name:
        return Response({"error": "Имя базы данных обязательно"}, status=400)
    
    try:
        server = DatabaseServer.objects.get(pk=server_id)
        db = Database.objects.create(server=server, name=name)
        return Response({"id": db.id, "message": "База данных создана"})
    except DatabaseServer.DoesNotExist:
        return Response({"error": "Сервер не найден"}, status=404)
    except Exception as e:
        return Response({"error": str(e)}, status=400)

@api_view(['DELETE'])
def delete_database(request, server_id, db_id):
    from .models import Database
    try:
        db = Database.objects.get(pk=db_id, server_id=server_id)
        db.delete()
        return Response({"message": "База данных удалена"})
    except Database.DoesNotExist:
        return Response({"error": "База данных не найдена"}, status=404)

@api_view(['POST'])
def connect_to_database(request, server_id, db_id):
    from .models import Database, DatabaseServer
    try:
        db_obj = Database.objects.get(pk=db_id, server_id=server_id)
        server = db_obj.server
        
        new_settings = {
            'ENGINE': 'django.db.backends.postgresql',
            'HOST': server.host,
            'PORT': server.port,
            'NAME': db_obj.name,
            'USER': server.username,
            'PASSWORD': server.password,
            'ATOMIC_REQUESTS': False,
            'AUTOCOMMIT': True,
            'CONN_MAX_AGE': 0
        }
        
        settings.DATABASES['default'] = new_settings
        connections['default'].close()
        
        return Response({"message": f"Подключено к {db_obj.name} на {server.name}"})
    except Database.DoesNotExist:
        return Response({"error": "База данных не найдена"}, status=404)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

@api_view(['GET'])
def get_tables_list(request):
    with connection.cursor() as cursor:
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE 'django_%' AND name NOT LIKE 'db_%'")
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
def get_all_records(request): 
    return Response([])

@api_view(['POST'])
def create_record(request): 
    return Response({'message': 'Используйте SQL'}, status=200)

@api_view(['DELETE'])
def delete_record(request, pk): 
    return Response({'message': 'Используйте SQL'}, status=200)
