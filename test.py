from dotenv import load_dotenv
import os
import psycopg2
import pandas as pd
from faicons import icon_svg

from shiny.express import render, ui, input, output
from shiny import reactive
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

ui.page_opts(title="HF in your LLM application!", fillable=True)


with ui.sidebar(title="Table selection"):
    ui.input_select(
        "select_table",
        "Select Table:",
        choices=["test_hf_following_questions", "test_hf_title"],
        selected="test_hf_title"
    )

with ui.layout_column_wrap(fill=False):
    with ui.value_box(showcase=icon_svg("database")):
        "Number of Data"

        @render.text
        def count():
            return data().shape[0]

    with ui.value_box(showcase=icon_svg("star")):
        "Total passed responses"
        ui.input_text("total_passed_response", "", width="50px")

    with ui.value_box(showcase=icon_svg("chart-simple")):
        "Average passing rate"
        ui.input_text("passing_rate", "", width="80px", value="0%")


with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("LLM application data")

        @render.data_frame
        def data_frame():
            df_display = data().copy(deep=True)
            df_display["pass"] = [
                ui.div(
                    ui.input_switch(f"pass_btn_{i}", "Pass", value=True),
                    ui.update_text(id = f"pass_btn_{i}", label = "Passed"),
                )
                for i in df_display.index
            ]
            return render.DataGrid(df_display)


ui.include_css("dashboard/styles.css")

@reactive.Calc
def db_info():
    conn = get_db_connection()
    stmt = "SELECT datname || ' | ' || datid FROM pg_stat_activity WHERE state = 'active';"
    cursor = conn.cursor()
    cursor.execute(stmt)
    res = cursor.fetchall()
    conn.close()
    return f"Table: {input.select_table()}"

@reactive.Calc
def data():
    conn = get_db_connection()
    stmt = f"SELECT input, output, pass, explanation FROM {input.select_table()}"
    df = pd.read_sql(stmt, con=conn)
    conn.close()
    return df


@reactive.effect
def handle_actions():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for idx in data().index:
        new_pass_value = input[f"pass_btn_{idx}"]()
        data().loc[idx, "pass"] = new_pass_value
        
        stmt = f"""
            UPDATE {input.select_table()}
            SET pass = %s
            WHERE input = %s AND output = %s
        """
        cursor.execute(stmt, (new_pass_value, data().loc[idx, "input"], data().loc[idx, "output"]))
        status_text = "Passed" if new_pass_value else "Not Passed"
        ui.update_text(id = f"pass_btn_{idx}", label = status_text)
        ui.update_text(id="total_passed_response", value=data()[data()["pass"] == True].shape[0])
        ui.update_text(id="passing_rate", value=f"{data()[data()['pass'] == True].shape[0] / data().shape[0] * 100:.1f}%")
    conn.commit()
    conn.close()
