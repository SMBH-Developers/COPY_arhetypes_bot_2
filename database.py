import pymysql
from pymysql.connections import Connection


class Database:

    @staticmethod
    def connect() -> Connection:
        """

        :return: Connection
        """

        connection: Connection = pymysql.connect(
            user="root", passwd="root", host="localhost", database='COPY_arhtypes_bot_2', #TODO
            port=3306, autocommit=True)
        return connection

    def registrate_user(self, user):
        query = f"INSERT INTO Users (User_ID) VALUES ({user});"
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query)

    def check_if_user_exists(self, user_id: int):
        query = f"SELECT User_ID FROM Users WHERE User_ID={user_id};"
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query)
                is_exists = cursor.fetchone()

        if is_exists is None:
            return False
        return True

    def get_all_users_count(self) -> int:
        query = "SELECT COUNT(*) FROM Users"
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query)
                count = cursor.fetchone()[0]
        return count

    def get_today_users_count(self) -> int:
        query = "SELECT COUNT(*) FROM Users WHERE DATE(Registration_Date)=CURDATE();"
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query)
                count = cursor.fetchone()[0]
        return count

    def get_user_birthdate(self, user_id: int):
        query = f"SELECT birth_date FROM Users WHERE User_ID={user_id} LIMIT 1"
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query)
                birth_date = cursor.fetchone()[0]
        return birth_date

    def registrate_user_birthdate(self, user_id: int, birthdate: str):
        query = f"UPDATE Users SET birth_date=%s WHERE User_ID={user_id} LIMIT 1;"
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, (birthdate,))

    def set_or_unset_push(self, user_id: int, push_value: int):
        query = f"UPDATE Users SET is_getting_push={push_value} WHERE User_ID={user_id} LIMIT 1;"
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query)

    def check_if_push_set(self, user_id: int):
        query = f"SELECT is_getting_push FROM Users WHERE User_ID={user_id} LIMIT 1;"
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query)
                is_getting_push = cursor.fetchone()[0]
        return is_getting_push

    def get_users_with_step(self, step: int) -> tuple:
        query_to_get_users_id = f"SELECT User_ID FROM Users WHERE step=%s;"
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query_to_get_users_id, (step,))
                users = cursor.fetchall()
        return users

    def get_count_users_with_step(self, step: str) -> int:
        query_to_get_count_users_with_step = f"SELECT COUNT(*) FROM Users WHERE step={step};"
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query_to_get_count_users_with_step)
                count_users = cursor.fetchone()[0]
        return count_users

    def update_step(self, user_id: int | str) -> None:
        query_to_update_user_step = f"UPDATE Users SET step=step+1 WHERE User_ID={user_id} LIMIT 1;"
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query_to_update_user_step)

    def get_all_users(self) -> tuple:
        query_to_get_users_id = "SELECT User_ID FROM Users;"
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query_to_get_users_id)
                users = cursor.fetchall()
        return users

    def get_count_all_users(self) -> int:
        query_to_get_users_id = "SELECT COUNT(*) FROM Users;"
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query_to_get_users_id)
                count_users = cursor.fetchone()[0]
        return count_users

    def update_user_sex(self, user_id: int, sex: str) -> None:
        query = "UPDATE Users SET sex=%s WHERE user_id=%s LIMIT 1;"
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, (sex, user_id))

    def update_user_birth_date(self, user_id: int, birth_date: str) -> None:
        query = "UPDATE Users SET birth_date=%s WHERE user_id=%s LIMIT 1;"
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, (birth_date, user_id))

    def update_user_birth_place(self, user_id: int, birth_place: str) -> None:
        query = "UPDATE Users SET birth_place=%s WHERE user_id=%s LIMIT 1;"
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, (birth_place, user_id))

    def get_daily_arh_step(self, user_id):
        query = f"SELECT daily_arh_step FROM Users WHERE User_ID={user_id} LIMIT 1;"
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query)
                step = cursor.fetchone()
        return step[0]

    def update_daily_arh_step(self):
        query = "UPDATE Users SET daily_arh_step=IF(daily_arh_step=4, 0, daily_arh_step+1);"
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query)

    def get_users_2h_autosending(self):
        query = "SELECT User_ID FROM Users WHERE Got_2h_autosending IS NULL AND TIMESTAMPDIFF(HOUR, Registration_Date, NOW())>=2;"
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query)
                users = cursor.fetchall()
        return [int(user_id[0]) for user_id in users]

    def mark_got_2h_autosending(self, user_id):
        query = f"UPDATE Users SET Got_2h_autosending=NOW() WHERE User_ID={user_id} LIMIT 1;"
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query)

    def get_users_24h_autosending(self):
        query = "SELECT User_ID FROM Users WHERE Got_24h_autosending IS NULL AND TIMESTAMPDIFF(HOUR, Got_2h_autosending, NOW())>=22;"
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query)
                users = cursor.fetchall()
        return [int(user_id[0]) for user_id in users]

    def mark_got_24h_autosending(self, user_id):
        query = f"UPDATE Users SET Got_24h_autosending=NOW() WHERE User_ID={user_id} LIMIT 1;"
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query)

    def get_users_48h_autosending(self):
        query = "SELECT User_ID FROM Users WHERE Got_48h_autosending IS NULL AND TIMESTAMPDIFF(HOUR, Got_24h_autosending, NOW())>=24;"
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query)
                users = cursor.fetchall()
        return [int(user_id[0]) for user_id in users]

    def mark_got_48h_autosending(self, user_id):
        query = f"UPDATE Users SET Got_48h_autosending=NOW() WHERE User_ID={user_id} LIMIT 1;"
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query)


    def get_users_72h_autosending(self):
        query = "SELECT User_ID FROM Users WHERE Got_72h_autosending IS NULL AND TIMESTAMPDIFF(HOUR, Got_48h_autosending, NOW())>=24;"
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query)
                users = cursor.fetchall()
        return [int(user_id[0]) for user_id in users]

    def mark_got_72h_autosending(self, user_id):
        query = f"UPDATE Users SET Got_72h_autosending=NOW() WHERE User_ID={user_id} LIMIT 1;"
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query)

    def delete_user(self, user):
        query = f"DELETE FROM Users WHERE User_ID={user} LIMIT 1;"
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query)

    def set_newsletter(self, user_id):
        query = f"UPDATE Users SET sending_4_april=NOW() WHERE User_ID={user_id}"
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query)

    def get_users_for_sending_newsletter(self):
        query = "SELECT User_ID FROM Users WHERE sending_4_april IS NULL;"
        with self.connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query)
                values = cursor.fetchall()
        return [str(value[0]) for value in values]

