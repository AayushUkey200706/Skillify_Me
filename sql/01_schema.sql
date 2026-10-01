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
