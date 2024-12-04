from dotenv import load_dotenv
import os
import logging
import pandas as pd
from faicons import icon_svg
from sqlalchemy import create_engine, text
from typing import Any

from shiny.express import render, ui, input, output
from shiny import reactive
from shiny import req

load_dotenv()
database = {"HF": "HF", "utoai_news": "NEWS"}
table_name = {"HF": "test_hf_followup_questions", "utoai_news": "reports_content"}
logger = logging.getLogger(__name__)

width_styles = [
    {
        "cols": ["report_id"],
        "style": {
            "minWidth": "100px",
            "maxWidth": "100px",
        },
    },
    {
        "cols": ["input"],
        "style": {
            "minWidth": "400px",
        },
    },
    {
        "cols": ["output"],
        "style": {
            "minWidth": "400px",
        },
    },
    {
        "cols": ["pass"],
        "style": {
            "minWidth": "150px",
            "maxWidth": "150px",
        },
    },
    {
        "cols": ["explanation"],
        "style": {
            "minWidth": "150px",
        },
    }
]


def get_db_connection(database: str) -> Any:
    """Get a SQLAlchemy engine connection to the PostgreSQL database.

    Returns:
        sqlalchemy.engine.Engine: Database engine object
    """
    try:
        db_url = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('POSTGRES_HOST')}/{os.getenv(f'POSTGRES_DATABASE_{database}')}?sslmode=disable"
        return create_engine(db_url)
    except Exception as e:
        print(f"Database connection failed: {e}")
        raise

ui.page_opts(title="HF in your LLM application!", fillable=True)

with ui.sidebar(title="Table selection"):
    ui.input_select(
        "select_table",
        "Select Table:",
        choices=["All labeled follow-up questions", "Unlabeled follow-up questions"],
        selected="Unlabeled follow-up questions"
    )

with ui.layout_column_wrap(fill=False):
    with ui.value_box(showcase=icon_svg("database")):
        "Number of Data"

        @render.text
        def count():
            if input.select_table() == "All labeled follow-up questions":
                return all_labeled_data().shape[0]
            else:
                return unlabeled_data().shape[0]

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
            if input.select_table() == "All labeled follow-up questions":
                df_display = all_labeled_data().copy(deep=True)
                df_display["pass"] = df_display["pass"].map({'true': True, 'false': False})
            else:
                df_display = unlabeled_data().copy(deep=True)
            
            df_display["input"] = [
                ui.div(
                    ui.div(title, class_="title-text", style="color: green;"),
                    ui.div(ui.markdown(summary), class_="summary-text"),
                )
                for title, summary in [
                    input_text.split("Summary: ", 1) 
                    for input_text in df_display["input"]
                ]
            ]

            df_display["output"] = [
                ui.div(
                    ui.tags.table(
                        [
                            ui.tags.tr(ui.tags.td(questions[i] if i < len(questions) else "", 
                             style=f"padding: 8px;"))
                            for i in range(3)
                        ],
                    )
                )
                for questions in df_display["output"]
            ]

            df_display["pass"] = [
                ui.div(
                    ui.tags.table(
                        [
                            ui.tags.tr(ui.tags.td(
                                ui.div([
                                    ui.input_radio_buttons(
                                        f"pass_btn_{i}_1",
                                        "",
                                        {
                                            "true": ui.span("Passed", style="color: #00AA00;"),
                                            "false": ui.span("Not Passed", style="color: #FF0000;"),
                                        },
                                        selected=df_display.loc[i, "pass"]
                                    ),
                                ], style="width: 120px; margin: auto;")
                            )),
                            ui.tags.tr(ui.tags.td(
                                ui.div([
                                    ui.input_radio_buttons(
                                        f"pass_btn_{i}_3",
                                        "",
                                        {
                                            "true": ui.span("Passed", style="color: #00AA00;"),
                                            "false": ui.span("Not Passed", style="color: #FF0000;"),
                                        },
                                        selected=df_display.loc[i, "pass"]
                                    ),
                                ], style="width: 120px; padding: 8px; margin: auto;")
                            )),
                            ui.tags.tr(ui.tags.td(
                                ui.div([
                                    ui.input_radio_buttons(
                                        f"pass_btn_{i}_3",
                                        "",
                                        {
                                            "true": ui.span("Passed", style="color: #00AA00;"),
                                            "false": ui.span("Not Passed", style="color: #FF0000;"),
                                        },
                                        selected=df_display.loc[i, "pass"]
                                    ),
                                ], style="width: 120px; padding: 8px; margin: auto;")
                            ))
                        ]
                    )
                )
                for i in df_display.index
            ]

            df_display["explanation"] = [
                ui.div(
                    ui.tags.table(
                        [
                            ui.tags.tr(ui.tags.td(
                                ui.input_text(f"explanation_{i}_1", "Explanation for Q1", value=df_display.loc[i, "explanation"][0] if isinstance(df_display.loc[i, "explanation"], list) else ""),
                                style="padding: 8px; margin: auto;"
                            )),
                            ui.tags.tr(ui.tags.td(
                                ui.input_text(f"explanation_{i}_2", "Explanation for Q2", value=df_display.loc[i, "explanation"][1] if isinstance(df_display.loc[i, "explanation"], list) else ""),
                                style="padding: 8px; margin: auto;"
                            )),
                            ui.tags.tr(ui.tags.td(
                                ui.input_text(f"explanation_{i}_3", "Explanation for Q3", value=df_display.loc[i, "explanation"][2] if isinstance(df_display.loc[i, "explanation"], list) else ""),
                                style="padding: 8px; margin: auto;"
                            ))
                        ]
                    )
                )
                for i in df_display.index
            ]
            return render.DataGrid(
                df_display, 
                styles=width_styles
            )
ui.input_action_button(
    "save_button",
    "Save labels",
    class_="btn-success"
)
ui.include_css("dashboard/styles.css")


@reactive.Calc
def all_labeled_data():
    conn = get_db_connection(database["HF"])
    labeled_table_name = table_name["HF"]
    stmt = f"SELECT report_id, input, output, pass, explanation FROM {labeled_table_name}"
    df = pd.read_sql(stmt, con=conn)
    conn.dispose()
    return df


@reactive.Calc
def unlabeled_data():
    utoai_news_engine = get_db_connection(database["utoai_news"])
    news_stmt = f"""
        SELECT 
            report_id,
            CONCAT('Title: ', title, 'Summary: ', summary) as input,
            followup_questions as output
        FROM "public"."reports_content"
    """
    try:
        news_df = pd.read_sql(news_stmt, con=utoai_news_engine)
    except Exception as e:
        logger.error(f"Query failed: {e}")
    finally:
        utoai_news_engine.dispose()

    hf_engine = get_db_connection(database["HF"])
    hf_stmt = f"""
        SELECT 
            report_id,
            pass,
            explanation
        FROM {table_name["HF"]}
        WHERE pass IS NOT NULL
    """
    hf_df = pd.read_sql(hf_stmt, con=hf_engine)
    hf_engine.dispose()

    # Merge the dataframes and filter for unprocessed records
    merged_df = news_df.merge(hf_df, on='report_id', how='left')
    unprocessed_df = merged_df[merged_df['pass'].isna()]
    
    return unprocessed_df


@reactive.effect
def save_labels():
    if not input.save_button():
        return
        
    try:
        if input.select_table() == "All labeled follow-up questions":
            return
        
        df_display = unlabeled_data().copy(deep=True)
        engine = get_db_connection(database["HF"])
        
        with engine.connect() as conn:
            with conn.begin():
                updates = []
                for idx in df_display.index:
                    try:
                        for i in range(1, 4):
                            pass_btn_id = f"pass_btn_{idx}_{i}"
                            explanation_id = f"explanation_{idx}_{i}"
                            report_id = f"{df_display.loc[idx, 'report_id']}_{i}"
                            
                            # Use req() to ensure inputs are ready
                            update = {}
                            try:
                                if pass_btn_value := req(input[pass_btn_id]()):
                                    update["pass"] = pass_btn_value
                            except:
                                pass
                            
                            try:
                                if explanation_value := req(input[explanation_id]()):
                                    update["explanation"] = explanation_value
                            except:
                                pass

                            if update:
                                update["report_id"] = report_id
                                update["input"] = df_display.loc[idx, "input"]
                                update["output"] = df_display.loc[idx, "output"][i-1] if isinstance(df_display.loc[idx, "output"], list) else df_display.loc[idx, "output"]
                                updates.append(update)
                    except Exception as row_error:
                        logger.error(f"Error processing row {idx}, question {i}: {str(row_error)}", exc_info=True)
                        return
                
                if updates:
                    for update in updates:
                        check_stmt = f"""SELECT report_id 
                                       FROM {table_name["HF"]} 
                                       WHERE report_id = :report_id"""
                        
                        check_result = conn.execute(text(check_stmt), update).fetchone()
                        
                        if check_result:
                            if "explanation" in update and "pass" in update: 
                                update_stmt = f"""UPDATE {table_name["HF"]}
                                                SET pass = CAST(:pass AS boolean), 
                                                explanation = :explanation,
                                                    output = :output
                                                    WHERE report_id = :report_id"""
                            elif "explanation" in update:
                                update_stmt = f"""UPDATE {table_name["HF"]}
                                                SET explanation = :explanation,
                                                    output = :output
                                                    WHERE report_id = :report_id"""
                            elif "pass" in update:
                                update_stmt = f"""UPDATE {table_name["HF"]}
                                                SET pass = CAST(:pass AS boolean), 
                                                    output = :output
                                                    WHERE report_id = :report_id"""
                        else:
                            if "explanation" not in update:
                                update["explanation"] = None
                            if "pass" not in update:
                                update["pass"] = None
                            update_stmt = f"""INSERT INTO {table_name["HF"]} 
                                            (pass, explanation, report_id, input, output)
                                        VALUES (CAST(:pass AS boolean), 
                                                :explanation, 
                                                :report_id, 
                                                :input, 
                                                :output)"""
                        
                        conn.execute(text(update_stmt), update)
                        
                labeled_data = all_labeled_data()
                total_passed = labeled_data[labeled_data["pass"] == True].shape[0]
                total_records = len(labeled_data)
                passing_rate = (total_passed / total_records * 100) if total_records > 0 else 0
                    
                ui.update_text(id="total_passed_response", value=str(total_passed))
                ui.update_text(id="passing_rate", value=f"{passing_rate:.1f}%")

    except Exception as e:
        logger.error(f"Error in save_labels: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Error details:", exc_info=True)  # This will log the full traceback
        raise
    finally:
        if 'engine' in locals():
            engine.dispose()


# @reactive.effect
# def handle_actions():
#     try:
#         df = data()
#         if df.empty:
#             return

#         conn = get_db_connection()
#         cursor = conn.cursor()
        
#         updates = []
#         for idx in df.index:
#             try:
#                 new_pass_value = input[f"pass_btn_{idx}"]()
#                 new_explanation_value = input[f"explanation_{idx}"]()
#             except Exception:
#                 continue
                
#             df.loc[idx, "pass"] = new_pass_value
            
#             # Only update explanation if there's a new non-empty value
#             if new_explanation_value:
#                 df.loc[idx, "explanation"] = new_explanation_value
#                 updates.append((new_pass_value, new_explanation_value, 
#                               df.loc[idx, "input"], df.loc[idx, "output"]))
#             else:
#                 # Keep the existing explanation value from the database
#                 updates.append((new_pass_value, df.loc[idx, "explanation"], 
#                               df.loc[idx, "input"], df.loc[idx, "output"]))
            
#             status_text = "Passed" if new_pass_value else "Not Passed"
#             ui.update_text(id=f"pass_btn_{idx}", label=status_text)

#         # Only proceed with updates if we have data to update
#         if updates:
#             stmt = f"""
#                 UPDATE {input.select_table()}
#                 SET pass = %s, explanation = %s
#                 WHERE input = %s AND output = %s
#             """
#             cursor.executemany(stmt, updates)
            
#             total_passed = df[df["pass"] == True].shape[0]
#             total_records = df.shape[0]
#             passing_rate = (total_passed / total_records * 100) if total_records > 0 else 0
            
#             ui.update_text(id="total_passed_response", value=str(total_passed))
#             ui.update_text(id="passing_rate", value=f"{passing_rate:.1f}%")

#             conn.commit()
            
#     except Exception as e:
#         print(f"Error in handle_actions: {e}")
#         if 'conn' in locals():
#             conn.rollback()
#     finally:
#         if 'conn' in locals():
#             conn.close()
