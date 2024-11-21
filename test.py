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
    Raises:
        psycopg2.Error: If connection fails
    """
    try:
        return psycopg2.connect(
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            host=os.getenv("POSTGRES_HOST"),
            database=os.getenv("POSTGRES_DB"),
            sslmode="disable",
        )
    except psycopg2.Error as e:
        print(f"Database connection failed: {e}")
        raise

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
            df_display["pass"] = df_display["pass"].map({'true': True, 'false': False})
            
            df_display["pass"] = [
                ui.div(
                    ui.input_switch(f"pass_btn_{i}", "Pass", value=df_display.loc[i, "pass"]),
                    ui.update_text(id = f"pass_btn_{i}", label = "Passed" if df_display.loc[i, "pass"] else "Not Passed"),
                )
                for i in df_display.index
            ]
            df_display["explanation"] = [
                ui.div(
                    ui.input_text(f"explanation_{i}", "Why it is passed or not?", value=""),
                )
                for i in df_display.index
            ]
            return render.DataGrid(df_display, editable=True)


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
    try:
        # Check if the data is available and inputs are initialized
        df = data()
        if df.empty:
            return

        conn = get_db_connection()
        cursor = conn.cursor()
        
        updates = []
        for idx in df.index:
            try:
                new_pass_value = input[f"pass_btn_{idx}"]()
                new_explanation_value = input[f"explanation_{idx}"]()
            except Exception:
                continue
                
            df.loc[idx, "pass"] = new_pass_value
            
            # Only update explanation if there's a new non-empty value
            if new_explanation_value:
                df.loc[idx, "explanation"] = new_explanation_value
                updates.append((new_pass_value, new_explanation_value, 
                              df.loc[idx, "input"], df.loc[idx, "output"]))
            else:
                # Keep the existing explanation value from the database
                updates.append((new_pass_value, df.loc[idx, "explanation"], 
                              df.loc[idx, "input"], df.loc[idx, "output"]))
            
            status_text = "Passed" if new_pass_value else "Not Passed"
            ui.update_text(id=f"pass_btn_{idx}", label=status_text)

        # Only proceed with updates if we have data to update
        if updates:
            stmt = f"""
                UPDATE {input.select_table()}
                SET pass = %s, explanation = %s
                WHERE input = %s AND output = %s
            """
            cursor.executemany(stmt, updates)
            
            total_passed = df[df["pass"] == True].shape[0]
            total_records = df.shape[0]
            passing_rate = (total_passed / total_records * 100) if total_records > 0 else 0
            
            ui.update_text(id="total_passed_response", value=str(total_passed))
            ui.update_text(id="passing_rate", value=f"{passing_rate:.1f}%")

            conn.commit()
            
    except Exception as e:
        print(f"Error in handle_actions: {e}")
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'conn' in locals():
            conn.close()
