import seaborn as sns
from faicons import icon_svg

# Import data from shared.py
from shared import app_dir, df

from shiny import reactive
from shiny.express import input, render, ui

ui.page_opts(title="Penguins dashboard", fillable=True)


with ui.sidebar(title="Filter controls"):
    ui.input_slider("mass", "Mass", 2000, 6000, 6000)
    ui.input_checkbox_group(
        "species",
        "Species",
        ["Adelie", "Gentoo", "Chinstrap"],
        selected=["Adelie", "Gentoo", "Chinstrap"],
    )


with ui.layout_column_wrap(fill=False):
    with ui.value_box(showcase=icon_svg("earlybirds")):
        "Number of penguins"

        @render.text
        def count():
            return filtered_df().shape[0]

    with ui.value_box(showcase=icon_svg("ruler-horizontal")):
        "Average bill length"

        @render.text
        def bill_length():
            return f"{filtered_df()['bill_length_mm'].mean():.1f} mm"

    with ui.value_box(showcase=icon_svg("ruler-vertical")):
        "Average bill depth"

        @render.text
        def bill_depth():
            return f"{filtered_df()['bill_depth_mm'].mean():.1f} mm"


with ui.layout_columns():
    with ui.card(full_screen=True):
        ui.card_header("Bill length and depth")

        @render.plot
        def length_depth():
            return sns.scatterplot(
                data=filtered_df(),
                x="bill_length_mm",
                y="bill_depth_mm",
                hue="species",
            )

    with ui.card(full_screen=True):
        ui.card_header("Penguin data")

        @render.data_frame
        def data_frame():
            df_display = filtered_df().copy(deep=True)
            df_display["pass"] = [
                ui.div(
                    ui.input_action_button(
                        f"pass_btn_{i}", "Pass", class_="btn-success btn-sm"
                    ),
                    ui.input_action_button(
                        f"fail_btn_{i}", "Fail", class_="btn-danger btn-sm"
                    ),
                    style="display: flex; gap: 4px;"
                )
                for i in df_display.index
            ]
            return render.DataGrid(df_display)


ui.include_css(app_dir / "styles.css")


@reactive.calc
def filtered_df():
    filt_df = df[df["species"].isin(input.species())]
    filt_df = filt_df.loc[filt_df["body_mass_g"] < input.mass()]
    return filt_df


@reactive.effect
def handle_actions():
    for idx in filtered_df().index:
        if input[f"pass_btn_{idx}"]() > 0:
            df.loc[idx, "pass"] = True
            df.to_csv(app_dir / "penguins.csv", index=False)
        
        if input[f"fail_btn_{idx}"]() > 0:
            df.loc[idx, "pass"] = False
            df.to_csv(app_dir / "penguins.csv", index=False)


# @reactive.effect
# def save_edits():
#     # Only save when there are actual changes
#     if data_frame.data_view() is not None:
#         # Convert the edited data to a pandas DataFrame
#         edited_df = data_frame.data_view()
#         # Save to CSV (or whatever format your original file is in)
#         edited_df.to_csv(app_dir / "penguins.csv", index=False)