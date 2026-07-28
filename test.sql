-- -- ============================================
-- -- PostgreSQL Connection & Database Explorer
-- -- ============================================
 
-- -- 1. Test Connection - Show server version
-- SELECT version() AS "SERVER INFO";
 
-- -- 2. Show current database
-- SELECT current_database() AS "CURRENT DATABASE";
 
-- -- 3. Show current user
-- SELECT current_user AS "CURRENT USER";
 
-- -- 4. List all databases
-- SELECT datname FROM pg_database WHERE NOT datistemplate ORDER BY datname;
 
-- -- 5. List all schemas in current database
-- SELECT schema_name FROM information_schema.schemata ORDER BY schema_name;
 
-- -- 6. List all tables in public schema
-- SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;
 
-- -- ============================================
-- -- AGENT_SUBMISSION_INTAKE TABLE SCHEMA
-- -- ============================================
 
-- -- 7. View all columns in agent_submission_intake (VERTICAL FORMAT)
-- SELECT
--     ordinal_position AS "Position",
--     column_name AS "Column Name",
--     data_type AS "Data Type",
--     is_nullable AS "Nullable (YES/NO)",
--     column_default AS "Default Value"
-- FROM information_schema.columns
-- WHERE table_schema = 'public'
-- AND table_name = 'agent_submission_intake'
-- ORDER BY ordinal_position;
 
-- 8. View sample data from agent_submission_intake (first 10 rows)
-- SELECT * FROM agent_submission_intake LIMIT 10;


-- SELECT * FROM risk_assessment LIMIT 10;
-- SELECT * FROM agent_risk_assessment LIMIT 10;

-- SELECT * FROM agent_submission_intake LIMIT 10;

-- SELECT 
--   string_agg(document_summary, E'\n\n---\n\n') AS document_summary_text,
--   string_agg(submission_summary, E'\n\n---\n\n') AS submission_summary_text
-- FROM agent_submission_intake
-- LIMIT 10;
-- UPDATE agent_submission_intake
-- SET submission_summary = NULL,
--     document_summary = NULL;




-- SELECT * From brt01;

-- CREATE TABLE BRT01 (
--    id SERIAL PRIMARY KEY,
--    parameter VARCHAR(10) NOT NULL,
--    construction_class VARCHAR(100) NOT NULL,
--    iso_class VARCHAR(20),
--    points INTEGER,
--    fire_rate_factor NUMERIC(4,2),
--    uw_action BOOLEAN,
--    notes TEXT
-- );

-- SELECT * FROM BRT05B;

-- INSERT INTO BRT01
-- (parameter, construction_class, iso_class, points, fire_rate_factor, uw_action, notes)
-- VALUES
-- ('A1','Frame (Wood)','Class 1',150,2.50,'False','Highest fire severity, no flat roofs >3 stories'),
-- ('A1','Joisted Masonry','Class 2',120,2.00,'False','Masonry walls / wood floors — common in older stock'),
-- ('A1','Non-Combustible (Light Steel)','Class 3',90,1.50,'False','Light steel frame; gypsum board finish preferred'),
-- ('A1','Masonry Non-Combustible','Class 4',50,1.10,'False','Concrete block / brick walls; non-combustible floors'),
-- ('A1','Modified Fire Resistive','Class 5',35,1.00,'False','Partial fire-resistive elements; ≥1 hr rating'),
-- ('A1','Fire Resistive (Concrete / Steel)','Class 6',10,0.70,'False','Full 2-hr fire rating; sprinklers credited separately'),
-- ('A1','Superior Fire Resistive','Class 6+',5,0.60,'False','LEED-certified or post-2015 IBC high-rise'),
-- ('A1','Modular / Prefab','Class 2',130,2.10,'False','Joint/seam vulnerability; limited market appetite'),
-- ('A1','Mixed Construction','Class 2–4',100,1.75,'True','Score each portion separately; blend by sq footage %'),
-- ('A1','Historic / Unreinforced Masonry','Class 1',145,2.40,'True','URM = highest seismic and fire vulnerability');





-- CREATE TABLE BRT02 (
--    id SERIAL PRIMARY KEY,
--    occupancy_type VARCHAR(100) NOT NULL,
--    base_points INTEGER,
--    hazard_class VARCHAR(30)
-- );

-- INSERT INTO BRT02
-- (occupancy_type, base_points, hazard_class)
-- VALUES
-- ('Class A Office',20,'Low'),
-- ('Medical Office / Clinic',55,'Medium'),
-- ('Retail – General Merchandise',60,'Medium'),
-- ('Restaurant / Food Service',120,'High'),
-- ('Light Industrial / Warehouse',80,'Medium-High'),
-- ('Heavy Manufacturing',160,'Very High'),
-- ('Automotive Services',130,'High'),
-- ('Hospitality / Hotel',75,'Medium'),
-- ('Self-Storage Facility',65,'Medium'),
-- ('Cannabis Dispensary',180,'Very High'),
-- ('Data Center / Co-Location',90,'Medium-High'),
-- ('Mixed Use (Office + Retail)',65,'Medium'),
-- ('Place of Worship',40,'Low-Medium'),
-- ('Educational Facility',50,'Medium');


-- ALTER TABLE BRT02
-- ADD COLUMN parameter VARCHAR(5);
-- UPDATE BRT02
-- SET parameter = 'B';


-- SELECT * FROM BRT02;



-- CREATE TABLE BRT03 (
--    id SERIAL PRIMARY KEY,
--    peril_parameter VARCHAR(100) NOT NULL,
--    condition_range VARCHAR(100) NOT NULL,
--    points_added INTEGER
-- );



-- INSERT INTO BRT03
-- (peril_parameter, condition_range, points_added)
-- VALUES
-- ('FEMA Flood Zone','Zone X (minimal)',0),
-- ('FEMA Flood Zone','Zone AH / AO',40),
-- ('FEMA Flood Zone','Zone AE / A (base)',80),
-- ('FEMA Flood Zone','Zone VE / V (coastal)',150),
-- ('Wildfire Risk Score (0–100)','0–25 (Low)',0),
-- ('Wildfire Risk Score (0–100)','26–50 (Moderate)',35),
-- ('Wildfire Risk Score (0–100)','51–75 (High)',80),
-- ('Wildfire Risk Score (0–100)','76–100 (Very High)',150),
-- ('Wind Zone / Hurricane','Zone 1–2 (Inland)',10),
-- ('Wind Zone / Hurricane','Zone 3 (Gulf/Atlantic)',60),
-- ('Wind Zone / Hurricane','Zone 4–5 (High-velocity)',120),
-- ('Earthquake PML (% TIV)','< 5%',10),
-- ('Earthquake PML (% TIV)','5–15%',50),
-- ('Earthquake PML (% TIV)','15–30%',100),
-- ('Earthquake PML (% TIV)','> 30%',160),
-- ('ISO PPC Rating','Class 1–3 (Excellent)',-20),
-- ('ISO PPC Rating','Class 4–6 (Good)',0),
-- ('ISO PPC Rating','Class 7–8 (Fair)',40),
-- ('ISO PPC Rating','Class 9–10 (Poor/Unprotected)',120),
-- ('Hail Score (0–10)','0–4 (Low)',0),
-- ('Hail Score (0–10)','5–7 (Moderate)',30),
-- ('Hail Score (0–10)','8–10 (High)',70);



-- DROP TABLE BRT03;
-- ADD COLUMN parameter VARCHAR(5);




-- CREATE TABLE BRT03 (

--     id SERIAL PRIMARY KEY,

--     parameter VARCHAR(3) NOT NULL,

--     peril VARCHAR(100) NOT NULL,

--     condition VARCHAR(100),

--     points INTEGER

-- );

-- INSERT INTO BRT03

-- (parameter, peril, condition, points)

-- VALUES

-- ('C2','FEMA Flood Zone','Zone X (minimal)',0),

-- ('C2','FEMA Flood Zone','Zone AH / AO',40),

-- ('C2','FEMA Flood Zone','Zone AE / A (base)',80),

-- ('C2','FEMA Flood Zone','Zone VE / V (coastal)',150),

-- ('C4','Wildfire Risk Score (0–100)','0–25 (Low)',0),

-- ('C4','Wildfire Risk Score (0–100)','26–50 (Moderate)',35),

-- ('C4','Wildfire Risk Score (0–100)','51–75 (High)',80),

-- ('C4','Wildfire Risk Score (0–100)','76–100 (Very High)',150),

-- ('C5','Wind Zone / Hurricane','Zone 1–2(Inland)',10),

-- ('C5','Wind Zone / Hurricane','Zone 3(Gulf/Atlantic)',60),

-- ('C5','Wind Zone / Hurricane','Zone 4–5(High-velocity)',120),

-- ('C6','Earthquake PML (% TIV)','<5%',10),

-- ('C6','Earthquake PML (% TIV)','5–15%',50),

-- ('C6','Earthquake PML (% TIV)','15–30%',100),

-- ('C6','Earthquake PML (% TIV)','>30%',160),

-- ('C10','ISO PPC Rating','Class 1–3(Excellent)',-20),

-- ('C10','ISO PPC Rating','Class 4–6(Good)',0),

-- ('C10','ISO PPC Rating','Class 7–8(Fair)',40),

-- ('C10','ISO PPC Rating','Class 9–10(Poor/Unprotected)',120),

-- ('C7','Hail Score (0–10)','0–4(Low)',0),

-- ('C7','Hail Score (0–10)','5–7(Moderate)',30),

-- ('C7','Hail Score (0–10)','8–10(High)',70);
 



-- SELECT * FROM BRT04;


-- CREATE TABLE BRT04 (

--     id SERIAL PRIMARY KEY,

--     system_name VARCHAR(50) NOT NULL,

--     age_range int4range,

--     points INTEGER,

--     required_action VARCHAR(150),

--     coverage_condition VARCHAR(150),

--     inspection_needed VARCHAR(20)

-- );

-- DROP TABLE BRT04;
 
-- INSERT INTO BRT04

-- (system_name, age_range, points, required_action, coverage_condition, inspection_needed)

-- VALUES

-- ('Overall Building Age',[0–10],0,'None','Full RCV available','No'),

-- ('Overall Building Age',[11–25]',15,'Document renovation history','Full RCV available','No'),

-- ('Overall Building Age','[26–40] ',35,'Verify major systems updated','RCV with conditions','Recommended'),

-- ('Overall Building Age','41–60 yrs',65,'Inspection required','ACV option; RCV with eng. report','Required'),

-- ('Overall Building Age','> 60 yrs',100,'Full engineering inspection','ACV unless full renovation','Mandatory'),

-- ('Electrical System','0–15 yrs',0,'None','Full coverage','No'),

-- ('Electrical System','16–25 yrs',20,'Document panel type/capacity','Full coverage','No'),

-- ('Electrical System','26–35 yrs',50,'Verify no knob-and-tube / aluminum wiring','Exclusion if aluminum wiring found','Recommended'),

-- ('Electrical System','> 35 yrs or Unknown',90,'Electrical inspection mandatory','May exclude electrical fire','Mandatory'),

-- ('Plumbing System','0–15 yrs',0,'None','Full coverage','No'),

-- ('Plumbing System','16–25 yrs',15,'Note pipe material','Full coverage','No'),

-- ('Plumbing System','26–40 yrs (copper/PVC)',30,'Note material; verify no lead','Full coverage if copper/PVC','Recommended'),

-- ('Plumbing System','> 40 yrs or galvanized',80,'Replacement timeline required','Exclude water damage if galvanized not replaced','Mandatory'),

-- ('HVAC System','0–10 yrs',0,'None','Full coverage','No'),

-- ('HVAC System','11–20 yrs',20,'Document service history','Full coverage','No'),

-- ('HVAC System','> 20 yrs',45,'Inspection + service records','BI coverage conditions apply','Required'),

-- ('Roof (Flat / TPO / EPDM)','0–7 yrs',0,'None','Full coverage','No'),

-- ('Roof (Flat / TPO / EPDM)','8–15 yrs',25,'Inspection recommended','Full coverage w/ inspection','Recommended'),

-- ('Roof (Flat / TPO / EPDM)','16–20 yrs',60,'Inspection required','ACV on roof; replacement plan','Required'),

-- ('Roof (Flat / TPO / EPDM)','> 20 yrs',100,'Immediate inspection + repair plan','ACV only on roof or exclude','Mandatory');
 

-- SELECT * FROM BRT04;





-- INSERT INTO BRT04
-- (system_name, age_range, points, required_action, coverage_condition, inspection_needed)
-- VALUES
-- ('Overall Building Age','[0,11)',0,'None','Full RCV available','No'),
-- ('Overall Building Age','[11,26)',15,'Document renovation history','Full RCV available','No'),
-- ('Overall Building Age','[26,41)',35,'Verify major systems updated','RCV with conditions','Recommended'),
-- ('Overall Building Age','[41,61)',65,'Inspection required','ACV option; RCV with eng. report','Required'),
-- ('Overall Building Age','[60,)',100,'Full engineering inspection','ACV unless full renovation','Mandatory'),
-- ('Electrical System','[0,16)',0,'None','Full coverage','No'),
-- ('Electrical System','[16,26)',20,'Document panel type/capacity','Full coverage','Recommended'),
-- ('Electrical System','[26,36)',50,'Verify no knob-and-tube / aluminum wiring','Exclusion if aluminum wiring found','Required'),
-- ('Electrical System','[36,)',90,'Electrical inspection mandatory','May exclude electrical fire','Mandatory'),
-- ('Plumbing System','[0,16)',0,'None','Full coverage','No'),
-- ('Plumbing System','[16,26)',15,'Note pipe material','Full coverage','No'),
-- ('Plumbing System','[26,41)',30,'Note material; verify no lead','Full coverage if copper/PVC','Recommended'),
-- ('Plumbing System','[41,)',80,'Replacement timeline required','Exclude water damage if galvanized not replaced','Mandatory'),
-- ('HVAC System','[0,11)',0,'None','Full coverage','No'),
-- ('HVAC System','[11,21)',20,'Document service history','Full coverage','No'),
-- ('HVAC System','[21,)',45,'Inspection + service records','BI coverage conditions apply','Required'),
-- ('Roof (Flat / TPO / EPDM)','[0,8)',0,'None','Full coverage','No'),
-- ('Roof (Flat / TPO / EPDM)','[8,16)',25,'Inspection recommended','Full coverage w/ inspection','Recommended'),
-- ('Roof (Flat / TPO / EPDM)','[16,21)',60,'Inspection required','ACV on roof; replacement plan','Required'),
-- ('Roof (Flat / TPO / EPDM)','[21,)',100,'Immediate inspection + repair plan','ACV only on roof or exclude','Mandatory');





-- DROP TABLE BRT04;

-- CREATE TABLE BRT04 (
--    id SERIAL PRIMARY KEY,
--    parameter VARCHAR(3) NOT NULL,
--    system VARCHAR(50) NOT NULL,
--    age_range int4range NOT NULL,
--    points INTEGER,
--    required_action TEXT,
--    coverage_condition TEXT,
--    inspection_needed VARCHAR(20)
-- );

-- INSERT INTO BRT04
-- (parameter, system, age_range, points, required_action, coverage_condition, inspection_needed)
-- VALUES
-- ('A2','Overall Building Age','[0,11)',0,'None','Full RCV available','No'),
-- ('A2','Overall Building Age','[11,26)',15,'Document renovation history','Full RCV available','No'),
-- ('A2','Overall Building Age','[26,41)',35,'Verify major systems updated','RCV with conditions','Recommended'),
-- ('A2','Overall Building Age','[41,61)',65,'Inspection required','ACV option; RCV with eng. report','Required'),
-- ('A2','Overall Building Age','[60,)',100,'Full engineering inspection','ACV unless full renovation','Mandatory'),
-- ('A8','Electrical System','[0,16)',0,'None','Full coverage','No'),
-- ('A8','Electrical System','[16,26)',20,'Document panel type/capacity','Full coverage','Recommended'),
-- ('A8','Electrical System','[26,36)',50,'Verify no knob-and-tube / aluminum wiring','Exclusion if aluminum wiring found','Required'),
-- ('A8','Electrical System','[36,)',90,'Electrical inspection mandatory','May exclude electrical fire','Mandatory'),
-- ('A9','Plumbing System','[0,16)',0,'None','Full coverage','No'),
-- ('A9','Plumbing System','[16,26)',15,'Note pipe material','Full coverage','No'),
-- ('A9','Plumbing System','[26,41)',30,'Note material; verify no lead','Full coverage if copper/PVC','Recommended'),
-- ('A9','Plumbing System','[41,)',80,'Replacement timeline required','Exclude water damage if galvanized not replaced','Mandatory'),
-- ('A7','HVAC System','[0,11)',0,'None','Full coverage','No'),
-- ('A7','HVAC System','[11,21)',20,'Document service history','Full coverage','No'),
-- ('A7','HVAC System','[21,)',45,'Inspection + service records','BI coverage conditions apply','Required'),
-- ('A6','Roof (Flat / TPO / EPDM)','[0,8)',0,'None','Full coverage','No'),
-- ('A6','Roof (Flat / TPO / EPDM)','[8,16)',25,'Inspection recommended','Full coverage w/ inspection','Recommended'),
-- ('A6','Roof (Flat / TPO / EPDM)','[16,21)',60,'Inspection required','ACV on roof; replacement plan','Required'),
-- ('A6','Roof (Flat / TPO / EPDM)','[21,)',100,'Immediate inspection + repair plan','ACV only on roof or exclude','Mandatory');



-- SELECT * FROM BRT04;


-- CREATE TABLE BRT05 (
--    id SERIAL PRIMARY KEY,
--    metric VARCHAR(50) NOT NULL,
--    condition_description VARCHAR(100) NOT NULL,
--    points INTEGER,
--    uw_action VARCHAR(100),
--    documentation_required VARCHAR(150)
-- );


-- INSERT INTO BRT05
-- (metric, condition_description, points, uw_action, documentation_required)
-- VALUES
-- ('5-Yr Loss Count','0 losses (loss-free)',0,'Auto-accept credit','Signed loss-free affidavit'),
-- ('5-Yr Loss Count','1 loss',15,'Accept','Loss run + description'),
-- ('5-Yr Loss Count','2 losses',40,'Accept with review','Loss runs + cause analysis'),
-- ('5-Yr Loss Count','3 losses',80,'Senior UW review','Full loss runs + risk improvement plan'),
-- ('5-Yr Loss Count','4 losses',130,'Mandatory referral','Full loss runs + loss control survey'),
-- ('5-Yr Loss Count','5+ losses',200,'Decline or E&S only','Full documentation; likely decline standard'),
-- ('5-Yr Incurred ($)','< $25,000',5,'Accept','None'),
-- ('5-Yr Incurred ($)','$25,000–$100,000',25,'Accept','Loss run summary'),
-- ('5-Yr Incurred ($)','$100,001–$500,000',70,'Senior UW review','Full loss runs + cause analysis'),
-- ('5-Yr Incurred ($)','$500,001–$1,000,000',130,'Mandatory referral','Engineering inspection required'),
-- ('5-Yr Incurred ($)','> $1,000,000',200,'Decline standard','E&S referral; loss control mandatory'),
-- ('Single Catastrophic Loss','CAT event (hurricane/flood/quake)',40,'Document CAT designation','FEMA declaration or CAT code'),
-- ('Single Catastrophic Loss','Non-CAT >$250K single loss',80,'Root cause analysis required','Detailed loss report + remediation'),
-- ('Prior Carrier Departure','Voluntary / market exit',0,'Standard processing','Prior policy copy'),
-- ('Prior Carrier Departure','Non-renewal (underwriting)',50,'Reason letter required','Non-renewal notice + explanation'),
-- ('Prior Carrier Departure','Cancellation (non-payment)',70,'Financial review required','Payment history; financials'),
-- ('Prior Carrier Departure','Cancellation (misrepresentation)',200,'AUTO-DECLINE','Hard stop — no exceptions');
 
 

-- SELECT * FROM BRT06;




-- DROP TABLE BRT05;


-- CREATE TABLE BRT05 (
--    id SERIAL PRIMARY KEY,
--    parameter VARCHAR(3) NOT NULL,
--    metric VARCHAR(80) NOT NULL,
--    condition_description VARCHAR(120),
--    points INTEGER,
--    uw_action TEXT,
--    documentation_required TEXT
-- );

-- INSERT INTO BRT05
-- (parameter, metric, condition_description, points, uw_action, documentation_required)
-- VALUES
-- ('D2','5-Yr Loss Count','0 losses (loss-free)',0,'Auto-accept credit','Signed loss-free affidavit'),
-- ('D2','5-Yr Loss Count','1 loss',15,'Accept','Loss run + description'),
-- ('D2','5-Yr Loss Count','2 losses',40,'Accept with review','Loss runs + cause analysis'),
-- ('D2','5-Yr Loss Count','3 losses',80,'Senior UW review','Full loss runs + risk improvement plan'),
-- ('D2','5-Yr Loss Count','4 losses',130,'Mandatory referral','Full loss runs + loss control survey'),
-- ('D2','5-Yr Loss Count','5+ losses',200,'Decline or E&S only',
-- 'Full documentation; likely decline standard'),
-- ('D3','5-Yr Incurred ($)','< $25,000',5,'Accept','None'),
-- ('D3','5-Yr Incurred ($)','$25,000–$100,000',25,'Accept','Loss run summary'),
-- ('D3','5-Yr Incurred ($)','$100,001–$500,000',70,
-- 'Senior UW review',
-- 'Full loss runs + cause analysis'),
-- ('D3','5-Yr Incurred ($)','$500,001–$1,000,000',
-- 130,'Mandatory referral',
-- 'Engineering inspection required'),
-- ('D3','5-Yr Incurred ($)','> $1,000,000',
-- 200,'Decline standard',
-- 'E&S referral; loss control mandatory'),
-- ('D1','Prior Carrier Departure',
-- 'Voluntary / market exit',
-- 0,'Standard processing','Prior policy copy'),
-- ('D1','Prior Carrier Departure',
-- 'Non-renewal (underwriting)',
-- 50,'Reason letter required',
-- 'Non-renewal notice + explanation'),
-- ('D1','Prior Carrier Departure',
-- 'Cancellation (non-payment)',
-- 70,'Financial review required',
-- 'Payment history; financials'),
-- ('D1','Prior Carrier Departure',
-- 'Cancellation (misrepresentation)',
-- 200,'AUTO-DECLINE',
-- 'Hard stop — no exceptions');






















-- CREATE TABLE BRT06 (
--    id SERIAL PRIMARY KEY,
--    system_name VARCHAR(50) NOT NULL,
--    condition_description VARCHAR(120) NOT NULL,
--    points INTEGER,
--    required_for VARCHAR(150),
--    inspection_interval VARCHAR(30)
-- );


-- INSERT INTO BRT06
-- (system_name, condition_description, points, required_for, inspection_interval)
-- VALUES
-- ('Sprinkler System','NFPA 13 Wet Pipe – 100% coverage',-50,'Preferred rate; BI credit','Annual'),
-- ('Sprinkler System','NFPA 13R / 13D (residential) – 100%',-30,'Standard credit','Annual'),
-- ('Sprinkler System','Partial (75–99% coverage)',20,'Explanation required','Semi-annual'),
-- ('Sprinkler System','Partial (< 75% coverage)',60,'Engineering plan for full coverage','Quarterly'),
-- ('Sprinkler System','None — required occupancy',130,'Mandatory for restaurants, warehouses >20k sqft','N/A'),
-- ('Sprinkler System','None — not required',30,'Fire alarm upgrade required','N/A'),
-- ('Fire Alarm','UL-Listed Central Station Monitored',-20,'Preferred rate','6 months'),
-- ('Fire Alarm','Local Alarm + Smoke Detectors',20,'Standard terms','Annual'),
-- ('Fire Alarm','Local Alarm Only (no smoke detection)',50,'Smoke detector installation required','Annual'),
-- ('Fire Alarm','None',100,'Mandatory — install or decline','N/A'),
-- ('Security System','Central-monitored + video + guard service',-15,'Preferred crime rate','Monthly test'),
-- ('Security System','Central-monitored burglar alarm',0,'Standard crime rate','Annual'),
-- ('Security System','Local alarm only',25,'Standard terms','Annual'),
-- ('Security System','None',60,'Installation required for limits > $500K','N/A'),
-- ('Last Fire Inspection','< 12 months ago',0,'Compliant','Annual required'),
-- ('Last Fire Inspection','12–24 months ago',20,'Schedule inspection at renewal','Overdue'),
-- ('Last Fire Inspection','> 24 months ago',70,'Inspection within 30 days of bind','Mandatory before bind'),
-- ('Backup Power','Generator — N+1 redundancy',-10,'BI credit; data center preferred','Annual'),
-- ('Backup Power','Generator — single unit',0,'Standard','Annual'),
-- ('Backup Power','UPS only (no generator)',15,'Note for BI assessment','N/A'),
-- ('Backup Power','None — critical occupancy',40,'Medical / data center: referral required','N/A');



-- SELECT * FROM BRT07;



-- DROP TABLE BRT06;

-- CREATE TABLE BRT06 (

--     id SERIAL PRIMARY KEY,

--     parameter VARCHAR(3) NOT NULL,

--     system VARCHAR(60) NOT NULL,

--     condition_description VARCHAR(150),

--     points INTEGER,

--     required_for TEXT,

--     inspection_interval VARCHAR(40)

-- );


-- INSERT INTO BRT06

-- (parameter, system, condition_description, points, required_for, inspection_interval)

-- VALUES

-- ('E1','Sprinkler System','NFPA 13 Wet Pipe – 100% coverage',-50,

-- 'Preferred rate; BI credit','Annual'),

-- ('E1','Sprinkler System','NFPA 13R / 13D (residential) – 100%',-30,

-- 'Standard credit','Annual'),

-- ('E1','Sprinkler System','Partial (75–99% coverage)',20,

-- 'Explanation required','Semi-annual'),

-- ('E1','Sprinkler System','Partial (<75% coverage)',60,

-- 'Engineering plan for full coverage','Quarterly'),

-- ('E1','Sprinkler System','None — required occupancy',130,

-- 'Mandatory for restaurants, warehouses >20k sqft',

-- 'N/A — require install timeline'),

-- ('E1','Sprinkler System','None — not required',30,

-- 'Fire alarm upgrade required','N/A'),

-- ('E3','Fire Alarm','UL-Listed Central Station Monitored',-20,

-- 'Preferred rate','6 months'),

-- ('E3','Fire Alarm','Local Alarm + Smoke Detectors',20,

-- 'Standard terms','Annual'),

-- ('E3','Fire Alarm','Local Alarm Only (no smoke detection)',50,

-- 'Smoke detector installation required','Annual'),

-- ('E3','Fire Alarm','None',100,

-- 'Mandatory — install or decline','N/A'),

-- ('E5','Security System','Central-monitored + video + guard service',-15,

-- 'Preferred crime rate','Monthly test'),

-- ('E5','Security System','Central-monitored burglar alarm',0,

-- 'Standard crime rate','Annual'),

-- ('E5','Security System','Local alarm only',25,

-- 'Standard terms','Annual'),

-- ('E5','Security System','None',60,

-- 'Installation required for limits > $500K','N/A'),

-- ('E6','Last Fire Inspection','< 12 months ago',0,

-- 'Compliant','Annual required'),

-- ('E6','Last Fire Inspection','12–24 months ago',20,

-- 'Schedule inspection at renewal','Overdue'),

-- ('E6','Last Fire Inspection','> 24 months ago',70,

-- 'Inspection within 30 days of bind',

-- 'Mandatory before bind'),

-- ('E8','Backup Power','Generator — N+1 redundancy',-10,

-- 'BI credit; data center preferred','Annual'),

-- ('E8','Backup Power','Generator — single unit',0,

-- 'Standard','Annual'),

-- ('E8','Backup Power','UPS only (no generator)',15,

-- 'Note for BI assessment','N/A'),

-- ('E8','Backup Power','None — critical occupancy',40,

-- 'Medical / data center: referral required','N/A');
 

-- CREATE TABLE BRT07 (
--    id SERIAL PRIMARY KEY,
--    parameter VARCHAR(60) NOT NULL,
--    condition int4range NOT NULL,
--    points INTEGER,
--    policy_action TEXT,
--    coverage_impact TEXT,
--    uw_note TEXT
-- );



-- DROP TABLE BRT07;


-- INSERT INTO BRT07
-- (parameter, condition, points, policy_action, coverage_impact, uw_note)
-- VALUES
-- ('Vacancy Rate','[0,6)',0,'None','Full coverage','Preferred'),
-- ('Vacancy Rate','[6,16)',15,'Notify insurer of changes','Full coverage','Monitor quarterly'),
-- ('Vacancy Rate','[16,31)',50,'Vacancy notification endorsement','Potential vacancy exclusions','Increased inspection frequency'),
-- ('Vacancy Rate','[31,51)',100,'Vacancy permit required','Limited fire coverage','Senior UW approval'),
-- ('Vacancy Rate','[51,)',180,'Vacancy permit or decline','Severely restricted coverage','Hard referral'),
-- ('Insurance-to-Value (ITV)','[100,)',0,'None','Full replacement cost','Note for renewal'),
-- ('Insurance-to-Value (ITV)','[90,100)',0,'None','Full replacement cost','Preferred range'),
-- ('Insurance-to-Value (ITV)','[80,90)',20,'Recommend appraisal','RCV with coinsurance note','Inflation guard'),
-- ('Insurance-to-Value (ITV)','[75,80)',60,'Appraisal required','Coinsurance penalty','Condition to bind'),
-- ('Insurance-to-Value (ITV)','[0,75)',120,'Appraisal mandatory','ACV only','Hard stop'),
-- ('BI Period Adequacy','[18,)',0,'None','Adequate BI coverage','Standard'),
-- ('BI Period Adequacy','[12,18)',20,'Recommend extended period','Potential underinsurance','Advisory'),
-- ('BI Period Adequacy','[0,12)',50,'BI adequacy letter','Extended endorsement','Signed acknowledgment'),
-- ('Annual Revenue (BI Limit Check)','[100,)',0,'None','Adequate','Standard'),
-- ('Annual Revenue (BI Limit Check)','[75,100)',20,'Advisory','Moderate risk','Discuss with insured'),
-- ('Annual Revenue (BI Limit Check)','[0,75)',50,'Letter required','Significant risk','Signed acknowledgment'),
-- ('Years in Business','[10,)',-10,'Premium credit','Seasoned operator credit','Document continuity'),
-- ('Years in Business','[5,10)',0,'None','Standard','Standard'),
-- ('Years in Business','[2,5)',25,'Financial statements required','Standard with conditions','3 yrs financials'),
-- ('Years in Business','[0,2)',60,'Full financial review','Possible D&O interaction','Referral');

-- SELECT * from BRT02;




-- INSERT INTO BRT07
-- (parameter_name, condition_description, points, policy_action, coverage_impact, uw_note)
-- VALUES
-- ('Vacancy Rate','0–5% (Fully occupied)',0,'None','Full coverage','Preferred'),
-- ('Vacancy Rate','6–15% (Minor vacancy)',15,'Notify insurer of changes','Full coverage','Monitor quarterly'),
-- ('Vacancy Rate','16–30% (Moderate vacancy)',50,'Vacancy notification endorsement','Potential vacancy exclusions at 60 days','Increased inspection frequency'),
-- ('Vacancy Rate','31–50% (High vacancy)',100,'Vacancy permit required','Vandalism/malicious mischief excluded; limited fire','Senior UW approval'),
-- ('Vacancy Rate','> 50% (Substantially vacant)',180,'Vacancy permit or decline','Severely restricted coverage','Hard referral; likely decline or non-standard terms'),
-- ('Insurance-to-Value (ITV)','> 100% (Slight over-insured)',0,'None','Full replacement cost','Note for renewal right-sizing'),
-- ('Insurance-to-Value (ITV)','90–100%',0,'None','Full replacement cost','Preferred range'),
-- ('Insurance-to-Value (ITV)','80–89%',20,'Recommend appraisal','RCV with coinsurance note','Flag for inflation guard'),
-- ('Insurance-to-Value (ITV)','75–79%',60,'Appraisal required','Coinsurance penalty clause activated','Condition to bind'),
-- ('Insurance-to-Value (ITV)','< 75%',120,'Appraisal mandatory; auto-condition','ACV only or coinsurance penalty','Hard stop — cannot bind RCV without appraisal'),
-- ('BI Period Adequacy','≥ 18 months',0,'None','Adequate BI coverage','Standard'),
-- ('BI Period Adequacy','12–17 months',20,'Recommend extended period','Potential underinsurance on long rebuilds','Advisory note to insured'),
-- ('BI Period Adequacy','< 12 months',50,'BI adequacy letter required','Sublimit or extended period endorsement','Signed acknowledgment required'),
-- ('Annual Revenue (BI Limit Check)','BI limit ≥ 100% of annual revenue',0,'None','Adequate','Standard'),
-- ('Annual Revenue (BI Limit Check)','BI limit 75–99% of annual revenue',20,'Advisory','Moderate underinsurance risk','Discuss with insured'),
-- ('Annual Revenue (BI Limit Check)','BI limit < 75% of annual revenue',50,'Letter required','Significant underinsurance risk','Signed acknowledgment required'),
-- ('Years in Business','> 10 years',-10,'-5% premium credit','Seasoned operator credit','Document ownership continuity'),
-- ('Years in Business','5–10 years',0,'None','Standard','Standard'),
-- ('Years in Business','2–4 years',25,'Financial statements required','Standard with conditions','3 yrs financials'),
-- ('Years in Business','< 2 years (startup)',60,'Full financial review','Possible D&O interaction','Referral; senior approval');



-- SELECT * FROM BRT07





-- CREATE TABLE BRT07 (
--    id SERIAL PRIMARY KEY,
--    parameter VARCHAR(3) NOT NULL,
--    parameter_type VARCHAR(80) NOT NULL,
--    condition int4range NOT NULL,
--    points INTEGER,
--    policy_action TEXT,
--    coverage_impact TEXT,
--    uw_note TEXT
-- );

-- INSERT INTO BRT07
-- (parameter, parameter_type, condition, points, policy_action, coverage_impact, uw_note)
-- VALUES
-- ('B5','Vacancy Rate','[0,6)',0,'None','Full coverage','Preferred'),
-- ('B5','Vacancy Rate','[6,16)',15,
-- 'Notify insurer of changes','Full coverage','Monitor quarterly'),
-- ('B5','Vacancy Rate','[16,31)',50,
-- 'Vacancy notification endorsement',
-- 'Potential vacancy exclusions at 60 days',
-- 'Increased inspection frequency'),
-- ('B5','Vacancy Rate','[31,51)',100,
-- 'Vacancy permit required',
-- 'Vandalism/malicious mischief excluded',
-- 'Senior UW approval'),
-- ('B5','Vacancy Rate','[51,)',180,
-- 'Vacancy permit or decline',
-- 'Severely restricted coverage',
-- 'Hard referral likely decline or non-standard terms'),
-- ('F7','Insurance-to-Value (ITV)','[100,)',0,
-- 'None','Full replacement cost','Note for renewal right-sizing'),
-- ('F7','Insurance-to-Value (ITV)','[90,100)',0,
-- 'None','Full replacement cost','Preferred range'),
-- ('F7','Insurance-to-Value (ITV)','[80,90)',20,
-- 'Recommend appraisal',
-- 'RCV with coinsurance note',
-- 'Flag for Inflation guard'),
-- ('F7','Insurance-to-Value (ITV)','[75,80)',60,
-- 'Appraisal required',
-- 'Coinsurance penalty clause activated',
-- 'Condition to bind'),
-- ('F7','Insurance-to-Value (ITV)','[0,75)',120,
-- 'Appraisal mandatory',
-- 'ACV only or coinsurance penalty',
-- 'Hard stop -- cannot bind RCV without appraisal'),
-- ('D6','BI Period Adequacy','[18,)',0,
-- 'None','Adequate BI coverage','Standard'),
-- ('D6','BI Period Adequacy','[12,18)',20,
-- 'Recommmend extended period',
-- 'Potential underinsurance on long rebuilds',
-- 'Advisory not to insured'),
-- ('D6','BI Period Adequacy','[0,12)',50,
-- 'BI adequacy letter required',
-- 'Sublimit or extended endorsement',
-- 'Signed acknowledgment required'),
-- ('D5','Annual Revenue (BI Limit Check)','[100,)',0,
-- 'None','Adequate','Standard'),
-- ('D5','Annual Revenue (BI Limit Check)','[75,100)',20,
-- 'Advisory','Moderate underinsurance risk',
-- 'Discuss with insured'),
-- ('D5','Annual Revenue (BI Limit Check)','[0,75)',50,
-- 'Letter required','Significant underinsurance risk',
-- 'Signed acknowledgment required'),
-- ('D8','Years in Business','[10,)',-10,
-- '-5% premium credit',
-- 'Seasoned operator credit',
-- 'Document ownership continuity'),
-- ('D8','Years in Business','[5,10)',0,
-- 'None','Standard','Standard'),
-- ('D8','Years in Business','[2,5)',25,
-- 'Financial statements required',
-- 'Standard with conditions',
-- '3 yrs financials'),
-- ('D8','Years in Business','[0,2)',60,
-- 'Full financial review',
-- 'Possible D&O interaction',
-- 'Referral; senior approval');



-- DROP TABLE BRT07;


-- SELECT * FROM BRT07;




-- CREATE TABLE BRT08 (
--    id SERIAL PRIMARY KEY,
--    parameter_name VARCHAR(80) NOT NULL,
--    condition_description VARCHAR(120) NOT NULL,
--    points INTEGER,
--    required_action VARCHAR(150),
--    endorsement VARCHAR(150),
--    hard_stop VARCHAR(50)
-- );


-- INSERT INTO BRT08
-- (parameter_name, condition_description, points, required_action, endorsement, hard_stop)
-- VALUES
-- ('Building Code Compliance','Current code (within 5 yrs)',0,'None','None','No'),
-- ('Building Code Compliance','6–15 years old code',20,'Code upgrade coverage offered','Ordinance/Law endorsement recommended','No'),
-- ('Building Code Compliance','16–30 years old code',50,'Code upgrade coverage required','Ordinance/Law endorsement mandatory','No'),
-- ('Building Code Compliance','> 30 years old code or unknown',90,'Engineering assessment required','Code upgrade + law endorsement','If >$5M TIV'),
-- ('ADA Compliance','Fully compliant',0,'None','GL standard form','No'),
-- ('ADA Compliance','Pending improvements (documented plan)',20,'Timeline and budget required','GL with ADA exclusion note','No'),
-- ('ADA Compliance','Non-compliant (no plan)',80,'Immediate referral to risk counsel','GL with ADA exclusion','Possible GL decline'),
-- ('Environmental Assessment','Phase I — Clean',0,'None','Standard GL','No'),
-- ('Environmental Assessment','Phase I — Recommendations',20,'Phase I recommendations resolved','Pollution exclusion standard','No'),
-- ('Environmental Assessment','Phase II Completed — Clean',10,'Phase II results on file','Pollution exclusion may be removed','No'),
-- ('Environmental Assessment','Phase II — Contamination found',150,'Environmental remediation plan required','Pollution EXCLUDED; refer to enviro market','YES — property coverage referral'),
-- ('Environmental Assessment','None / No assessment',35,'Phase I required if industrial/auto occ','Pollution exclusion applies','If prior industrial use'),
-- ('Risk Management Program','Formal ERM (ISO 31000 / RIMS)',-15,'ERM documentation required','Premium credit applied','No'),
-- ('Risk Management Program','Informal (written policies only)',0,'None','Standard','No'),
-- ('Risk Management Program','Ad hoc (verbal only)',25,'Loss control survey recommended','Standard','No'),
-- ('Risk Management Program','None / Unknown',50,'Loss control survey required','Loss control condition to renewal','No'),
-- ('Deferred Maintenance Score','0–2 (Minimal)',0,'None','Full coverage','No'),
-- ('Deferred Maintenance Score','3–5 (Moderate)',25,'Remediation timeline','Coverage with conditions','No'),
-- ('Deferred Maintenance Score','6–8 (Significant)',80,'Inspection + remediation plan','Scheduled property exclusions','If >8'),
-- ('Deferred Maintenance Score','9–10 (Critical)',150,'Mandatory — decline pending remediation','Severely restricted coverage','YES — hard decline until addressed'),
-- ('Claims Litigation / Disputes','None',0,'None','Standard','No'),
-- ('Claims Litigation / Disputes','Prior dispute resolved',20,'Settlement documentation','Standard with note','No'),
-- ('Claims Litigation / Disputes','Active litigation against carrier',100,'Legal review required','Referral — legal dept approval','YES — legal must approve');



-- SELECT * FROM BRT08;




-- DROP TABLE BRT08A;



-- CREATE TABLE BRT08A (

--     id SERIAL PRIMARY KEY,

--     parameter VARCHAR(3) NOT NULL,

--     parameter_type VARCHAR(80) NOT NULL,

--     condition_description VARCHAR(150),

--     points INTEGER,

--     required_action TEXT,

--     endorsement TEXT,

--     hard_stop VARCHAR(60)

-- );

-- INSERT INTO BRT08A

-- (parameter, parameter_type, condition_description, points, required_action, endorsement, hard_stop)

-- VALUES

-- ('F2','ADA Compliance','Fully compliant',0,

-- 'None','GL standard form','No'),

-- ('F2','ADA Compliance','Pending improvements (documented plan)',20,

-- 'Timeline and budget required',

-- 'GL with ADA exclusion note','No'),

-- ('F2','ADA Compliance','Non-compliant (no plan)',80,

-- 'Immediate referral to risk counsel',

-- 'GL with ADA exclusion','Possible GL decline'),

-- ('F3','Environmental Assessment','Phase I — Clean',0,

-- 'None','Standard GL','No'),

-- ('F3','Environmental Assessment','Phase I — Recommendations',20,

-- 'Phase I recommendations resolved',

-- 'Pollution exclusion standard','No'),

-- ('F3','Environmental Assessment','Phase II Completed — Clean',10,

-- 'Phase II results on file',

-- 'Pollution exclusion may be removed','No'),

-- ('F3','Environmental Assessment','Phase II — Contamination found',150,

-- 'Environmental remediation plan required',

-- 'Pollution EXCLUDED; refer to enviro market',

-- 'YES — property coverage referral'),

-- ('F3','Environmental Assessment','None / No assessment',35,

-- 'Phase I required if industrial/auto occ.',

-- 'Pollution exclusion applies',

-- 'If prior industrial use'),

-- ('F4','Risk Management Program','Formal ERM (ISO 31000 / RIMS)',-15,

-- 'ERM documentation required',

-- 'Premium credit applied','No'),

-- ('F4','Risk Management Program','Informal (written policies only)',0,

-- 'None','Standard','No'),

-- ('F4','Risk Management Program','Ad hoc (verbal only)',25,

-- 'Loss control survey recommended',

-- 'Standard','No'),

-- ('F4','Risk Management Program','None / Unknown',50,

-- 'Loss control survey required',

-- 'Loss control condition to renewal','No'),

-- ('F6','Claims Litigation / Disputes','None',0,

-- 'None','Standard','No'),

-- ('F6','Claims Litigation / Disputes','Prior dispute resolved',20,

-- 'Settlement documentation',

-- 'Standard with note','No'),

-- ('F6','Claims Litigation / Disputes','Active litigation against carrier',100,

-- 'Legal review required',

-- 'Referral — legal dept approval',

-- 'YES — legal must approve');
 


--  SELECT * FROM BRT08A;




-- CREATE TABLE BRT08B (

--    id SERIAL PRIMARY KEY,

--    parameter VARCHAR(80) NOT NULL,

--    condition int4range NOT NULL,

--    points INTEGER,

--    required_action TEXT,

--    endorsement TEXT,

--    hard_stop VARCHAR(50)

-- );
 


-- INSERT INTO BRT08B

-- (parameter, condition, points, required_action, endorsement, hard_stop)

-- VALUES

-- ('Building Code Compliance','[0,6)',0,'None','None','No'),

-- ('Building Code Compliance','[6,16)',20,'Code upgrade coverage offered',

-- 'Ordinance/Law endorsement recommended','No'),

-- ('Building Code Compliance','[16,31)',50,'Code upgrade coverage required',

-- 'Ordinance/Law endorsement mandatory','No'),

-- ('Building Code Compliance','[30,)',90,'Engineering assessment required',

-- 'Code upgrade + law endorsement','If > $5M TIV'),

-- ('Deferred Maintenance Score','[0,3)',0,'None',

-- 'Full coverage','No'),

-- ('Deferred Maintenance Score','[3,6)',25,'Remediation timeline',

-- 'Coverage with conditions','No'),

-- ('Deferred Maintenance Score','[6,9)',80,'Inspection + remediation plan',

-- 'Scheduled property exclusions','If > 8'),

-- ('Deferred Maintenance Score','[9,11)',150,

-- 'Mandatory — decline pending remediation',

-- 'Severely restricted coverage',

-- 'YES — hard decline until addressed');
 


--  SELECT * FROM BRT08B;



-- CREATE TABLE BRT08A (

--    id SERIAL PRIMARY KEY,

--    parameter VARCHAR(80) NOT NULL,

--    condition TEXT NOT NULL,

--    points INTEGER,

--    required_action TEXT,

--    endorsement TEXT,

--    hard_stop VARCHAR(50)

-- );
 
-- INSERT INTO BRT08A

-- (parameter, condition, points, required_action, endorsement, hard_stop)

-- VALUES

-- ('ADA Compliance','Fully compliant',0,'None','GL standard form','No'),

-- ('ADA Compliance','Pending improvements (documented plan)',20,

-- 'Timeline and budget required',

-- 'GL with ADA exclusion note','No'),

-- ('ADA Compliance','Non-compliant (no plan)',80,

-- 'Immediate referral to risk counsel',

-- 'GL with ADA exclusion','Possible GL decline'),

-- ('Environmental Assessment','Phase I — Clean',0,

-- 'None','Standard GL','No'),

-- ('Environmental Assessment','Phase I — Recommendations',20,

-- 'Phase I recommendations resolved',

-- 'Pollution exclusion standard','No'),

-- ('Environmental Assessment','Phase II Completed — Clean',10,

-- 'Phase II results on file',

-- 'Pollution exclusion may be removed','No'),

-- ('Environmental Assessment','Phase II — Contamination found',150,

-- 'Environmental remediation plan required',

-- 'Pollution EXCLUDED; refer to enviro market',

-- 'YES — property coverage referral'),

-- ('Environmental Assessment','None / No assessment',35,

-- 'Phase I required if industrial/auto occupancy',

-- 'Pollution exclusion applies',

-- 'If prior industrial use'),

-- ('Risk Management Program','Formal ERM (ISO 31000 / RIMS)',-15,

-- 'ERM documentation required',

-- 'Premium credit applied','No'),

-- ('Risk Management Program','Informal (written policies only)',0,

-- 'None','Standard','No'),

-- ('Risk Management Program','Ad hoc (verbal only)',25,

-- 'Loss control survey recommended',

-- 'Standard','No'),

-- ('Risk Management Program','None / Unknown',50,

-- 'Loss control survey required',

-- 'Loss control condition to renewal','No'),

-- ('Claims Litigation / Disputes','None',0,

-- 'None','Standard','No'),

-- ('Claims Litigation / Disputes','Prior dispute resolved',20,

-- 'Settlement documentation',

-- 'Standard with note','No'),

-- ('Claims Litigation / Disputes','Active litigation against carrier',100,

-- 'Legal review required',

-- 'Referral — legal dept approval',

-- 'YES — legal must approve');
 







--  SELECT * FROM BRT08A; 
-- DROP TABLE BRT08A;






-- DROP TABLE BRT08B;


-- CREATE TABLE BRT08B (
--    id SERIAL PRIMARY KEY,
--    parameter VARCHAR(3) NOT NULL,
--    parameter_type VARCHAR(80) NOT NULL,
--    condition_range int4range NOT NULL,
--    points INTEGER,
--    required_action TEXT,
--    endorsement TEXT,
--    hard_stop VARCHAR(60)
-- );
-- INSERT INTO BRT08B
-- (parameter, parameter_type, condition_range, points, required_action, endorsement, hard_stop)
-- VALUES
-- ('F1','Building Code Compliance','[0,6)',0,
-- 'None',
-- 'None',
-- 'No'),
-- ('F1','Building Code Compliance','[6,16)',20,
-- 'Code upgrade coverage offered',
-- 'Ordinance/Law endorsement recommended',
-- 'No'),
-- ('F1','Building Code Compliance','[16,31)',50,
-- 'Code upgrade coverage required',
-- 'Ordinance/Law endorsement mandatory',
-- 'No'),
-- ('F1','Building Code Compliance','[30,)',90,
-- 'Engineering assessment required',
-- 'Code upgrade + law endorsement',
-- 'If > $5M TIV'),
-- ('F5','Deferred Maintenance Score','[0,3)',0,
-- 'None',
-- 'Full coverage',
-- 'No'),
-- ('F5','Deferred Maintenance Score','[3,6)',25,
-- 'Remediation timeline',
-- 'Coverage with conditions',
-- 'No'),
-- ('F5','Deferred Maintenance Score','[6,9)',80,
-- 'Inspection + remediation plan',
-- 'Scheduled property exclusions',
-- 'If >8'),
-- ('F5','Deferred Maintenance Score','[9,11)',150,
-- 'Mandatory — decline pending remediation',
-- 'Severely restricted coverage',
-- 'YES — hard decline until addressed');


--  SELECT * FROM brt01; 
















-- DROP TABLE BRT03A;

-- CREATE TABLE BRT03A (
--    id SERIAL PRIMARY KEY,
--    parameter VARCHAR(4) NOT NULL,
--    peril VARCHAR(80) NOT NULL,
--    condition VARCHAR(120) NOT NULL,
--    points_added INTEGER
-- );
-- INSERT INTO BRT03A
-- (parameter, peril, condition, points_added)
-- VALUES
-- ('C2','FEMA Flood Zone','Zone X',0),
-- ('C2','FEMA Flood Zone','Zone AH',40),
-- ('C2','FEMA Flood Zone','Zone AO',40),
-- ('C2','FEMA Flood Zone','Zone AE',80),
-- ('C2','FEMA Flood Zone','Zone A',80),
-- ('C2','FEMA Flood Zone','Zone VE',150),
-- ('C2','FEMA Flood Zone','Zone V',150),
-- ('C5','Wind Zone / Hurricane','Zone 1 (Inland)',10),
-- ('C5','Wind Zone / Hurricane','Zone 2 (Inland)',10),
-- ('C5','Wind Zone / Hurricane','Zone 3 (Gulf/Atlantic)',60),
-- ('C5','Wind Zone / Hurricane','Zone 4 (High-velocity)',120),
-- ('C5','Wind Zone / Hurricane','Zone 5 (High-velocity)',120),
-- ('C10','ISO PPC Rating','Class 1 (Excellent)',-20),
-- ('C10','ISO PPC Rating','Class 2 (Excellent)',-20),
-- ('C10','ISO PPC Rating','Class 3 (Excellent)',-20),
-- ('C10','ISO PPC Rating','Class 4 (Good)',0),
-- ('C10','ISO PPC Rating','Class 5 (Good)',0),
-- ('C10','ISO PPC Rating','Class 6 (Good)',0),
-- ('C10','ISO PPC Rating','Class 7 (Fair)',40),
-- ('C10','ISO PPC Rating','Class 8 (Fair)',40),
-- ('C10','ISO PPC Rating','Class 9 (Poor/Unprotected)',120),
-- ('C10','ISO PPC Rating','Class 10 (Poor/Unprotected)',120);



-- Select * from BRT06B;


-- DROP TABLE BRT03B;

-- CREATE TABLE BRT03B (

--     id SERIAL PRIMARY KEY,

--     parameter VARCHAR(4) NOT NULL,

--     peril VARCHAR(80) NOT NULL,

--     condition int4range NOT NULL,

--     points_added INTEGER

-- );

-- INSERT INTO BRT03B

-- (parameter, peril, condition, points_added)

-- VALUES

-- ('C4','Wildfire Risk Score (0–100)','[0,26)',0),

-- ('C4','Wildfire Risk Score (0–100)','[26,51)',35),

-- ('C4','Wildfire Risk Score (0–100)','[51,76)',80),

-- ('C4','Wildfire Risk Score (0–100)','[76,101)',150),

-- ('C6','Earthquake PML (% TIV)','[0,6)',10),

-- ('C6','Earthquake PML (% TIV)','[6,16)',50),

-- ('C6','Earthquake PML (% TIV)','[16,31)',100),

-- ('C6','Earthquake PML (% TIV)','[31,)',160),

-- ('C7','Hail Score (0–10)','[0,5)',0),

-- ('C7','Hail Score (0–10)','[5,8)',30),

-- ('C7','Hail Score (0–10)','[8,11)',70);
 






-- CREATE TABLE BRT05A (
--    id SERIAL PRIMARY KEY,
--    parameter VARCHAR(3) NOT NULL,
--    metric VARCHAR(80) NOT NULL,
--    condition VARCHAR(120) NOT NULL,
--    points INTEGER,
--    uw_action TEXT,
--    documentation_required TEXT
-- );
-- INSERT INTO BRT05A
-- (parameter, metric, condition, points, uw_action, documentation_required)
-- VALUES
-- ('D1','Prior Carrier Departure','Voluntary / market exit',0,
-- 'Standard processing',
-- 'Prior policy copy'),
-- ('D1','Prior Carrier Departure','Non-renewal (underwriting)',50,
-- 'Reason letter required',
-- 'Non-renewal notice + explanation'),
-- ('D1','Prior Carrier Departure','Cancellation (non-payment)',70,
-- 'Financial review required',
-- 'Payment history; financials'),
-- ('D1','Prior Carrier Departure','Cancellation (misrepresentation)',200,
-- 'AUTO-DECLINE',
-- 'Hard stop — no exceptions');


-- SELECT * FROM BRT05A;








-- CREATE TABLE BRT05B (
--    id SERIAL PRIMARY KEY,
--    parameter VARCHAR(3) NOT NULL,
--    metric VARCHAR(80) NOT NULL,
--    condition int4range NOT NULL,
--    points INTEGER,
--    uw_action TEXT,
--    documentation_required TEXT
-- );
-- INSERT INTO BRT05B
-- (parameter, metric, condition, points, uw_action, documentation_required)
-- VALUES
-- ('D2','5-Yr Loss Count','[0,1)',0,
-- 'Auto-accept credit',
-- 'Signed loss-free affidavit'),
-- ('D2','5-Yr Loss Count','[1,2)',15,
-- 'Accept',
-- 'Loss run + description'),
-- ('D2','5-Yr Loss Count','[2,3)',40,
-- 'Accept with review',
-- 'Loss runs + cause analysis'),
-- ('D2','5-Yr Loss Count','[3,4)',80,
-- 'Senior UW review',
-- 'Full loss runs + risk improvement plan'),
-- ('D2','5-Yr Loss Count','[4,5)',130,
-- 'Mandatory referral',
-- 'Full loss runs + loss control survey'),
-- ('D2','5-Yr Loss Count','[5,)',200,
-- 'Decline or E&S only',
-- 'Full documentation; likely decline standard'),
-- ('D3','5-Yr Incurred ($)','[0,25000)',5,
-- 'Accept',
-- 'None'),
-- ('D3','5-Yr Incurred ($)','[25000,100001)',25,
-- 'Accept',
-- 'Loss run summary'),
-- ('D3','5-Yr Incurred ($)','[100001,500001)',70,
-- 'Senior UW review',
-- 'Full loss runs + cause analysis'),
-- ('D3','5-Yr Incurred ($)','[500001,1000001)',130,
-- 'Mandatory referral',
-- 'Engineering inspection required'),
-- ('D3','5-Yr Incurred ($)','[1000001,)',200,
-- 'Decline standard',
-- 'E&S referral; loss control mandatory');


-- SELECT * FROM BRT05B;








-- -------------------------IN uw action true false-----------------------------------------------



-- CREATE TABLE BRT05B (
--    id SERIAL PRIMARY KEY,
--    parameter VARCHAR(3) NOT NULL,
--    metric VARCHAR(80) NOT NULL,
--    condition int4range NOT NULL,
--    points INTEGER,
--    uw_action TEXT,
--    documentation_required TEXT
-- );
-- INSERT INTO BRT05B
-- (parameter, metric, condition, points, uw_action, documentation_required)
-- VALUES
-- ('D2','5-Yr Loss Count','[0,1)',0,
-- 'False',
-- 'Signed loss-free affidavit'),
-- ('D2','5-Yr Loss Count','[1,2)',15,
-- 'False',
-- 'Loss run + description'),
-- ('D2','5-Yr Loss Count','[2,3)',40,
-- 'False',
-- 'Loss runs + cause analysis'),
-- ('D2','5-Yr Loss Count','[3,4)',80,
-- 'False',
-- 'Full loss runs + risk improvement plan'),
-- ('D2','5-Yr Loss Count','[4,5)',130,
-- 'False',
-- 'Full loss runs + loss control survey'),
-- ('D2','5-Yr Loss Count','[5,)',200,
-- 'True',
-- 'Full documentation; likely decline standard'),
-- ('D3','5-Yr Incurred ($)','[0,25000)',5,
-- 'Accept',
-- 'None'),
-- ('D3','5-Yr Incurred ($)','[25000,100001)',25,
-- 'Accept',
-- 'Loss run summary'),
-- ('D3','5-Yr Incurred ($)','[100001,500001)',70,
-- 'Senior UW review',
-- 'Full loss runs + cause analysis'),
-- ('D3','5-Yr Incurred ($)','[500001,1000001)',130,
-- 'Mandatory referral',
-- 'Engineering inspection required'),
-- ('D3','5-Yr Incurred ($)','[1000001,)',200,
-- 'Decline standard',
-- 'E&S referral; loss control mandatory');


-- Drop table BRT05B;

-- SELECT * FROM BRT05B;





-- DROP TABLE BRT06A;





-- CREATE TABLE BRT06A (

--     id SERIAL PRIMARY KEY,

--     parameter VARCHAR(3) NOT NULL,

--     system VARCHAR(50) NOT NULL,

--     condition VARCHAR(150) NOT NULL,

--     points INTEGER,

--     required_for TEXT,

--     inspection_interval VARCHAR(40)

-- );

-- INSERT INTO BRT06A

-- (parameter, system, condition, points, required_for, inspection_interval)

-- VALUES

-- ('E1','Sprinkler System','NFPA 13 Wet Pipe – 100% coverage',-50,

-- 'Preferred rate; BI credit',

-- 'Annual'),

-- ('E1','Sprinkler System','NFPA 13R / 13D (residential) – 100%',-30,

-- 'Standard credit',

-- 'Annual'),

-- ('E1','Sprinkler System','Partial (75–99% coverage)',20,

-- 'Explanation required',

-- 'Semi-annual'),

-- ('E1','Sprinkler System','Partial (< 75% coverage)',60,

-- 'Engineering plan for full coverage',

-- 'Quarterly'),

-- ('E1','Sprinkler System','None — required occupancy',130,

-- 'Mandatory for restaurants, warehouses >20k sqft',

-- 'N/A — require install timeline'),

-- ('E1','Sprinkler System','None — not required',30,

-- 'Fire alarm upgrade required',

-- 'N/A'),

-- ('E3','Fire Alarm','UL-Listed Central Station Monitored',-20,

-- 'Preferred rate',

-- '6 months'),

-- ('E3','Fire Alarm','Local Alarm + Smoke Detectors',20,

-- 'Standard terms',

-- 'Annual'),

-- ('E3','Fire Alarm','Local Alarm Only (no smoke detection)',50,

-- 'Smoke detector installation required',

-- 'Annual'),

-- ('E3','Fire Alarm','None',100,

-- 'Mandatory — install or decline',

-- 'N/A'),

-- ('E5','Security System','Central-monitored + video + guard service',-15,

-- 'Preferred crime rate',

-- 'Monthly test'),

-- ('E5','Security System','Central-monitored burglar alarm',0,

-- 'Standard crime rate',

-- 'Annual'),

-- ('E5','Security System','Local alarm only',25,

-- 'Standard terms',

-- 'Annual'),

-- ('E5','Security System','None',60,

-- 'Installation required for limits > $500K',

-- 'N/A'),

-- ('E8','Backup Power','Generator — N+1 redundancy',-10,

-- 'BI credit; data center preferred',

-- 'Annual'),

-- ('E8','Backup Power','Generator — single unit',0,
                                   
-- 'Standard',

-- 'Annual'),

-- ('E8','Backup Power','UPS only (no generator)',15,

-- 'Note for BI assessment',

-- 'N/A'),

-- ('E8','Backup Power','None — critical occupancy',40,

-- 'Medical / data center referral required',

-- 'N/A');
 


-- SELECT * FROM BRT06B;

-- DROP TABLE BRT06B;


-- CREATE TABLE BRT06B (

--     id SERIAL PRIMARY KEY,

--     parameter VARCHAR(3) NOT NULL,

--     system VARCHAR(50) NOT NULL,

--     condition_months int4range NOT NULL,

--     points INTEGER,

--     required_for TEXT,

--     inspection_interval VARCHAR(50)

-- );
 
-- INSERT INTO BRT06B

-- (parameter, system, condition_months, points, required_for, inspection_interval)

-- VALUES

-- ('E6','Last Fire Inspection','[0,13)',0,

-- 'Compliant',

-- 'Annual required'),

-- ('E6','Last Fire Inspection','[13,25)',20,

-- 'Schedule inspection at renewal',

-- 'Overdue'),

-- ('E6','Last Fire Inspection','[24,)',70,

-- 'Inspection within 30 days of bind',

-- 'Mandatory before bind');
 

-- Select * from ref_prompt_library;

-- SELECT * FROM BRT06A;












-- CREATE TABLE Risk_Weightage (

--     id SERIAL PRIMARY KEY,

--     risk_domain VARCHAR(4) NOT NULL,

--     weight_percent INTEGER NOT NULL,

--     max_points INTEGER NOT NULL,

--     rationale TEXT

-- );

-- INSERT INTO Risk_Weightage

-- (risk_domain, weight_percent, max_points, rationale)

-- VALUES

-- ('A',25,250,

-- 'Construction type is #1 fire loss driver'),

-- ('B',20,200,

-- 'Occupancy determines base loss cost'),

-- ('C',20,200,

-- 'Catastrophe PML is portfolio accumulation driver'),

-- ('D',15,150,

-- 'Loss history is strongest frequency predictor'),

-- ('E',12,120,

-- 'Sprinklers reduce severity by 50–80%'),

-- ('F',8,80,

-- 'ERM maturity correlates with frequency');
 


-- SELECT * FROM Risk_Weightage; 



-- CREATE TABLE Risk_Score_Band (
--    id SERIAL PRIMARY KEY,
--    band INTEGER NOT NULL,
--    score_range int4range NOT NULL,
--    rating VARCHAR(30) NOT NULL,
--    uw_action VARCHAR(50) NOT NULL,
--    premium_modifier numrange NOT NULL,
--    required_conditions TEXT
-- );
-- INSERT INTO Risk_Score_Band
-- (band, score_range, rating, uw_action, premium_modifier, required_conditions)
-- VALUES
-- (1,'[0,201)','EXCELLENT','Auto-Accept','[-20,-10)',
-- 'Standard policy; enhanced credits available; eligible for 3 yr policy'),
-- (2,'[201,351)','PREFERRED','Accept','[-10,0)',
-- 'Standard policy; minor conditions may apply; annual review'),
-- (3,'[351,501)','STANDARD','Accept w/ Conditions','[0,20)',
-- 'Specific exclusions; higher deductibles; required remediation timeline'),
-- (4,'[501,651)','ELEVATED','Senior UW Review','[20,45)',
-- 'Engineering inspection mandatory; loss control plan required within 30 days'),
-- (5,'[651,801)','HIGH RISK','Refer to Specialty','[45,80)',
-- 'Refer to E&S market; sublimits on cat perils; 5% wind/hail deductible minimum'),
-- (6,'[801,1001)','UNACCEPTABLE','DECLINE','[0,0]',
-- 'Outside appetite; provide declination letter; suggest surplus lines broker');



-- SELECT * FROM Risk_Score_Band; 


-- SELECT * FROM BRT04;

-- SELECT currennt_database();






-- SELECT * FROM agent_eligibility;




-- 7. View all columns in agent_submission_intake (VERTICAL FORMAT)
-- SELECT table_schema,
--       table_name,
--       column_name,
--       data_type,
--       ordinal_position
-- FROM information_schema.columns
-- WHERE table_name = 'BRT01'
-- ORDER BY ordinal_position;



-- SELECT
--    column_name,
--    data_type,
--    is_nullable,
--    character_maximum_length
-- FROM information_schema.columns
-- WHERE table_name = 'attachment_info';

-- Select * from domainf


--###################################################################################################

-- Layout Detection Db table

--###################################################################################################


-- CREATE TABLE attachment_info (
--     id SERIAL PRIMARY KEY,
--     submission_id VARCHAR(50) NOT NULL,
--     attachment_blob_url TEXT NOT NULL,
--     document_classification TEXT NOT NULL,
--     is_templated INT DEFAULT 0
-- );


-- SELECT * FROM ref_prompt_library

-- SELECT * from brt01;






-- SELECT * FROM communication_history;

-- SELECT * FROM claim_sentiment_tracker;

-- SELECT * FROM customer_feedback_per_stage;
-- SELECT * FROM claim_sentiment_tracker WHERE claim_number='CLM-2026-1001';
 
-- SELECT * FROM customer_feedback_per_stage WHERE claim_number='CLM-2026-1001' ORDER BY submitted_at DESC;
 
-- select * from claims;


-- select * from policy_details;

-- SELECT column_name
-- FROM information_schema.columns
-- WHERE table_name='policy_details';


-- SELECT
--    tc.constraint_name,
--    tc.constraint_type,
--    kcu.column_name
-- FROM information_schema.table_constraints tc
-- JOIN information_schema.key_column_usage kcu
-- ON tc.constraint_name = kcu.constraint_name
-- WHERE tc.table_name = 'policy_details';


-- ALTER TABLE policy_details
-- ADD CONSTRAINT policy_details_policy_id_unique
-- UNIQUE (policy_id);


-- DELETE FROM policy_details
-- WHERE id = 1002;
-- TRUNCATE TABLE policy_details;
 
-- select * from policy_details
-- UPDATE claims
-- SET policy_number='3364961688'
-- WHERE claim_number='CLM-2026-1001';


-- UPDATE claims
-- SET policy_number='2767977312'
-- WHERE claim_number='CLM-2026-1001';


-- SELECT *
-- FROM coverage_verification_results
-- WHERE claim_id='CLM-2026-1001';



-- select * from policy_details;


-- select * from claims;


-- DELETE FROM coverage_verification_results
-- WHERE id = 33;

-- ALTER TABLE policy_details
-- ADD COLUMN gw_policy_id VARCHAR(100),
-- ADD COLUMN effective_date TIMESTAMP,
-- ADD COLUMN expiration_date TIMESTAMP,
-- ADD COLUMN insured_name VARCHAR(255),
-- ADD COLUMN account_number VARCHAR(100),
-- ADD COLUMN policy_address TEXT,
-- ADD COLUMN state VARCHAR(100),
-- ADD COLUMN term_type VARCHAR(50),
-- ADD COLUMN premium_amount NUMERIC,
-- ADD COLUMN currency VARCHAR(20),
-- ADD COLUMN city VARCHAR(100),
-- ADD COLUMN country VARCHAR(50),
-- ADD COLUMN postal_code VARCHAR(20);


-- SELECT column_name
-- FROM information_schema.columns
-- WHERE table_name='coverage_verification_results'


-- select * from coverage_verification_results;
select * from claims;
-- select * from policy_details

select * from fnol_submissions;
-- select * from claim_journey_master;



select * from documents;