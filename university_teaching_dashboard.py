# -*- coding: utf-8 -*-

# === MNLU University Teaching Dashboard (Phase 3 - Syllabus Filter Added) ===
import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import plotly.express as px
from rapidfuzz import fuzz

st.set_page_config(page_title="MNLU NEP/NAAC Teaching Dashboard", layout="wide")
st.title("📊 MNLU Teaching Methods & NEP/NAAC Compliance Dashboard")

# === Sidebar Upload ===
st.sidebar.header("📂 Upload Required Files")
data_file = st.sidebar.file_uploader("Upload Attendance Excel", type=["xlsx"])
syllabus_file = st.sidebar.file_uploader("Upload Syllabus Excel", type=["xlsx"])

if data_file and syllabus_file:
    df = pd.read_excel(data_file)
    s_df = pd.read_excel(syllabus_file)

    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    s_df.columns = s_df.columns.str.strip().str.lower().str.replace(" ", "_")

    df = df.rename(columns={'course_': 'course_code','course': 'course_group','course_subtopic': 'subtopic'})
    s_df['status'] = s_df['status'].astype(str).str.lower().str.strip()
    df['remedial_class'] = df['remedial_class'].fillna('No').astype(str).str.lower()

    st.write("✅ Available columns in uploaded attendance file:", df.columns.tolist())

    # === Sidebar Filters ===
    st.sidebar.header("🔎 Filter Options")
    selected_faculty = st.sidebar.multiselect("Faculty", df['faculty_name'].dropna().unique())
    selected_semester = st.sidebar.multiselect("Semester", sorted(df['semester'].dropna().unique()))
    selected_course_group = st.sidebar.multiselect("Course Group", df['course_group'].dropna().unique())

    filtered_df = df.copy()
    if selected_faculty:
        filtered_df = filtered_df[filtered_df['faculty_name'].isin(selected_faculty)]
    if selected_semester:
        filtered_df = filtered_df[filtered_df['semester'].isin(selected_semester)]
    if selected_course_group:
        filtered_df = filtered_df[filtered_df['course_group'].isin(selected_course_group)]

    # === Categorization Maps ===
    method_category = {
        'field based': 'Experiential','seminar': 'Participative','group discussion': 'Participative',
        'peer learning': 'Peer','case method': 'Case Law','problem solving': 'Problem Solving',
        'quiz': 'Quiz','lecture': 'Lecture','project': 'Project Based','flipped': 'Flipped','industry': 'Industry'
    }

    tool_category = {
        'board & pen': 'Board & Pen','extempore': 'Speech','interactive board': 'ICT','ppt': 'ICT','lms': 'ICT',
        'audio': 'ICT','av': 'ICT','tv': 'ICT','zoom': 'Online','g class': 'Online','hybrid': 'Hybrid'
    }

    nep_tag = {
        'Experiential': 'Student-Centric','Participative': 'Student-Centric','Peer': 'Student-Centric',
        'Flipped': 'Blended','Lecture': 'Traditional','Problem Solving': 'Skill-Based','Project Based': 'Project-Based',
        'Case Law': 'Legal-Oriented','Quiz': 'Interactive','Industry': 'Experiential'
    }

    def map_category(text, mapping):
        text = str(text).lower()
        for key in mapping:
            if key in text:
                return mapping[key]
        return 'Other'

    filtered_df['method_category'] = filtered_df['teaching_method_used'].apply(lambda x: map_category(x, method_category))
    filtered_df['tool_category'] = filtered_df['teaching_tool_used'].apply(lambda x: map_category(x, tool_category))
    filtered_df['nep_class'] = filtered_df['method_category'].map(nep_tag).fillna('Other')

    # === Fuzzy Matching of Topics ===
    topic_column = (
        'topic_covered' if 'topic_covered' in filtered_df.columns else
        'topics_taught' if 'topics_taught' in filtered_df.columns else
        'unnamed:_3' if 'unnamed:_3' in filtered_df.columns else
        None
    )

    def fuzzy_match(topic, subtopics):
        scores = [(sub, fuzz.partial_ratio(str(topic).lower(), str(sub).lower())) for sub in subtopics]
        best_match = max(scores, key=lambda x: x[1])
        return best_match[0] if best_match[1] > 80 else 'No Match'

    if topic_column:
        filtered_df['matched_subtopic'] = filtered_df[topic_column].apply(lambda x: fuzzy_match(x, s_df['subtopic']))
    else:
        st.warning("❗ Topic column not found for fuzzy matching.")

    # === Convert numeric ===
    filtered_df['credits'] = pd.to_numeric(filtered_df['credits'], errors='coerce')
    filtered_df['marks'] = pd.to_numeric(filtered_df['marks'], errors='coerce')

    # === Syllabus Coverage Summary ===
    st.subheader("📘 Syllabus Coverage Summary Table")
    syllabus_coverage = s_df['status'].value_counts()
    st.bar_chart(syllabus_coverage)

    fig_cov, ax_cov = plt.subplots()
    ax_cov.pie(syllabus_coverage, labels=syllabus_coverage.index, autopct='%1.1f%%')
    ax_cov.axis('equal')
    st.pyplot(fig_cov)

    # === NEW: Syllabus Filter & Graph ===
    st.subheader("📚 Filter & Visualize Syllabus Coverage (Faculty/Course/Semester)")
    s_filter = st.selectbox("Choose Syllabus View:", ['Overall', 'By Course Group', 'By Semester', 'By Faculty'])

    if s_filter == 'By Course Group':
        coursewise = filtered_df.groupby('course_group')['matched_subtopic'].nunique().reset_index()
        coursewise = coursewise.rename(columns={'matched_subtopic': 'topics_covered'})
        total_per_course = s_df.groupby('course_group')['subtopic'].nunique().reset_index()
        syllabus_merge = pd.merge(coursewise, total_per_course, on='course_group', how='outer').fillna(0)
        syllabus_merge['%_covered'] = (syllabus_merge['topics_covered'] / syllabus_merge['subtopic']) * 100
        fig = px.bar(syllabus_merge, x='course_group', y='%_covered', title="Syllabus Coverage by Course Group")
        st.plotly_chart(fig)

    elif s_filter == 'By Semester':
        semwise = filtered_df.groupby('semester')['matched_subtopic'].nunique().reset_index()
        semwise = semwise.rename(columns={'matched_subtopic': 'topics_covered'})
        fig = px.bar(semwise, x='semester', y='topics_covered', title="Syllabus Topics Taught by Semester")
        st.plotly_chart(fig)

    elif s_filter == 'By Faculty':
        facultywise = filtered_df.groupby('faculty_name')['matched_subtopic'].nunique().reset_index()
        facultywise = facultywise.rename(columns={'matched_subtopic': 'topics_covered'})
        fig = px.bar(facultywise, x='faculty_name', y='topics_covered', title="Syllabus Topics Taught by Faculty")
        st.plotly_chart(fig)

    # === Teaching Method & Tool Distribution ===
    st.subheader("📈 Teaching Methods & Tools")
    fig_method = px.bar(filtered_df.groupby(['semester', 'method_category']).size().reset_index(name='count'),
                        x='semester', y='count', color='method_category', title="Teaching Methods by Semester")
    st.plotly_chart(fig_method)

    fig_tool = px.bar(filtered_df.groupby(['semester', 'tool_category']).size().reset_index(name='count'),
                      x='semester', y='count', color='tool_category', title="Teaching Tools by Semester")
    st.plotly_chart(fig_tool)

    # === Remedial ===
    st.subheader("🩺 Remedial Class Breakdown")
    remedial_df = filtered_df[filtered_df['remedial_class'] == 'yes']
    st.write("Remedial Methods")
    st.bar_chart(remedial_df['method_category'].value_counts())
    st.write("Remedial Tools")
    st.bar_chart(remedial_df['tool_category'].value_counts())

    # === Method vs Tool Heatmap ===
    st.subheader("🔥 Method vs Tool Heatmap")
    fig_heat, ax = plt.subplots(figsize=(10, 6))
    sns.heatmap(pd.crosstab(filtered_df['method_category'], filtered_df['tool_category']),
                annot=True, fmt="d", cmap="YlGnBu", ax=ax)
    st.pyplot(fig_heat)

    # === Credit / Marks Correlation ===
    st.subheader("🧮 Credit & Marks Correlation")
    summary_corr = filtered_df.groupby('method_category').agg({
        'credits': 'sum','marks': 'sum','teaching_method_used': 'count'
    }).rename(columns={'teaching_method_used': 'method_usage'})
    st.dataframe(summary_corr)

    # === NEP Classification ===
    st.subheader("🧭 NEP-aligned Classification Summary")
    st.bar_chart(filtered_df['nep_class'].value_counts())

    st.subheader("📊 Semester-wise NEP Compliance Score")
    compliance_score = filtered_df.groupby('semester')['nep_class'].apply(
        lambda x: sum(c in ['Student-Centric', 'Blended'] for c in x) / len(x) * 100)
    st.line_chart(compliance_score)

    # === Identity Summary ===
    st.subheader("🏷️ MNLUM Identity: Top 3 Methods & Tools")
    st.write("Top Teaching Methods")
    st.write(filtered_df['method_category'].value_counts().head(3))
    st.write("Top Teaching Tools")
    st.write(filtered_df['tool_category'].value_counts().head(3))

    # === Programme-wise Summary ===
    st.subheader("📚 Programme-wise Method & Tool Trends")
    for program in ['BALLB', 'PG', 'PG Diploma', 'Diploma', 'Certificate']:
        program_df = df[df['course_group'].str.contains(program, case=False, na=False)].copy()
        if not program_df.empty:
            program_df['method_category'] = program_df['teaching_method_used'].apply(lambda x: map_category(x, method_category))
            program_df['tool_category'] = program_df['teaching_tool_used'].apply(lambda x: map_category(x, tool_category))
            st.markdown(f"### 📘 {program} Programme")
            st.write("Top Methods")
            st.write(program_df['method_category'].value_counts().head(3))
            st.write("Top Tools")
            st.write(program_df['tool_category'].value_counts().head(3))

    # === View Data ===
    with st.expander("📄 View Raw Filtered Data"):
        st.dataframe(filtered_df)

else:
    st.info("📥 Please upload both Attendance and Syllabus Excel files to begin analysis.")
