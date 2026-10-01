SELECT pain_point, COUNT(DISTINCT respondent_id) as student_count, ROUND(AVG(pain_severity), 2) as avg_severity FROM pain_points GROUP BY pain_point ORDER BY student_count DESC;
