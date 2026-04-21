from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.db import connection

# 1. Получить список всех таблиц
@api_view(['GET'])
def get_tables_list(request):
    with connection.cursor() as cursor:
        try:
            cursor.execute("""
                SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE 'django_%'
            """)
            tables = [row[0] for row in cursor.fetchall()]
            return Response(tables)
        except Exception:
            try:
                cursor.execute("""
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_schema = 'public' ORDER BY table_name
                """)
                tables = [row[0] for row in cursor.fetchall()]
                return Response(tables)
            except Exception:
                return Response([])

# 2. Получить структуру таблицы
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
                cursor.execute("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns WHERE table_name = %s
                    ORDER BY ordinal_position
                """, [table_name])
                columns = cursor.fetchall()
                result = [{'name': col[0], 'type': col[1], 'nullable': col[2]} for col in columns]
                return Response(result)
            except Exception:
                return Response({'error': 'Не удалось загрузить структуру'})

# 3. Получить данные из таблицы
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

# 4. Выполнить несколько SQL запросов сразу
@api_view(['POST'])
def execute_raw_sql(request):
    sql_text = request.data.get('sql', '').strip()
    if not sql_text:
        return Response({"error": "Нет SQL"}, status=400)

    # Разбиваем текст на отдельные запросы по точке с запятой
    queries = [q.strip() for q in sql_text.split(';') if q.strip()]
    last_select_data = None

    with connection.cursor() as cursor:
        for query in queries:
            try:
                cursor.execute(query)
                # Если запрос вернул данные (SELECT)
                if cursor.description:
                    columns = [col[0] for col in cursor.description]
                    rows = cursor.fetchall()
                    last_select_data = [dict(zip(columns, row)) for row in rows]
            except Exception as e:
                return Response({"error": f"Ошибка в запросе:\n{query}\n\nДетали: {str(e)}"}, status=500)

    # Если последний запрос был SELECT, отдаём данные для таблицы
    if last_select_data is not None:
        return Response(last_select_data)
    else:
        return Response({"message": f"✅ Успешно выполнено запросов: {len(queries)}"})

# Заглушки для обратной совместимости
@api_view(['GET'])
def get_all_records(request): return Response([])
@api_view(['POST'])
def create_record(request): return Response({'message': 'Используйте SQL'}, status=200)
@api_view(['DELETE'])
def delete_record(request, pk): return Response({'message': 'Используйте SQL'}, status=200)