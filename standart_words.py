import psycopg2,os
from dotenv import load_dotenv

load_dotenv()
password = os.getenv('PASSWORD')
default_conn = psycopg2.connect(database='dictionary', user='postgres', password=password)


def get_conn():
    global default_conn
    if default_conn.closed:
        default_conn = psycopg2.connect(database='dictionary', user='postgres', password=password)
    return default_conn

def conn_close():
    default_conn.close()

def delete_tables():    # Для удаления созданных таб
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("""
        DROP TABLE basic_words;
        DROP TABLE user_words;
        DROP TABLE all_words;
        """)
        conn.commit()

def create_tables():
    conn = get_conn()
    with conn.cursor() as cur:
        basic_words = cur.execute("""
        CREATE TABLE IF NOT EXISTS basic_words(
        id SERIAL PRIMARY KEY,
        russian_words VARCHAR(60) NOT NULL,
        english_words VARCHAR(60) NOT NULL
        );
        """)

        user_words = cur.execute("""
        CREATE TABLE IF NOT EXISTS user_words(
            id SERIAL PRIMARY KEY,
            russian_words VARCHAR(60) NOT NULL,
            english_words VARCHAR(60) NOT NULL
            );
        """)

        all_words = cur.execute("""
        CREATE TABLE all_words (
            id SERIAL PRIMARY KEY,
            source_table VARCHAR(20) NOT NULL,  -- Отмечаем источник данных (basic/user)
            russian_words VARCHAR(60) NOT NULL,
            english_words VARCHAR(60) NOT NULL
            );
        """)
        conn.commit()

def basic_words():  # заполняем базовыми словами
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("""
        INSERT INTO basic_words(russian_words, english_words)
            VALUES
                ('время', 'time'),
                ('мужчина', 'man'),
                ('женщина', 'woman'),
                ('мальчик', 'boy'),
                ('девочка', 'girl'),
                ('родители', 'parents'),
                ('отец', 'father'),
                ('сын', 'son'),
                ('дочь', 'daughter'),
                ('брат', 'brother'),
                ('мама', 'mother');
        """)
        cur.execute("""
        INSERT INTO all_words (source_table, russian_words, english_words)
            SELECT 'basic', russian_words, english_words FROM basic_words;
        """)
        conn.commit()

def user_words_write(rus_w: str, en_w: str): # добавление в БД слов
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(f"""
        INSERT INTO user_words(russian_words, english_words)
            VALUES (%s, %s);
        """, (rus_w, en_w))
        cur.execute("""
        INSERT INTO all_words (source_table, russian_words, english_words)
            SELECT 'user_words', russian_words, english_words FROM user_words;
        """)
        conn.commit()

def get_random_words_right():  # получение случайного слова из БД
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("""
        SELECT russian_words, english_words FROM all_words
            ORDER BY RANDOM() 
            LIMIT 1
        """)
        fetchone = cur.fetchone()
    return fetchone

def delete_words_from_tables(rus_w: str, en_w: str):
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("""
        DELETE FROM all_words
        WHERE russian_words = %s AND english_words = %s;
        """, (rus_w, en_w))
        conn.commit()

def get_others_words(exclude_word: str, count: int = 3):    # получение "ложных" вариантов
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("""
        SELECT english_words FROM all_words
            WHERE english_words != %s
            ORDER BY RANDOM()
            LIMIT %s
        """, (exclude_word, count))
        fetchall = [row[0] for row in cur.fetchall()]
    return fetchall


con = get_conn()
delete_tables()  # при первом запуске закомититить, далее раскомитить
create_tables()
basic_words()
con.close()