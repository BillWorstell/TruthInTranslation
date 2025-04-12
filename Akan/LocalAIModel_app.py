import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os
import re
import string
from collections import defaultdict

###############################################################################
# 1) Page config
###############################################################################
st.set_page_config(page_title="Truth In Translation", layout="wide")

###############################################################################
# 2) Helpers for cleaning/normalizing text
###############################################################################
PUNCT_TO_STRIP = string.punctuation + "“”‘’…"

def clean_word(word):
    """Removes leading/trailing punctuation/quotes from a word."""
    return word.strip(PUNCT_TO_STRIP)

def normalize_text(t):
    """Replaces curly quotes/dashes with ASCII equivalents."""
    if not isinstance(t, str):
        return ""
    t = t.replace("“", '"').replace("”", '"')
    t = t.replace("‘", "'").replace("’", "'")
    t = t.replace("–", "-").replace("—", "-")
    return t

###############################################################################
# 3) The StoryNavigator table
###############################################################################
def make_html_table(df, selected_idx, font_size):
    """
    Builds an HTML table [Line#, AKAN, ENGLISH],
    highlights the selected row, and autoscrolls to it.
    """
    table_html = (
        f'<table style="border-collapse:collapse; font-size:{font_size}px; width:100%;">'
        "<thead>"
        "<tr style='background-color:#ddd;'>"
        "<th style='padding:4px;'>Line#</th>"
        "<th style='padding:4px;'>AKAN</th>"
        "<th style='padding:4px;'>ENGLISH</th>"
        "</tr>"
        "</thead>"
        "<tbody>"
    )
    for i, row in df.iterrows():
        bg_color = "#f9f9f9" if i % 2 == 0 else "#fff"
        fw = "font-weight:bold;" if i == selected_idx else ""
        sel = ' selected-line="true"' if i == selected_idx else ""
        table_html += (
            f"<tr style='background-color:{bg_color}; {fw}'{sel}>"
            f"<td style='padding:4px; text-align:center;'>{i+1}</td>"
            f"<td style='padding:4px;'>{row['AKAN']}</td>"
            f"<td style='padding:4px;'>{row['ENGLISH']}</td>"
            "</tr>"
        )
    table_html += "</tbody></table>"
    table_html += (
        "<script>"
        "document.addEventListener('DOMContentLoaded',function(){"
        "var s=document.querySelector('tr[selected-line=\"true\"]');"
        "if(s){s.scrollIntoView({block:'center', inline:'center'});}"
        "});</script>"
    )
    return table_html

###############################################################################
# 4) Extraction routines for sections
###############################################################################
def extract_section_by_bold_headings(cell_text, start_bold, end_bold_list):
    """
    Searches for "**start_bold**" and returns text until any "**end_bold**" from end_bold_list.
    """
    if not cell_text:
        return ""
    start_marker = f"**{start_bold}**"
    pat_start = re.compile(re.escape(start_marker), re.IGNORECASE)
    m_start = pat_start.search(cell_text)
    if not m_start:
        return ""
    st_idx = m_start.end()
    subsequent = cell_text[st_idx:]
    min_end_pos = None
    for e_bold in end_bold_list:
        pat_end = re.compile(re.escape(f"**{e_bold}**"), re.IGNORECASE)
        m_end = pat_end.search(subsequent)
        if m_end:
            pos = m_end.start()
            if min_end_pos is None or pos < min_end_pos:
                min_end_pos = pos
    if min_end_pos is not None:
        return subsequent[:min_end_pos]
    else:
        return subsequent

def extract_section_generic(cell_text, header, next_headers):
    """
    Fallback: searches for a line like "2. Cultural Context: ... " ignoring bold.
    """
    pattern = re.compile(
        rf"(?i){re.escape(header)}\s*[:\-]\s*(.*?)(?=\d+\.\s*|$)",
        re.DOTALL
    )
    m = pattern.search(cell_text)
    if m:
        return m.group(1).strip()
    return ""

def parse_bullet_lines(text_block):
    """
    Returns lines that start with '- ' or '• ' from text_block, preserving them "as is."
    """
    if not text_block:
        return []
    lines = []
    for ln in text_block.splitlines():
        ln_stripped = ln.strip()
        if ln_stripped.startswith("- ") or ln_stripped.startswith("• "):
            # preserve entire line (dash, quotes, etc.)
            lines.append(ln)
    return lines

###############################################################################
# 5) Separate lines: 2+ "=>" -> literal; <2 => AI
###############################################################################
def separate_ai_vs_literal(ai_list, lit_list):
    """
    Lines with 2+ "=>" get assigned to 'literal',
    lines with <2 "=>" get assigned to 'ai'.
    """
    final_ai = []
    final_lit = []
    for line in ai_list:
        arrow_count = line.count("=>")
        if arrow_count >= 2:
            final_lit.append(line)
        else:
            final_ai.append(line)
    for line in lit_list:
        arrow_count = line.count("=>")
        if arrow_count < 2:
            final_ai.append(line)
        else:
            final_lit.append(line)
    return final_ai, final_lit

###############################################################################
# 6) parse_model_cell
###############################################################################
def parse_model_cell(cell_text):
    """
    Extracts AI, Literal, Cultural, Clarification from a single cell text.
    """
    res = {
        "AI_English_Full": "",
        "AI_English_Bullets": [],
        "Literal_Full": "",
        "Literal_Bullets": [],
        "Cultural": "",
        "Clarification": ""
    }
    if not isinstance(cell_text, str):
        return res

    cell_text = normalize_text(cell_text)

    # AI section
    ai_block = extract_section_by_bold_headings(
        cell_text,
        "AI English Translation",
        ["1. Literal Translation Mapping", "2. Cultural Context", "3. Translation Clarification", "Footnote"]
    )
    if not ai_block.strip():
        # fallback
        m = re.search(r"(?i)English Translation:\s*(.*?)\s*(?=\d+\.\s*Literal Translation Mapping:|\s*$)",
                      cell_text, flags=re.DOTALL)
        if m:
            ai_block = m.group(1)
    ai_bullets = parse_bullet_lines(ai_block)
    res["AI_English_Full"] = ai_block.strip()

    # Literal
    lit_block = extract_section_by_bold_headings(
        cell_text,
        "1. Literal Translation Mapping",
        ["2. Cultural Context", "3. Translation Clarification", "Footnote"]
    )
    lit_bullets = parse_bullet_lines(lit_block)
    res["Literal_Full"] = lit_block.strip()

    # Cultural
    cult_block = extract_section_by_bold_headings(
        cell_text,
        "2. Cultural Context",
        ["3. Translation Clarification", "Footnote"]
    ).strip()
    if not cult_block:
        cult_block = extract_section_generic(cell_text, "2. Cultural Context", ["3. Translation Clarification","Footnote"])
    res["Cultural"] = cult_block

    # Clarification
    clar_block = extract_section_by_bold_headings(
        cell_text,
        "3. Translation Clarification",
        ["Footnote"]
    ).strip()
    if not clar_block:
        clar_block = extract_section_generic(cell_text, "3. Translation Clarification", ["Footnote"])
    res["Clarification"] = clar_block

    # separate lines
    final_ai, final_lit = separate_ai_vs_literal(ai_bullets, lit_bullets)
    res["AI_English_Bullets"] = final_ai
    res["Literal_Bullets"] = final_lit
    return res

###############################################################################
# 7) POS color map
###############################################################################
POS_COLOR_MAP = {
    "pronoun": "blue",
    "verb": "red",
    "adverb": "green",
    "adjective": "darkorange",
    "conjunction": "teal",
    "preposition": "brown",
    "punctuation": "gray",
    "auxiliary verb": "purple",
    "contraction": "darkred",
    "noun": "navy",
    "interjection": "olive"
}

###############################################################################
# 8) bullet-on colorizing entire bullet line by final substring's POS
###############################################################################
def colorize_full_bullet_line(line: str, color_pos_on: bool) -> str:
    """
    Color the entire bullet line if final => substring is recognized as POS.
    Otherwise uncolored.
    """
    # keep original line intact, only strip leading spaces
    raw_line = line.lstrip("\t ")
    splitted = re.split(r'\s*=>\s*', raw_line)
    splitted = [p.strip().strip('"') for p in splitted if p.strip()]
    if len(splitted) == 0:
        return raw_line  # no parse
    pos_part = splitted[-1].lower()
    if color_pos_on and pos_part in POS_COLOR_MAP:
        color = POS_COLOR_MAP[pos_part]
        return f"<span style='color:{color};'>{raw_line}</span>"
    else:
        return raw_line

def build_section_rows_bullet_on(section_label, dict_of_lists, color_pos_on=False):
    """
    bullet-on => each bullet line is a row, unedited, color-coded by final => POS
    """
    model_names = sorted(dict_of_lists.keys())
    max_len = max(len(dict_of_lists[m]) for m in model_names)
    rows = []
    for i in range(max_len):
        row_label = section_label if i == 0 else ""
        row_data = [row_label]
        for m in model_names:
            bullet_lines = dict_of_lists[m]
            if i < len(bullet_lines):
                line_html = colorize_full_bullet_line(bullet_lines[i], color_pos_on)
                row_data.append(line_html)
            else:
                row_data.append("")
        rows.append(row_data)
    return rows

###############################################################################
# 9) bullet-off logic
###############################################################################
def parse_bullet_line_for_english_substring(line: str, color_pos_on: bool) -> str:
    """
    bullet-off (AI lines)
    skip first => skip last => ...
    """
    line_nobullet = re.sub(r'^[\s\-\u2022]+', '', line)
    parts = re.split(r'\s*=>\s*', line_nobullet)
    parts = [p.strip().strip('"') for p in parts if p.strip()]

    if len(parts) == 0:
        return ""
    if len(parts) == 1:
        english_list = [parts[0]]
        pos_part = ""
    elif len(parts) == 2:
        english_list = [parts[0]]
        pos_part = parts[1].lower()
    else:
        pos_part = parts[-1].lower()
        middle = parts[1:-1]
        english_list = middle
    english_text = " ".join(english_list)
    if color_pos_on and pos_part in POS_COLOR_MAP:
        return f'<span style="color:{POS_COLOR_MAP[pos_part]};">{english_text}</span>'
    else:
        return english_text

def parse_bullet_line_for_literal_substring(line: str, color_pos_on: bool) -> str:
    """
    bullet-off literal lines => second substring is English, last substring is pos
    """
    line_nobullet = re.sub(r'^[\s\-\u2022]+', '', line)
    parts = re.split(r'\s*=>\s*', line_nobullet)
    parts = [p.strip().strip('"') for p in parts if p.strip()]
    if len(parts) < 2:
        return line_nobullet
    text = parts[1]
    pos_part = parts[-1].lower() if len(parts) > 2 else ""
    if color_pos_on and pos_part in POS_COLOR_MAP:
        return f'<span style="color:{POS_COLOR_MAP[pos_part]};">{text}</span>'
    else:
        return text

def parse_bullet_line_for_akan_substring(line: str, color_pos_on: bool) -> str:
    """
    bullet-off literal => Akan is first substring, color by last substring if recognized
    """
    line_nobullet = re.sub(r'^[\s\-\u2022]+', '', line)
    parts = re.split(r'\s*=>\s*', line_nobullet)
    parts = [p.strip().strip('"') for p in parts if p.strip()]
    if len(parts) == 0:
        return ""
    if len(parts) == 1:
        akan_token = parts[0]
        pos_part = ""
    elif len(parts) == 2:
        akan_token = parts[0]
        pos_part = parts[1].lower()
    else:
        akan_token = parts[0]
        pos_part = parts[-1].lower()
    if color_pos_on and pos_part in POS_COLOR_MAP:
        return f'<span style="color:{POS_COLOR_MAP[pos_part]};">{akan_token}</span>'
    else:
        return akan_token

def build_single_joined_akan_row(section_label, dict_of_lists, color_pos_on=False):
    """
    bullet-off => single row "Akan" from bullet lines
    """
    model_names = sorted(dict_of_lists.keys())
    if not any(dict_of_lists[m] for m in model_names):
        return []
    row_data = [section_label]
    for m in model_names:
        bullet_lines = dict_of_lists[m]
        tokens = []
        for bl in bullet_lines:
            tokens.append(parse_bullet_line_for_akan_substring(bl, color_pos_on))
        joined = " ".join(tokens)
        row_data.append(joined)
    return [row_data]

###############################################################################
# 10) bullet-off "joined" multi-line for literal or AI
###############################################################################
def build_section_rows_bullet_off_ai(dict_of_lists, color_pos_on=False):
    """
    Return dict model-> joined AI text
    """
    tokens_by_model = {}
    for m, lines in dict_of_lists.items():
        tlist = []
        for line in lines:
            tlist.append(parse_bullet_line_for_english_substring(line, color_pos_on))
        tokens_by_model[m] = " ".join(tlist)
    return tokens_by_model

def build_section_rows_bullet_off_literal(dict_of_lists, color_pos_on=False):
    """
    Return dict model-> joined literal text
    """
    tokens_by_model = {}
    for m, lines in dict_of_lists.items():
        tlist = []
        for line in lines:
            tlist.append(parse_bullet_line_for_literal_substring(line, color_pos_on))
        tokens_by_model[m] = " ".join(tlist)
    return tokens_by_model

###############################################################################
# 11) build_literal_akan_subtable
###############################################################################
def build_literal_akan_subtable(akan_text, model_names, model_bullet_lines, color_pos_on=False):
    """
    Called in some older versions for bullet-on literal mode,
    which we can keep for backward references. We color entire bullet lines.
    """
    if not any(model_bullet_lines[m] for m in model_names):
        return []
    header = [["Literal Translation Mapping"] + [""] * len(model_names)]
    rows = build_section_rows_bullet_on("", model_bullet_lines, color_pos_on=color_pos_on)
    return header + rows

###############################################################################
# 12) build big table and cultural/clar
###############################################################################
def build_cultural_or_clar_rows(section_label, dict_of_strings):
    model_names = sorted(dict_of_strings.keys())
    if all(not dict_of_strings[m].strip() for m in model_names):
        return []
    row_data = [section_label]
    for m in model_names:
        row_data.append(dict_of_strings[m])
    return [row_data]

def build_big_table_html(model_names, rows_data):
    num_cols = 1 + len(model_names)
    table_html = "<table style='border-collapse:collapse; width:100%; table-layout:fixed;'><colgroup>"
    for _ in range(num_cols):
        table_html += f"<col style='width:{100/num_cols}%;'>"
    table_html += "</colgroup><thead><tr style='background-color:#ddd;'>"
    table_html += "<th>Section</th>"
    for mn in model_names:
        table_html += f"<th>{mn}</th>"
    table_html += "</tr></thead><tbody>"
    alt = False
    for row in rows_data:
        bg = "#f9f9f9" if alt else "#fff"
        alt = not alt
        table_html += f"<tr style='background-color:{bg};'>"
        for cell in row:
            table_html += f"<td style='padding:4px; vertical-align:top; word-wrap:break-word;'>{cell}</td>"
        table_html += "</tr>"
    table_html += "</tbody></table>"
    return table_html

def make_transition_row(label, num_models):
    return [[label] + [""] * num_models]

###############################################################################
# 13) The main build function for AIModel
###############################################################################
def build_ai_model_display_for_line(row,
                                    model_cols,
                                    show_ai_bullets,
                                    show_literal_bullets,
                                    show_cultural,
                                    show_clarification,
                                    color_pos_on):
    akan_val = str(row.get("AKAN",""))
    ref_val = str(row.get("ReferenceEN",""))

    # parse each model
    model_data = {}
    for mc in model_cols:
        parsed = parse_model_cell(str(row.get(mc, "")))
        model_data[mc] = parsed

    model_names = sorted(model_cols)

    # LITERAL
    lit_dict_bullets = {m: model_data[m]["Literal_Bullets"] for m in model_names}
    lit_dict_full = {m: model_data[m]["Literal_Full"] for m in model_names}

    if show_literal_bullets and any(lit_dict_bullets[m] for m in model_names):
        # bullet-on => entire lines unedited, color-coded by final => pos
        # can either call build_literal_akan_subtable or do it directly
        # We'll do it directly for consistency
        # but let's just call build_literal_akan_subtable to keep references
        lit_rows = build_literal_akan_subtable(akan_val, model_names, lit_dict_bullets, color_pos_on)
    else:
        # bullet-off => produce single "Akan" row + "Literal English" row
        if any(lit_dict_bullets[m] for m in model_names):
            # gather Akan row
            akan_row_data = {}
            for m in model_names:
                lines = lit_dict_bullets[m]
                tokens = [parse_bullet_line_for_akan_substring(ln, color_pos_on) for ln in lines]
                akan_row_data[m] = " ".join(tokens)
            row1 = ["Akan"]
            for m in model_names:
                row1.append(akan_row_data[m])

            # gather Literal English row
            lit_data = build_section_rows_bullet_off_literal(lit_dict_bullets, color_pos_on)
            row2 = ["Literal English Translation"]
            for m in model_names:
                row2.append(lit_data[m])

            lit_rows = [row1, row2]
        else:
            # fallback => single row if any full literal
            if any(lit_dict_full[m].strip() for m in model_names):
                row_data = ["Literal English Translation"]
                for m in model_names:
                    row_data.append(lit_dict_full[m])
                lit_rows = [row_data]
            else:
                lit_rows = []

    # AI
    ai_dict_bullets = {m: model_data[m]["AI_English_Bullets"] for m in model_names}
    ai_dict_full = {m: model_data[m]["AI_English_Full"] for m in model_names}

    if show_ai_bullets and any(ai_dict_bullets[m] for m in model_names):
        # bullet-on => multi-row
        # we color entire line by final => pos
        # do build_section_rows_bullet_on
        ai_header = [["AI English Translation"] + [""]*len(model_names)]
        bullet_rows = build_section_rows_bullet_on("", ai_dict_bullets, color_pos_on)
        ai_rows = ai_header + bullet_rows
    else:
        # bullet-off => single row
        if any(ai_dict_bullets[m] for m in model_names):
            row_data = ["AI English Translation"]
            joined_map = build_section_rows_bullet_off_ai(ai_dict_bullets, color_pos_on)
            for m in model_names:
                row_data.append(joined_map[m])
            ai_rows = [row_data]
        else:
            # fallback => single row if there's any AI_Full
            if any(ai_dict_full[m].strip() for m in model_names):
                row_data = ["AI English Translation"]
                for m in model_names:
                    row_data.append(ai_dict_full[m])
                ai_rows = [row_data]
            else:
                ai_rows = []

    # Cultural / Clar
    cult_dict = {m: model_data[m]["Cultural"] for m in model_names}
    clar_dict = {m: model_data[m]["Clarification"] for m in model_names}
    cult_rows = build_cultural_or_clar_rows("Cultural Context", cult_dict) if show_cultural else []
    clar_rows = build_cultural_or_clar_rows("Translation Clarification", clar_dict) if show_clarification else []

    all_rows = []
    all_rows += lit_rows
    all_rows += ai_rows
    all_rows += cult_rows
    all_rows += clar_rows

    if not all_rows:
        table_html = "<p>[No data to display — toggles off or no recognized sections found]</p>"
    else:
        table_html = build_big_table_html(model_names, all_rows)

    return f"""
    <p><strong>AKAN:</strong> {akan_val}</p>
    <p><strong>ReferenceEN:</strong> {ref_val}</p>
    {table_html}
    """

###############################################################################
# 14) The main Streamlit app
###############################################################################
def main():
    st.sidebar.title("Truth In Translation")
    st.sidebar.markdown("---")

    # Single shared line_idx
    if "line_idx" not in st.session_state:
        st.session_state["line_idx"] = 1
    if "story" not in st.session_state:
        st.session_state["story"] = ""

    modes = ["StoryNavigator","AIModel"]
    selected_mode = st.sidebar.selectbox("Mode", modes)

    ###########################################################################
    # STORYNAVIGATOR
    ###########################################################################
    if selected_mode == "StoryNavigator":
        st.sidebar.markdown("---")
        st.sidebar.header("Story Selection")

        master_xlsx = "D:/Truth In Translation/Akan/AnanseStories.xlsx"
        df_stories = pd.read_excel(master_xlsx)
        story_names = df_stories["Name"].tolist()
        story_titles = df_stories["Title"].tolist()
        name_to_title = dict(zip(story_names, story_titles))

        # ensure st.session_state["story"] is valid
        if st.session_state["story"] not in story_names:
            st.session_state["story"] = story_names[0]

        chosen_story_name = st.sidebar.selectbox(
            "Choose a Story",
            story_names,
            index=story_names.index(st.session_state["story"])
        )
        chosen_title = name_to_title.get(chosen_story_name,"Unknown Title")

        # if user picks a different story, reset line idx
        if chosen_story_name != st.session_state["story"]:
            st.session_state["line_idx"] = 1
        st.session_state["story"] = chosen_story_name

        st.sidebar.write(f"**Selected**: {chosen_story_name} – {chosen_title}")

        story_folder = f"D:/Truth In Translation/Akan/{chosen_story_name}"
        aligned_path = os.path.join(story_folder,"AkanEnglishAligned.xlsx")
        if not os.path.exists(aligned_path):
            st.error(f"No aligned file found at {aligned_path}.")
            return

        df_aligned = pd.read_excel(aligned_path)
        if len(df_aligned) == 0:
            st.warning("No lines in alignment file.")
            return
        df_aligned.columns = ["AKAN","ENGLISH"]
        num_lines = len(df_aligned)
        st.sidebar.write(f"Total lines: {num_lines}")

        c5, c1, cslider, c1b, c5b = st.sidebar.columns([1,1,4,1,1])
        line_idx = st.session_state["line_idx"]

        with c5:
            if st.button("&lt;&lt;", key="dec5_story"):
                st.session_state["line_idx"] = max(1, line_idx - 5)
        with c1:
            if st.button("&lt;", key="dec1_story"):
                st.session_state["line_idx"] = max(1, line_idx - 1)
        with cslider:
            new_val = st.slider("Select line #",1,num_lines,line_idx,1)
            if new_val != line_idx:
                st.session_state["line_idx"] = new_val
        with c1b:
            if st.button("&gt;", key="inc1_story"):
                st.session_state["line_idx"] = min(num_lines, line_idx + 1)
        with c5b:
            if st.button("&gt;&gt;", key="inc5_story"):
                st.session_state["line_idx"] = min(num_lines, line_idx + 5)

        line_idx = st.session_state["line_idx"]
        selected_idx = line_idx - 1

        font_size = st.sidebar.slider("Font Size (px)",10,36,14,1)

        st.title("‘Spider-stories’")
        st.write(f"**Story**: {chosen_story_name}, **Line**: {line_idx} / {num_lines}")

        table_html = make_html_table(df_aligned, selected_idx, font_size)
        components.html(table_html, height=600, scrolling=True)

        st.info("Use arrow or slider to navigate lines. The selected line auto-scrolls to center.")

    ###########################################################################
    # AI MODEL
    ###########################################################################
    elif selected_mode == "AIModel":
        st.sidebar.markdown("---")
        st.sidebar.header("Story Selection")

        if "ai_mode_inited" not in st.session_state:
            st.session_state["ai_mode_inited"] = True
            # reorder: literal bullet first, AI bullet second
            st.session_state.setdefault("show_literal_bullets", False)
            st.session_state.setdefault("show_ai_bullets", False)
            st.session_state.setdefault("show_cultural", False)
            st.session_state.setdefault("show_clarification", False)
            st.session_state.setdefault("color_pos", True)

        master_xlsx = "D:/Truth In Translation/Akan/AnanseStories.xlsx"
        df_stories = pd.read_excel(master_xlsx)
        story_names = df_stories["Name"].tolist()
        story_titles = df_stories["Title"].tolist()
        name_to_title = dict(zip(story_names, story_titles))

        # ensure st.session_state["story"] is valid
        if st.session_state["story"] not in story_names:
            st.session_state["story"] = story_names[0]

        chosen_story_name = st.sidebar.selectbox(
            "Choose a Story",
            story_names,
            index=story_names.index(st.session_state["story"])
        )
        chosen_title = name_to_title.get(chosen_story_name,"Unknown Title")

        # if story changed, reset line
        if chosen_story_name != st.session_state["story"]:
            st.session_state["line_idx"] = 1
        st.session_state["story"] = chosen_story_name

        st.sidebar.write(f"**Selected**: {chosen_story_name} – {chosen_title}")

        story_folder = f"D:/Truth In Translation/Akan/{chosen_story_name}"
        aligned_file = os.path.join(story_folder,"AkanEnglishAligned.xlsx")
        if not os.path.exists(aligned_file):
            st.error(f"No aligned file found at {aligned_file}.")
            return

        df_ref = pd.read_excel(aligned_file)
        if len(df_ref.columns) < 2:
            st.error("Expecting at least 2 columns in the aligned file (AKAN, ENGLISH).")
            return
        df_ref.columns = ["AKAN","ReferenceEN"]

        models_xlsx = os.path.join(story_folder,"Models.xlsx")
        if not os.path.exists(models_xlsx):
            st.warning("No Models.xlsx found. We'll just show reference lines.")
            model_sheets=[]
        else:
            xls = pd.ExcelFile(models_xlsx)
            exist_sheets = xls.sheet_names
            model_sheets = [sh for sh in exist_sheets if sh.lower() not in ["metadata","reference"]]

        df_combined = df_ref.copy()
        for ms in model_sheets:
            df_m = pd.read_excel(models_xlsx, sheet_name=ms)
            if len(df_m.columns) >= 2:
                df_m.columns = ["AKAN", ms]
                df_combined = pd.merge(df_combined, df_m, on="AKAN", how="outer")

        num_lines = len(df_combined)
        st.sidebar.write(f"Found {len(model_sheets)} model sheets, {num_lines} lines total.")

        c5, c1, cslider, c1b, c5b = st.sidebar.columns([1,1,4,1,1])
        line_idx = st.session_state["line_idx"]

        with c5:
            if st.button("&lt;&lt;", key="dec5_ai"):
                st.session_state["line_idx"] = max(1, line_idx-5)
        with c1:
            if st.button("&lt;", key="dec1_ai"):
                st.session_state["line_idx"] = max(1, line_idx-1)
        with cslider:
            new_val = st.slider("Select line #",1,num_lines,line_idx,1)
            if new_val != line_idx:
                st.session_state["line_idx"] = new_val
        with c1b:
            if st.button("&gt;", key="inc1_ai"):
                st.session_state["line_idx"] = min(num_lines,line_idx+1)
        with c5b:
            if st.button("&gt;&gt;", key="inc5_ai"):
                st.session_state["line_idx"] = min(num_lines,line_idx+5)

        line_idx = st.session_state["line_idx"]
        selected_idx = line_idx - 1

        font_size = st.sidebar.slider("Font Size (px)",10,36,14,1)

        # reorder toggles so literal bullet is first
        with st.sidebar.expander("Display Options", expanded=True):
            st.session_state["show_literal_bullets"] = st.checkbox("Show Literal Translation Bullets?", value=st.session_state["show_literal_bullets"])
            st.session_state["show_ai_bullets"] = st.checkbox("Show AI English Bullets?", value=st.session_state["show_ai_bullets"])
            st.session_state["show_cultural"] = st.checkbox("Show Cultural Context?", value=st.session_state["show_cultural"])
            st.session_state["show_clarification"] = st.checkbox("Show Translation Clarification?", value=st.session_state["show_clarification"])
            st.session_state["color_pos"] = st.checkbox("Color Parts of Speech?", value=st.session_state["color_pos"])

        st.title("AIModel Comparison")
        st.write(f"**Story**: {chosen_story_name}, **Line**: {line_idx} / {num_lines}")

        if selected_idx < 0 or selected_idx >= num_lines:
            st.error("Line index out of range.")
            return

        all_cols = df_combined.columns.tolist()
        model_cols = [c for c in all_cols if c not in ["AKAN","ReferenceEN"]]

        show_literal_bullets = st.session_state["show_literal_bullets"]
        show_ai_bullets = st.session_state["show_ai_bullets"]
        show_cultural = st.session_state["show_cultural"]
        show_clarification = st.session_state["show_clarification"]
        color_pos_on = st.session_state["color_pos"]

        html_block = build_ai_model_display_for_line(
            row = df_combined.iloc[selected_idx],
            model_cols = model_cols,
            show_ai_bullets = show_ai_bullets,
            show_literal_bullets = show_literal_bullets,
            show_cultural = show_cultural,
            show_clarification = show_clarification,
            color_pos_on = color_pos_on
        )
        final_html = f"<div style='font-size:{font_size}px;'>{html_block}</div>"
        components.html(final_html,height=600,scrolling=True)

        st.info("Use arrow or slider to navigate lines. The selected line auto-scrolls to center.")

    else:
        st.write("Other modes go here...")

if __name__=="__main__":
    main()
