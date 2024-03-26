import mysql.connector

class MySqlConnection:
    def __init__(self):
        self.conn = None
        self.cur = None
        self.connect()

    def connect(self):
        try:
            self.conn = mysql.connector.connect(host="localhost", user="root", password="linux", database="attendance")
            self.cur = self.conn.cursor()
        except mysql.connector.Error as err:
            print(f"Error connecting to MySQL: {err}")

    def reconnect(self):
        self.close()
        self.connect()

    def insert(self, sql_query, values):
        try:
            if not self.conn.is_connected():
                self.reconnect()
            self.cur.execute(sql_query, values)
            self.conn.commit()
        except mysql.connector.Error as err:
            print(f"Error executing insert query: {err}")

    def read(self, sql_query, params=None):
        try:
            if not self.conn.is_connected():
                self.reconnect()
            if params is None:
                self.cur.execute(sql_query)
            else:
                self.cur.execute(sql_query, params)
            result = self.cur.fetchall()
            return result
        except mysql.connector.Error as err:
            print(f"Error executing read query: {err}")
            return None

    def create(self, sql_query):
        try:
            if not self.conn.is_connected():
                self.reconnect()
            self.cur.execute(sql_query)
            self.conn.commit()
        except mysql.connector.Error as err:
            print(f"Error executing create query: {err}")

    def update(self, sql_query, values):
        try:
            if not self.conn.is_connected():
                self.reconnect()
            self.cur.execute(sql_query, values)
            self.conn.commit()
        except mysql.connector.Error as err:
            print(f"Error executing update query: {err}")

    def delete(self, sql_query, values):
        try:
            if not self.conn.is_connected():
                self.reconnect()
            self.cur.execute(sql_query, values)
            self.conn.commit()
        except mysql.connector.Error as err:
            print(f"Error executing delete query: {err}")

    def close(self):
        try:
            if self.cur:
                self.cur.close()
            if self.conn:
                self.conn.close()
        except mysql.connector.Error as err:
            print(f"Error closing connection: {err}")

conn = MySqlConnection()
