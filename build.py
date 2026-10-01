import os
import pandas as pd
import numpy as np

base_dir = r"d:\Professional Work\Business\Media_net\SkillifyMe_Analytics"
os.makedirs(base_dir, exist_ok=True)

def write_file(path, content):
    full_path = os.path.join(base_dir, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")

# ==========================================
# 1. MOCK DATA GENERATION
# ==========================================
print("Generating synthetic data...")
np.random.seed(42)
n = 1000
years = np.random.choice(['1st', '2nd', '3rd', '4th', 'Graduated'], n, p=[0.1, 0.2, 0.3, 0.3, 0.1])
domains = np.random.choice(['Engineering', 'Science', 'Arts', 'Commerce'], n)
goals = np.random.choice(['Software Engineer', 'Data Scientist', 'Researcher', 'Product Manager'], n)
tiers = np.random.choice(['Tier 1', 'Tier 2', 'Tier 3'], n, p=[0.15, 0.5, 0.35])

intent = np.clip(np.random.normal(3, 1, n).astype(int), 1, 5)
intent = np.where(goals == 'Researcher', np.clip(intent + 1, 1, 5), intent) # Bias intent based on goal

data = {
    'respondent_id': [f"R{str(i).zfill(4)}" for i in range(1, n+1)],
    'name': [f"Student_{i}" for i in range(n)],
    'email': [f"student{i}@test.com" for i in range(n)],
    'phone': [f"555-01{str(i).zfill(4)[-2:]}" for i in range(n)],
    'year_of_study': years,
    'domain': domains,
    'career_goal': goals,
    'college_tier': tiers,
    'pain_severity': np.clip(np.random.normal(3.5, 1, n).astype(int), 1, 5),
    'skill_research': np.clip(np.random.normal(2.5, 1, n).astype(int), 1, 5),
    'intent': intent,
    'hours_available': np.random.randint(0, 25, n),
    'willing_to_pay': np.where(intent >= 4, np.random.choice([0, 1], n, p=[0.4, 0.6]), np.random.choice([0, 1], n, p=[0.8, 0.2]))
}
pain_opts = ['Lack of practical experience', 'No mentorship', 'Poor portfolio', 'No research exposure', 'No industry connections']
data['pain_points'] = [",".join(np.random.choice(pain_opts, np.random.randint(1, 4), replace=False)) for _ in range(n)]

os.makedirs(os.path.join(base_dir, 'data', 'raw'), exist_ok=True)
pd.DataFrame(data).to_csv(os.path.join(base_dir, 'data', 'raw', 'survey_export.csv'), index=False)


# ==========================================
# 2. PYTHON PIPELINE SCRIPTS
# ==========================================
write_file("python/01_clean.py", """
import pandas as pd
import os

df = pd.read_csv('../data/raw/survey_export.csv')
initial_count = len(df)

# 1. Drop PII
df_clean = df.drop(columns=['name', 'email', 'phone'])

# 2. Filter invalid data (straight-lining / fake answers)
# Rule: If intent == 1 but willing_to_pay == 1 (contradictory)
valid_mask = ~((df_clean['intent'] == 1) & (df_clean['willing_to_pay'] == 1))
df_clean = df_clean[valid_mask]
filtered_count = len(df_clean)

# 3. Explode pain points for long format
df_pain = df_clean[['respondent_id', 'pain_points', 'pain_severity']].copy()
df_pain['pain_point'] = df_pain['pain_points'].str.split(',')
df_pain = df_pain.explode('pain_point').drop(columns=['pain_points'])

os.makedirs('../data/cleaned', exist_ok=True)
df_clean.drop(columns=['pain_points']).to_csv('../data/cleaned/respondents.csv', index=False)
df_pain.to_csv('../data/cleaned/pain_points.csv', index=False)

# Log
with open('../docs/cleaning_log.md', 'w') as f:
    f.write(f"# Cleaning Log\\n- Raw rows: {initial_count}\\n- Contradictory dropped: {initial_count - filtered_count}\\n- Final valid rows: {filtered_count}")
""")

write_file("python/02_load.py", """
import sqlite3
import pandas as pd
import os

# Using SQLite for zero-dependency seamless execution in this pipeline
db_path = '../data/skillifyme.db'
if os.path.exists(db_path):
    os.remove(db_path)
conn = sqlite3.connect(db_path)

with open('../sql/01_schema.sql', 'r') as f:
    conn.executescript(f.read())

pd.read_csv('../data/cleaned/respondents.csv').to_sql('respondents', conn, if_exists='append', index=False)
pd.read_csv('../data/cleaned/pain_points.csv').to_sql('pain_points', conn, if_exists='append', index=False)

print("Data loaded to SQLite database successfully.")
""")

write_file("python/03_stats.py", """
import pandas as pd
import numpy as np
import statsmodels.api as sm
from statsmodels.stats.proportion import proportion_confint
import os

df = pd.read_csv('../data/cleaned/respondents.csv')
os.makedirs('../outputs', exist_ok=True)

# 1. Wilson 95% CI
high_intent = len(df[df['intent'] >= 4])
total = len(df)
ci_low, ci_high = proportion_confint(high_intent, total, method='wilson')

# 2. Logistic Regression
df['high_intent'] = (df['intent'] >= 4).astype(int)
X = pd.get_dummies(df[['year_of_study', 'career_goal']], drop_first=True)
X['hours_available'] = df['hours_available']
X = sm.add_constant(X)
model = sm.Logit(df['high_intent'], X).fit(disp=0)

with open('../outputs/stats_results.txt', 'w') as f:
    f.write(f"High Intent Rate: {high_intent/total:.1%} (95% CI: {ci_low:.1%} - {ci_high:.1%})\\n\\n")
    f.write("Logistic Regression Drivers for Intent:\\n")
    f.write(model.summary().as_text())
""")

write_file("python/04_sizing.py", """
import numpy as np
import os

n_sims = 10000
reachable_students = 50000 

intent_rate = np.random.uniform(0.15, 0.25, n_sims)
application_rate = np.random.uniform(0.05, 0.15, n_sims)
acceptance_capacity = np.random.uniform(0.80, 0.95, n_sims)

expected_starts = reachable_students * intent_rate * application_rate * acceptance_capacity

with open('../outputs/sizing_results.txt', 'w') as f:
    f.write("Monte Carlo Simulation Results (10,000 runs)\\n")
    f.write(f"Base Case (Median) Completions: {np.median(expected_starts):.0f}\\n")
    f.write(f"Conservative (10th Pct): {np.percentile(expected_starts, 10):.0f}\\n")
    f.write(f"Optimistic (90th Pct): {np.percentile(expected_starts, 90):.0f}\\n")
""")


# ==========================================
# 3. SQL SCRIPTS
# ==========================================
write_file("sql/01_schema.sql", """
CREATE TABLE respondents (
    respondent_id VARCHAR PRIMARY KEY,
    year_of_study VARCHAR,
    domain VARCHAR,
    career_goal VARCHAR,
    college_tier VARCHAR,
    pain_severity INT,
    skill_research INT,
    intent INT,
    hours_available INT,
    willing_to_pay INT
);

CREATE TABLE pain_points (
    respondent_id VARCHAR,
    pain_point VARCHAR,
    pain_severity INT
);

CREATE VIEW v_respondent_flat AS
SELECT r.*, p.pain_point, p.pain_severity as item_severity
FROM respondents r
JOIN pain_points p ON r.respondent_id = p.respondent_id;
""")

write_file("sql/analysis/01_prevalence.sql", """
-- a. Prevalence and average severity
SELECT 
    pain_point,
    COUNT(DISTINCT respondent_id) as student_count,
    ROUND(AVG(pain_severity), 2) as avg_severity
FROM pain_points
GROUP BY pain_point
ORDER BY student_count DESC;
""")

write_file("sql/analysis/02_priority.sql", """
-- b. Priority score = prevalence x severity
WITH prev AS (
    SELECT 
        pain_point,
        COUNT(DISTINCT respondent_id) * 1.0 / (SELECT COUNT(*) FROM respondents) as prevalence,
        AVG(pain_severity) as severity
    FROM pain_points
    GROUP BY pain_point
)
SELECT 
    pain_point,
    ROUND(prevalence * 100, 2) as prevalence_pct,
    ROUND(severity, 2) as avg_severity,
    ROUND(prevalence * severity * 100, 2) as priority_score,
    RANK() OVER(ORDER BY prevalence * severity DESC) as rank
FROM prev;
""")

write_file("sql/analysis/03_segmentation.sql", """
-- c. Segmentation: pain-point share within career goal
SELECT 
    r.career_goal,
    p.pain_point,
    COUNT(r.respondent_id) as count,
    ROUND(COUNT(r.respondent_id) * 100.0 / SUM(COUNT(r.respondent_id)) OVER(PARTITION BY r.career_goal), 2) as pct_in_segment
FROM respondents r
JOIN pain_points p ON r.respondent_id = p.respondent_id
GROUP BY r.career_goal, p.pain_point;
""")

write_file("sql/analysis/04_funnel.sql", """
-- d. Intent funnel
SELECT 
    COUNT(*) as total_students,
    SUM(CASE WHEN intent >= 4 THEN 1 ELSE 0 END) as high_interest,
    SUM(CASE WHEN intent >= 4 AND hours_available >= 10 THEN 1 ELSE 0 END) as interested_with_time,
    SUM(CASE WHEN intent >= 4 AND hours_available >= 10 AND willing_to_pay = 1 THEN 1 ELSE 0 END) as highly_qualified_leads
FROM respondents;
""")

write_file("sql/analysis/06_cooccurrence.sql", """
-- f. Pain-point co-occurrence (Self-Join)
SELECT 
    a.pain_point as problem_1,
    b.pain_point as problem_2,
    COUNT(*) as co_occurrences
FROM pain_points a
JOIN pain_points b 
    ON a.respondent_id = b.respondent_id 
    AND a.pain_point < b.pain_point
GROUP BY a.pain_point, b.pain_point
ORDER BY co_occurrences DESC
LIMIT 10;
""")


# ==========================================
# 4. DOCS AND DASHBOARD
# ==========================================
write_file("docs/00_brief.md", """
# Project Brief: Research Internship Program Viability

## Business Question
Which student problems are most prevalent and severe, and should we launch the Research Internship Program, for which segment first?

## Hypotheses
1. Lack of mentorship is the top pain point.
2. Pain severity is higher among Final-Year students.
3. Career goal strongly predicts intent to join.

## Metric Tree
- **North Star:** Verified Research Outputs Completed per cohort
- **Input:** Application Rate -> Activation Rate -> Weekly Engagement -> Completion Rate
""")

write_file("dashboard/app.py", """
import streamlit as st
import pandas as pd
import sqlite3

st.set_page_config(layout="wide")
st.title("SkillifyMe: Research Internship Analytics")

conn = sqlite3.connect('data/skillifyme.db')

st.header("1. Executive Summary")
funnel = pd.read_sql("SELECT * FROM respondents", conn)
st.metric("Total Valid Respondents", len(funnel))
st.metric("High Intent Segment", len(funnel[funnel['intent']>=4]))

st.header("2. Problem Prioritization")
priority_query = \"\"\"
WITH prev AS (
    SELECT pain_point, COUNT(DISTINCT respondent_id) * 1.0 / (SELECT COUNT(*) FROM respondents) as prev, AVG(pain_severity) as sev
    FROM pain_points GROUP BY pain_point
)
SELECT pain_point, ROUND(prev*100, 1) as prev_pct, ROUND(sev, 2) as severity, ROUND(prev*sev*100, 1) as score FROM prev ORDER BY score DESC
\"\"\"
st.dataframe(pd.read_sql(priority_query, conn))
""")

write_file("README.md", """
# SkillifyMe End-to-End Analytics Pipeline
Built for Media.net Senior Product Analyst Application.

## Setup
1. `cd python`
2. `python 01_clean.py`
3. `python 02_load.py`
4. `python 03_stats.py`
5. `python 04_sizing.py`
6. `cd ../dashboard && streamlit run app.py`
""")

print("Build script successfully created all files.")
