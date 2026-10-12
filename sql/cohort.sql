-- Synthetic target trial: index at study day 0. No future enrollment/survival rule.
-- Simple demonstration labels, NOT production ICD/NDC code lists.
WITH index_rx AS (
 SELECT person_id, day AS index_day,
        MAX(CASE WHEN drug='dapagliflozin' THEN 1 ELSE 0 END) AS a
 FROM fills WHERE day=0 AND drug IN ('dapagliflozin','sitagliptin')
 GROUP BY person_id,day HAVING COUNT(DISTINCT drug)=1
), eligible AS (
 SELECT i.person_id,i.index_day,i.a,e.end_day,
        CASE WHEN e.age>=75 THEN 1 ELSE 0 END AS older,
        CASE WHEN l.egfr<30 THEN 1 ELSE 0 END AS severe,
        CASE WHEN EXISTS(SELECT 1 FROM diagnoses d WHERE d.person_id=i.person_id
          AND d.code='HF' AND d.day BETWEEN i.index_day-365 AND i.index_day-1) THEN 1 ELSE 0 END AS hf
 FROM index_rx i JOIN enrollment e ON e.person_id=i.person_id
 JOIN labs l ON l.person_id=i.person_id AND l.day=(SELECT MAX(z.day) FROM labs z
   WHERE z.person_id=i.person_id AND z.day<i.index_day AND z.day>=i.index_day-90)
 WHERE e.age>=18 AND e.start_day<=i.index_day-365 AND e.end_day>=i.index_day
 AND l.egfr BETWEEN 25 AND 75 AND l.uacr BETWEEN 200 AND 5000
 AND EXISTS(SELECT 1 FROM labs old WHERE old.person_id=i.person_id
   AND old.day BETWEEN i.index_day-365 AND l.day-90 AND old.uacr>=200)
 AND (SELECT COUNT(DISTINCT day) FROM diagnoses d WHERE d.person_id=i.person_id AND d.code='T2D'
      AND d.day BETWEEN i.index_day-365 AND i.index_day-1)>=2
 AND NOT EXISTS(SELECT 1 FROM fills f WHERE f.person_id=i.person_id
   AND f.drug IN ('dapagliflozin','sitagliptin') AND f.day BETWEEN i.index_day-365 AND i.index_day-1)
 AND NOT EXISTS(SELECT 1 FROM events v WHERE v.person_id=i.person_id AND v.event IN ('KRT','transplant') AND v.day<i.index_day)
), observed AS (
 SELECT e.*,
   (SELECT MIN(v.day) FROM events v WHERE v.person_id=e.person_id AND v.event='KRT' AND v.day BETWEEN 0 AND MIN(e.end_day,364)) renal_day,
   (SELECT MIN(v.day) FROM events v WHERE v.person_id=e.person_id AND v.event='death' AND v.day BETWEEN 0 AND MIN(e.end_day,364)) death_day
 FROM eligible e
)
SELECT person_id,older,severe,hf,a,
 CASE WHEN renal_day IS NOT NULL AND (death_day IS NULL OR renal_day<death_day) THEN 1
      WHEN death_day IS NOT NULL THEN 2 WHEN end_day<364 THEN 3 ELSE 0 END status,
 CASE WHEN renal_day IS NOT NULL AND (death_day IS NULL OR renal_day<death_day) THEN CAST((renal_day+1)*12.0/365+0.5 AS INT)
      WHEN death_day IS NOT NULL THEN CAST((death_day+1)*12.0/365+0.5 AS INT)
      WHEN end_day<364 THEN CAST(end_day*12.0/365+0.5 AS INT)+1 ELSE 12 END month
FROM observed ORDER BY person_id;
