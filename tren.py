import sqlite3
import re

conn = sqlite3.connect('data.db')
c = conn.cursor()


def column_name():
    c.execute('SELECT * FROM anthropometry')

    column_names = [description[0] for description in c.description]

    conn.close()

    return column_names


# print(type(column_name()[5]))


def receiving_data() -> None:
    """Получаем значение счетчика"""
    user_id = 5281543691
    c.execute(
        f"SELECT weight FROM anthropometry WHERE user_id = ?",
        (user_id,)
    )
    result = c.fetchone()[0]

    return result

# print(receiving_data())


pattern = r'^\d*\.?\d+$'

if re.match(pattern, '83'):
    print('Ypa')
else:
    print('He ypa')