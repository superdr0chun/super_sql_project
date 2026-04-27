from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db import connection, connections
from django.conf import settings
from sqlalchemy import create_engine, text, inspect, MetaData, Table, Column, String, Integer, Float, Boolean, DateTime, Date, Text, ForeignKey
from sqlalchemy.orm import sessionmaker
import json
import os

_engines = {}

def get_server_path(server):
    return os.path.join(settings.BASE_DIR, 'servers', f'server_{server.id}')

def get_db_path(db_obj):
    server_path = get_server_path(db_obj.server)
    return os.path.join(server_path, f'{db_obj.name}.db')

def get_db_engine(db_obj):
    db_path = get_db_path(db_obj)
    return create_engine(f'sqlite:///{db_path}')

@api_view(['GET'])
def get_servers(request):
    from .models import DatabaseServer
    servers = DatabaseServer.objects.all().values('id', 'name', 'host', 'port', 'username', 'created_at')
    return Response(list(servers))

@api_view(['POST'])
def create_server(request):
    from .models import DatabaseServer
    import os
    
    name = request.data.get('name')
    
    if not name:
        return Response({"error": "Имя сервера обязательно"}, status=400)
    
    try:
        server = DatabaseServer.objects.create(
            name=name,
            host='localhost',
            port=5432,
            username='sqlite',
            password=''
        )
        server_path = get_server_path(server)
        os.makedirs(server_path, exist_ok=True)
        return Response({"id": server.id, "message": "Сервер создан"})
    except Exception as e:
        return Response({"error": str(e)}, status=400)

@api_view(['DELETE'])
def delete_server(request, pk):
    from .models import DatabaseServer
    import shutil
    
    try:
        server = DatabaseServer.objects.get(pk=pk)
        server_path = get_server_path(server)
        if os.path.exists(server_path):
            shutil.rmtree(server_path)
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
        
        db_path = os.path.join(get_server_path(server), f'{name}.db')
        
        engine = create_engine(f'sqlite:///{db_path}')
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
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
        db_path = get_db_path(db)
        
        if os.path.exists(db_path):
            os.remove(db_path)
        
        db.delete()
        return Response({"message": "База данных удалена"})
    except Database.DoesNotExist:
        return Response({"error": "База данных не найдена"}, status=404)
    except Exception as e:
        return Response({"error": str(e)}, status=400)

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
    db_id = request.GET.get('db_id')
    if db_id:
        from .models import Database
        try:
            db_obj = Database.objects.get(pk=db_id)
            engine = get_db_engine(db_obj)
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            hidden = ['auth_group', 'auth_permission', 'auth_group_permissions', 'auth_user', 'auth_user_groups', 'auth_user_permissions', 'db_servers', 'db_databases']
            tables = [t for t in tables if t.lower() not in hidden]
            return Response(tables)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
    
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
    db_id = request.GET.get('db_id')
    if db_id:
        from .models import Database
        try:
            db_obj = Database.objects.get(pk=db_id)
            engine = get_db_engine(db_obj)
            inspector = inspect(engine)
            columns = inspector.get_columns(table_name)
            result = [{'name': c['name'], 'type': str(c['type']), 'nullable': c.get('nullable', True)} for c in columns]
            return Response(result)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
    
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
    db_id = request.GET.get('db_id')
    limit = request.GET.get('limit', 100)
    
    if db_id:
        from .models import Database
        try:
            db_obj = Database.objects.get(pk=db_id)
            engine = get_db_engine(db_obj)
            with engine.connect() as conn:
                result = conn.execute(text(f"SELECT * FROM {table_name} LIMIT :limit"), {"limit": int(limit)})
                columns = result.keys()
                rows = result.fetchall()
                data = [dict(zip(columns, row)) for row in rows]
                return Response(data)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
    
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
    db_id = request.data.get('db_id')
    
    if not sql_text:
        return Response({"error": "Нет SQL"}, status=400)

    if db_id:
        from .models import Database
        try:
            db_obj = Database.objects.get(pk=db_id)
            engine = get_db_engine(db_obj)
            
            queries = [q.strip() for q in sql_text.split(';') if q.strip()]
            last_select_data = None
            
            with engine.connect() as conn:
                for query in queries:
                    result = conn.execute(text(query))
                    if result.returns_rows:
                        columns = result.keys()
                        rows = result.fetchall()
                        last_select_data = [dict(zip(columns, row)) for row in rows]
                conn.commit()
            
            if last_select_data is not None:
                return Response(last_select_data)
            else:
                return Response({"message": f"Успешно выполнено запросов: {len(queries)}"})
        except Exception as e:
            return Response({"error": f"Ошибка в запросе:\n{sql_text}\n\nДетали: {str(e)}"}, status=500)
    
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

@api_view(['POST'])
def create_table(request):
    db_id = request.data.get('db_id')
    table_name = request.data.get('table_name')
    columns = request.data.get('columns', [])
    
    if not db_id or not table_name:
        return Response({"error": "db_id и table_name обязательны"}, status=400)
    
    from .models import Database
    try:
        db_obj = Database.objects.get(pk=db_id)
        engine = get_db_engine(db_obj)
        
        type_map = {
            'INTEGER': Integer,
            'INT': Integer,
            'VARCHAR': String,
            'TEXT': Text,
            'BOOLEAN': Boolean,
            'DATE': Date,
            'TIMESTAMP': DateTime,
            'FLOAT': Float,
            'STRING': String
        }
        
        metadata = MetaData()
        cols = []
        for col in columns:
            col_name = col.get('name')
            col_type = col.get('type', 'VARCHAR').upper()
            is_pk = col.get('is_pk', False)
            
            sa_type = type_map.get(col_type, String)
            if sa_type == String:
                column_obj = Column(col_name, sa_type(255), primary_key=is_pk)
            elif sa_type == DateTime:
                column_obj = Column(col_name, sa_type, primary_key=is_pk)
            else:
                column_obj = Column(col_name, sa_type, primary_key=is_pk)
            cols.append(column_obj)
        
        new_table = Table(table_name, metadata, *cols)
        metadata.create_all(engine)
        
        return Response({"message": f"Таблица {table_name} создана"})
    except Exception as e:
        return Response({"error": str(e)}, status=400)

@api_view(['GET'])
def get_all_records(request): 
    return Response([])

@api_view(['POST'])
def create_record(request): 
    return Response({'message': 'Используйте SQL'}, status=200)

@api_view(['DELETE'])
def delete_record(request, pk): 
    return Response({'message': 'Используйте SQL'}, status=200)
