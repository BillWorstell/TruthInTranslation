import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os

#############
# 1) Setup
#############
st.set_page_config(page_title="Truth In Translation — Story Navigator", layout="wide")

def make_html_table(df, selected_idx, font_size):
    """
    Builds an HTML table with a selected (bolded) row, plus a small JS snippet
    to scroll that selected row into center.
    """
    table_html = f'<table style="border-collapse:collapse; font-size:{font_size}px; width:100%;">'
    # Table header
    table_html += (
        "<thead>"
        "<tr style='background-color:#ddd;'>"
        "<th style='padding:4px;'>Line#</th>"
        "<th style='padding:4px;'>AKAN</th>"
        "<th style='padding:4px;'>ENGLISH</th>"
        "</tr>"
        "</thead>"
    )
    table_html += "<tbody>"

    for i, row in df.iterrows():
        bg_color = "#f9f9f9" if i % 2 == 0 else "#ffffff"

        # Bold & scroll target if it's the selected line
        if i == selected_idx:
            font_weight = "font-weight:bold;"
            selected_attr = ' selected-line="true"'
        else:
            font_weight = ""
            selected_attr = ""

        table_html += (
            f"<tr style='background-color:{bg_color}; {font_weight}'{selected_attr}>"
            f"<td style='padding:4px; width:50px; text-align:center;'>{i+1}</td>"
            f"<td style='padding:4px;'>{row['AKAN']}</td>"
            f"<td style='padding:4px;'>{row['ENGLISH']}</td>"
            "</tr>"
        )

    table_html += "</tbody></table>\n"
    # A small JS snippet to auto-scroll the selected line
    table_html += (
        "<script>\n"
        "document.addEventListener('DOMContentLoaded', function() {\n"
        "  var selectedRow = document.querySelector('tr[selected-line=\"true\"]');\n"
        "  if (selectedRow) {\n"
        "    selectedRow.scrollIntoView({block: 'center', inline: 'center', behavior: 'auto'});\n"
        "  }\n"
        "});\n"
        "</script>\n"
    )
    return table_html

#############
# 2) Main Code
#############

modes = ["StoryNavigator"]
selected_mode = st.sidebar.selectbox("Mode", modes)

if selected_mode == "StoryNavigator":
    st.sidebar.markdown("---")
    st.sidebar.header("Story Selection")

    # Path to your "AnanseStories.xlsx" (adjust as needed)
    master_xlsx = "D:/Truth In Translation/Akan/AnanseStories.xlsx"
    df_stories = pd.read_excel(master_xlsx)

    story_names = df_stories["Name"].tolist()
    story_titles = df_stories["Title"].tolist()
    name_to_title = dict(zip(story_names, story_titles))

    # The user chooses a story
    chosen_story_name = st.sidebar.selectbox("Choose a Story", story_names)
    chosen_title = name_to_title.get(chosen_story_name, "Unknown Title")

    # Use session_state to detect story changes
    if "selected_story" not in st.session_state:
        st.session_state["selected_story"] = chosen_story_name
    else:
        # If user picks a different story, reset line idx to 1
        if chosen_story_name != st.session_state["selected_story"]:
            st.session_state["line_idx"] = 1
        st.session_state["selected_story"] = chosen_story_name

    st.sidebar.write(f"**Selected**: {chosen_story_name} – {chosen_title}")

    # Build path for the chosen story
    story_folder = f"D:/Truth In Translation/Akan/{chosen_story_name}"
    aligned_xlsx_path = os.path.join(story_folder, "AkanEnglishAligned.xlsx")

    if not os.path.exists(aligned_xlsx_path):
        st.error(f"No aligned file found at {aligned_xlsx_path}.")
    else:
        df_aligned = pd.read_excel(aligned_xlsx_path)
        num_lines = len(df_aligned)
        if num_lines == 0:
            st.warning("This story has no lines in the alignment file.")
        else:
            st.sidebar.write(f"Total lines: {num_lines}")

            # We'll create 5 columns for the arrow buttons + slider
            col_left5, col_left1, col_slider, col_right1, col_right5 = st.sidebar.columns([1,1,4,1,1])

            # Initialize line_idx in session_state if needed
            if "line_idx" not in st.session_state:
                st.session_state.line_idx = 1

            # << button
            with col_left5:
                if st.button("<<", key="dec5"):
                    st.session_state.line_idx = max(1, st.session_state.line_idx - 5)

            # < button
            with col_left1:
                if st.button("<", key="dec1"):
                    st.session_state.line_idx = max(1, st.session_state.line_idx - 1)

            # > button (using HTML entity for '>')
            with col_right1:
                if st.button("&gt;", key="inc1"):
                    st.session_state.line_idx = min(num_lines, st.session_state.line_idx + 1)

            # >> button (using &gt;&gt;)
            with col_right5:
                if st.button("&gt;&gt;", key="inc5"):
                    st.session_state.line_idx = min(num_lines, st.session_state.line_idx + 5)

            # The slider
            with col_slider:
                new_val = st.slider(
                    "Select line #",
                    min_value=1,
                    max_value=num_lines,
                    value=st.session_state.line_idx,  # from session_state
                    step=1
                )
                if new_val != st.session_state.line_idx:
                    st.session_state.line_idx = new_val

            # Our final line index is from session_state
            line_idx = st.session_state.line_idx
            selected_idx = line_idx - 1

            # Font size
            font_size = st.sidebar.slider("Font Size (px)", 10, 36, 14, 1)

            st.title("‘Spider-stories’")
            st.write(f"**Story**: {chosen_story_name}, **Line**: {line_idx} / {num_lines}")

            table_html = make_html_table(df_aligned, selected_idx, font_size)
            components.html(table_html, height=600, scrolling=True)

            st.info("Click the line slider or the arrow buttons to navigate. The selected line auto-scrolls to center.")

else:
    st.write("Other modes go here...")
