from dotenv import load_dotenv
import os
import psycopg2
import pandas as pd

from shiny import App, render, ui, reactive
load_dotenv()


def get_db_connection() -> psycopg2.extensions.connection:
    """Get a connection to the PostgreSQL database.

    Returns:
        psycopg2.extensions.connection: Database connection object
    """
    return psycopg2.connect(
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOST"),
        database=os.getenv("POSTGRES_DB"),
        sslmode="disable",
    )

app_ui = ui.page_fluid(
    ui.h2("Shiny for Python Database Connections"),
    ui.input_select(
        id="select_data", 
        label="Selected Data:", 
        choices=["test_hf_following_questions", "test_hf_title"], 
        selected="test_hf_title"
    ),
    ui.hr(),
    ui.output_text(id="out_db_details"),
    ui.output_table(id="out_table")
)


def server(input, output, session):
    @reactive.Calc
    def db_info():
        conn = get_db_connection()
        stmt = "SELECT datname || ' | ' || datid FROM pg_stat_activity WHERE state = 'active';"
        cursor = conn.cursor()
        cursor.execute(stmt)
        res = cursor.fetchall()
        conn.close()
        return f"Table: {input.select_data()}"

    @reactive.Calc
    def data():
        conn = get_db_connection()
        stmt = f"SELECT input, output, pass, explanation FROM {input.select_data()}"
        df = pd.read_sql(stmt, con=conn)
        conn.close()
        return df


    @output
    @render.text
    def out_db_details():
        return f"Current database-> {db_info()}"

    @output
    @render.table
    def out_table():
        return data()


app = App(app_ui, server)