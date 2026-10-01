SELECT career_goal, ROUND(AVG(skill_research), 2) as avg_research_skill FROM respondents GROUP BY career_goal;
