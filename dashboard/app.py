import streamlit as st
import sqlite3

st.set_page_config(layout="wide")
st.title("SkillifyMe: Research Internship Analytics")

conn = sqlite3.connect('data/skillifyme.db')
cur = conn.cursor()

st.header("Executive Summary")
cur.execute("SELECT COUNT(*) FROM respondents")
total = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM respondents WHERE intent >= 4")
high_intent = cur.fetchone()[0]

col1, col2 = st.columns(2)
col1.metric("Total Valid Respondents", total)
col2.metric("High Intent Segment", high_intent)

st.header("Problem Prioritization")
priority_query = """
WITH prev AS (
    SELECT pain_point, COUNT(DISTINCT respondent_id) * 1.0 / (SELECT COUNT(*) FROM respondents) as prev, AVG(pain_severity) as sev 
    FROM pain_points GROUP BY pain_point
) 
SELECT pain_point, ROUND(prev*100, 1) as prev_pct, ROUND(sev, 2) as severity, ROUND(prev*sev*100, 1) as score 
FROM prev ORDER BY score DESC
"""
cur.execute(priority_query)
rows = cur.fetchall()

# Build a Markdown table to avoid using pandas
md_table = "| Pain Point | Prevalence % | Severity (1-5) | Priority Score |\\n|---|---|---|---|\\n"
for r in rows:
    md_table += f"| {r[0]} | {r[1]}% | {r[2]} | {r[3]} |\\n"
    
st.markdown(md_table)

st.header("Funnel Analysis")
funnel_query = """
SELECT 
    COUNT(*) as total, 
    SUM(CASE WHEN intent >= 4 THEN 1 ELSE 0 END) as high_interest, 
    SUM(CASE WHEN intent >= 4 AND hours_available >= 10 THEN 1 ELSE 0 END) as interested_with_time, 
    SUM(CASE WHEN intent >= 4 AND hours_available >= 10 AND willing_to_pay = 1 THEN 1 ELSE 0 END) as hql 
FROM respondents;
"""
cur.execute(funnel_query)
f_row = cur.fetchone()
f_table = "| Funnel Stage | Count |\\n|---|---|\\n"
f_table += f"| Total Students | {f_row[0]} |\\n"
f_table += f"| High Interest | {f_row[1]} |\\n"
f_table += f"| With Time | {f_row[2]} |\\n"
f_table += f"| Willing to Pay | {f_row[3]} |\\n"
st.markdown(f_table)
