import os
import random

base_dir = r"d:\Professional Work\Business\Media_net\SkillifyMe_Analytics"
os.makedirs(base_dir, exist_ok=True)

def write_file(path, content):
    full_path = os.path.join(base_dir, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content.strip() + "\n")

# 1. GENERATE MOCK DATA WITHOUT PANDAS
os.makedirs(os.path.join(base_dir, 'data', 'raw'), exist_ok=True)
csv_lines = ["respondent_id,name,email,phone,year_of_study,domain,career_goal,college_tier,pain_severity,skill_research,intent,hours_available,willing_to_pay,pain_points"]
pain_opts = ['Lack of practical experience', 'No mentorship', 'Poor portfolio', 'No research exposure', 'No industry connections']

random.seed(42)
for i in range(1, 1001):
    r_id = f"R{str(i).zfill(4)}"
    name = f"Student_{i}"
    email = f"student{i}@test.com"
    phone = f"555-01{str(i).zfill(4)[-2:]}"
    year = random.choice(['1st', '2nd', '3rd', '4th', 'Graduated'])
    domain = random.choice(['Engineering', 'Science', 'Arts', 'Commerce'])
    goal = random.choice(['Software Engineer', 'Data Scientist', 'Researcher', 'Product Manager'])
    tier = random.choice(['Tier 1', 'Tier 2', 'Tier 3'])
    
    intent = max(1, min(5, int(random.gauss(3.5 if goal == 'Researcher' else 3.0, 1.0))))
    pain_sev = max(1, min(5, int(random.gauss(3.5, 1.0))))
    skill = max(1, min(5, int(random.gauss(2.5, 1.0))))
    hours = random.randint(0, 25)
    wtp = random.choice([1, 0]) if intent >= 4 else random.choice([0]*8 + [1]*2)
    
    selected_pains = ";".join(random.sample(pain_opts, random.randint(1, 3)))
    
    csv_lines.append(f"{r_id},{name},{email},{phone},{year},{domain},{goal},{tier},{pain_sev},{skill},{intent},{hours},{wtp},{selected_pains}")

with open(os.path.join(base_dir, 'data', 'raw', 'survey_export.csv'), 'w', encoding='utf-8') as f:
    f.write("\n".join(csv_lines))


# 2. PYTHON FILES
write_file("python/01_clean.py", """
import pandas as pd
import os

df = pd.read_csv('../data/raw/survey_export.csv', sep=',')
initial_count = len(df)

# Drop PII
df_clean = df.drop(columns=['name', 'email', 'phone'])

# Filter invalid
valid_mask = ~((df_clean['intent'] == 1) & (df_clean['willing_to_pay'] == 1))
df_clean = df_clean[valid_mask]

# Explode pain points (using semicolon since we mocked it that way to avoid csv escaping issues)
df_pain = df_clean[['respondent_id', 'pain_points', 'pain_severity']].copy()
df_pain['pain_point'] = df_pain['pain_points'].str.split(';')
df_pain = df_pain.explode('pain_point').drop(columns=['pain_points'])

os.makedirs('../data/cleaned', exist_ok=True)
df_clean.drop(columns=['pain_points']).to_csv('../data/cleaned/respondents.csv', index=False)
df_pain.to_csv('../data/cleaned/pain_points.csv', index=False)
print("Data cleaned and saved.")
""")

write_file("python/02_load.py", """
import sqlite3
import pandas as pd
import os

db_path = '../data/skillifyme.db'
if os.path.exists(db_path):
    os.remove(db_path)
conn = sqlite3.connect(db_path)

with open('../sql/01_schema.sql', 'r') as f:
    conn.executescript(f.read())

pd.read_csv('../data/cleaned/respondents.csv').to_sql('respondents', conn, if_exists='append', index=False)
pd.read_csv('../data/cleaned/pain_points.csv').to_sql('pain_points', conn, if_exists='append', index=False)
print("Database loaded.")
""")

write_file("python/03_stats.py", """
import pandas as pd
import statsmodels.api as sm
from statsmodels.stats.proportion import proportion_confint
import os

df = pd.read_csv('../data/cleaned/respondents.csv')
os.makedirs('../outputs', exist_ok=True)

high_intent = len(df[df['intent'] >= 4])
total = len(df)
ci_low, ci_high = proportion_confint(high_intent, total, method='wilson')

df['high_intent'] = (df['intent'] >= 4).astype(int)
X = pd.get_dummies(df[['year_of_study', 'career_goal']], drop_first=True)
X['hours_available'] = df['hours_available']
X = sm.add_constant(X)
model = sm.Logit(df['high_intent'], X).fit(disp=0)

with open('../outputs/stats_results.txt', 'w') as f:
    f.write(f"High Intent Rate: {high_intent/total:.1%} (95% CI: {ci_low:.1%} - {ci_high:.1%})\\n\\n")
    f.write(model.summary().as_text())
print("Stats calculated.")
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

os.makedirs('../outputs', exist_ok=True)
with open('../outputs/sizing_results.txt', 'w') as f:
    f.write(f"Base Case (Median) Completions: {np.median(expected_starts):.0f}\\n")
    f.write(f"Conservative (10th Pct): {np.percentile(expected_starts, 10):.0f}\\n")
    f.write(f"Optimistic (90th Pct): {np.percentile(expected_starts, 90):.0f}\\n")
print("Sizing complete.")
""")

# 3. SQL FILES
write_file("sql/01_schema.sql", """
CREATE TABLE respondents (
    respondent_id VARCHAR PRIMARY KEY, year_of_study VARCHAR, domain VARCHAR,
    career_goal VARCHAR, college_tier VARCHAR, pain_severity INT,
    skill_research INT, intent INT, hours_available INT, willing_to_pay INT
);
CREATE TABLE pain_points (
    respondent_id VARCHAR, pain_point VARCHAR, pain_severity INT
);
CREATE VIEW v_respondent_flat AS
SELECT r.*, p.pain_point, p.pain_severity as item_severity
FROM respondents r JOIN pain_points p ON r.respondent_id = p.respondent_id;
""")

write_file("sql/analysis/01_prevalence.sql", "SELECT pain_point, COUNT(DISTINCT respondent_id) as student_count, ROUND(AVG(pain_severity), 2) as avg_severity FROM pain_points GROUP BY pain_point ORDER BY student_count DESC;")
write_file("sql/analysis/02_priority.sql", "WITH prev AS (SELECT pain_point, COUNT(DISTINCT respondent_id) * 1.0 / (SELECT COUNT(*) FROM respondents) as prevalence, AVG(pain_severity) as severity FROM pain_points GROUP BY pain_point) SELECT pain_point, ROUND(prevalence*100, 2) as prevalence_pct, ROUND(severity, 2) as avg_severity, ROUND(prevalence*severity*100, 2) as priority_score, RANK() OVER(ORDER BY prevalence*severity DESC) as rank FROM prev;")
write_file("sql/analysis/03_segmentation.sql", "SELECT r.career_goal, p.pain_point, COUNT(r.respondent_id) as count, ROUND(COUNT(r.respondent_id) * 100.0 / SUM(COUNT(r.respondent_id)) OVER(PARTITION BY r.career_goal), 2) as pct_in_segment FROM respondents r JOIN pain_points p ON r.respondent_id = p.respondent_id GROUP BY r.career_goal, p.pain_point;")
write_file("sql/analysis/04_funnel.sql", "SELECT COUNT(*) as total, SUM(CASE WHEN intent >= 4 THEN 1 ELSE 0 END) as high_interest, SUM(CASE WHEN intent >= 4 AND hours_available >= 10 THEN 1 ELSE 0 END) as interested_with_time, SUM(CASE WHEN intent >= 4 AND hours_available >= 10 AND willing_to_pay = 1 THEN 1 ELSE 0 END) as hql FROM respondents;")
write_file("sql/analysis/05_skill_gap.sql", "SELECT career_goal, ROUND(AVG(skill_research), 2) as avg_research_skill FROM respondents GROUP BY career_goal;")
write_file("sql/analysis/06_cooccurrence.sql", "SELECT a.pain_point as prob1, b.pain_point as prob2, COUNT(*) as co_occurrences FROM pain_points a JOIN pain_points b ON a.respondent_id = b.respondent_id AND a.pain_point < b.pain_point GROUP BY prob1, prob2 ORDER BY co_occurrences DESC LIMIT 10;")
write_file("sql/analysis/07_respondent_segmentation.sql", "SELECT CASE WHEN intent >=4 AND pain_severity >=4 THEN 'High Need / High Intent' WHEN intent <4 AND pain_severity >=4 THEN 'High Need / Low Intent' WHEN intent >=4 AND pain_severity <4 THEN 'Low Need / High Intent' ELSE 'Low Need / Low Intent' END as quadrant, COUNT(*) as size FROM respondents GROUP BY 1;")
write_file("sql/analysis/08_launch_priority.sql", "SELECT career_goal, COUNT(*) as size, AVG(intent) as avg_intent, AVG(pain_severity) as avg_severity, ROUND(COUNT(*) * AVG(intent) * AVG(pain_severity), 2) as launch_score FROM respondents GROUP BY career_goal ORDER BY launch_score DESC;")

# 4. DOCS AND DASHBOARD
write_file("docs/00_brief.md", "# Project Brief\\n\\n## Business Question\\nShould we launch the Research Internship Program? Which segment first?\\n\\n## Hypotheses\\n1. Mentorship is the top pain point.\\n2. Severity is higher in final-year students.\\n3. Career goal predicts intent.")
write_file("docs/02_experiment_plan.md", "# Experiment Plan (A/B Test)\\n\\n**Hypothesis:** Messaging emphasizing 'Portfolio Building' yields a 15% higher application rate than 'Mentorship'.\\n- **Primary Metric:** Application Rate\\n- **Randomization:** User ID hash (modulo 2)\\n- **Sample Size:** 2,500 per arm (80% power, 5% alpha)")
write_file("docs/03_competitive_benchmark.md", "# Competitive Benchmark\\n\\n| Competitor | Mentorship | Price | Portfolio Value |\\n|---|---|---|---|\\n| Internshala | Low | Low | Low |\\n| Forage | None | Free | Medium |\\n| **SkillifyMe** | **High** | **Premium** | **High** |")

write_file("dashboard/app.py", """
import streamlit as st
import pandas as pd
import sqlite3

st.set_page_config(layout="wide")
st.title("SkillifyMe: Research Internship Analytics")

conn = sqlite3.connect('data/skillifyme.db')

st.header("Executive Summary")
funnel = pd.read_sql("SELECT * FROM respondents", conn)
st.metric("Total Valid Respondents", len(funnel))
st.metric("High Intent Segment", len(funnel[funnel['intent']>=4]))

st.header("Problem Prioritization")
priority_query = "WITH prev AS (SELECT pain_point, COUNT(DISTINCT respondent_id) * 1.0 / (SELECT COUNT(*) FROM respondents) as prev, AVG(pain_severity) as sev FROM pain_points GROUP BY pain_point) SELECT pain_point, ROUND(prev*100, 1) as prev_pct, ROUND(sev, 2) as severity, ROUND(prev*sev*100, 1) as score FROM prev ORDER BY score DESC"
st.dataframe(pd.read_sql(priority_query, conn))
""")

write_file("README.md", "# SkillifyMe End-to-End Analytics Pipeline\\nBuilt for Media.net.\\n\\n## Run\\n`python python/01_clean.py`\\n`python python/02_load.py`\\n`streamlit run dashboard/app.py`")

print("All files successfully laid out on disk.")
