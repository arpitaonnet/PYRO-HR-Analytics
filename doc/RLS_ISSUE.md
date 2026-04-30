Power BI - RLS Technical Issue & Solution
RLS Filter Bleeding Into DAX Measures - Root Cause Analysis & Fix
ISSUE CATEGORY	RLS Filter Bleeding - Aggregate measures returning incorrect results due to RLS table-level filtering
AFFECTED ROLES	Role_HR - KPI cards showing filtered counts instead of org-wide totals
SOLUTION	Disconnected calculated table using SUMMARIZE(ALL(Employees)) to bypass RLS for aggregate measures

1.  The Problem - What Went Wrong
1.1  Observed Symptoms
KPI Measure	Expected Value	Actual Value (HR Login)
Total Headcount	10	6  WRONG
Active Employees	10	6  WRONG
Avg Salary	$106,700	$98,333  WRONG
Total Salary Budget	$1,067,000	$590,000  WRONG

1.2  Root Cause - RLS Filter Bleeding
When the HR role logs in, the RLS DAX filter is applied directly on the Employees dimension table:
Role_HR filter on Employees table:
[Email] = USERPRINCIPALNAME() || [Role] = "Employee"

This filter reduces the Employees table to only 6 rows. Since ALL measures reference the Employees table, they ALL calculate on only 6 rows - not the full 10 employees in the organisation.

1.3  Why ALL() and REMOVEFILTERS() Do Not Work
A natural first attempt is to use ALL() or REMOVEFILTERS() in the measure:
Total Headcount = CALCULATE(COUNTROWS(Employees), ALL(Employees))

This does NOT work because of the DAX evaluation order:
Step	Operation	What Happens
1	RLS Applied	Employees table reduced to 6 rows - happens at engine level BEFORE DAX
2	DAX Runs	CALCULATE evaluates - but table already has only 6 rows
3	ALL() Fires	ALL() removes user-applied filters BUT cannot remove RLS filters
4	Result	COUNTROWS = 6 - still wrong because RLS is preserved by the engine

RLS filters are applied at the VertiPaq engine level - BEFORE any DAX evaluation. This means they cannot be overridden by DAX filter functions. This is an intentional Power BI security design decision.

2.  The Solution - Disconnected Calculated Table
2.1  Core Concept
Create a disconnected calculated table that captures a complete snapshot of Employees data at model load time - before any RLS filters are applied. Since this table has NO relationships, RLS filters never propagate to it.

2.2  Step 1 - Create EmpCount Table
Modeling tab -> New Table -> paste this DAX:
EmpCount = 
SUMMARIZE(
    ALL(Employees),
    Employees[EmployeeID],
    Employees[FullName],
    Employees[Status],
    Employees[Salary],
    Employees[Department],
    Employees[Role],
    Employees[JobTitle]
)

•	SUMMARIZE() creates a new table from the specified columns
•	ALL(Employees) removes all filters including RLS before SUMMARIZE runs
•	The resulting EmpCount table always contains all 10 rows
•	No relationships = no RLS propagation = always full dataset

2.3  Step 2 - Rebuild All KPI Measures
Measure Name	New DAX Formula
Total Headcount	COUNTROWS(EmpCount)
Active Employees	CALCULATE(COUNTROWS(EmpCount), EmpCount[Status] = "Active")
Avg Salary	AVERAGE(EmpCount[Salary])
Total Salary Budget	SUM(EmpCount[Salary])

3.  Verification After Fix
KPI Measure	HR Login Result	Status
Total Headcount	10	FIXED
Active Employees	10	FIXED
Avg Salary	$106,700	FIXED
Total Salary Budget	$1,067,000	FIXED
Directory Table Rows	6 rows (HR view)	CORRECT

 
4.  Interview Answer
"We encountered a common Power BI RLS challenge where aggregate KPI measures were returning incorrect values for the HR role. The root cause was that our RLS filter was applied directly on the Employees dimension table - this caused all DAX measures referencing that table to calculate on the filtered subset rather than the full dataset.

For example, Total Headcount was returning 6 instead of 10 for HR users because the RLS filter reduced the Employees table to only HR-visible rows before any DAX evaluation occurred. Using ALL() or REMOVEFILTERS() did not help because RLS filters take precedence over DAX filter manipulation - they are applied at the VertiPaq engine level before DAX runs.

The solution was to create a disconnected calculated table using SUMMARIZE(ALL(Employees)) which captures a complete snapshot of the Employees data at model load time before RLS is applied. Since this table has no relationships to other tables, RLS filters never propagate to it. We then built all aggregate KPI measures against this disconnected table, while keeping row-level visuals like the directory table pointing to the original RLS-filtered Employees table.

This gives us a clean two-layer architecture: the RLS layer controls what rows users see in detail visuals, while the disconnected layer provides accurate org-wide statistics regardless of the viewer's role."

5.  Key Technical Terms
Term	Definition
RLS Filter Bleeding	When RLS filters unintentionally restrict measure calculations beyond their intended scope
Table-Level RLS	RLS applied to an entire table affects ALL queries against that table including measures
Disconnected Table	A calculated table with no relationships - completely bypasses RLS propagation
SUMMARIZE(ALL())	DAX pattern that captures a full table snapshot before RLS filters are applied
DAX Evaluation Order	RLS -> table filters -> context transition -> DAX measures. RLS always runs first.
Two-Layer Architecture	Separate tables for filtered row-level visuals (RLS) vs aggregate KPIs (disconnected)
VertiPaq Engine	Power BI in-memory columnar database engine that applies RLS before DAX evaluation

6.  The Golden Rule
Remember This Rule
RLS filter on Table X  ->  ALL measures using Table X are affected
Cannot be bypassed with ALL() or REMOVEFILTERS()
Solution: Use SUMMARIZE(ALL(Table)) disconnected table for aggregates

Document prepared for Power BI Developer interview preparation. Based on real implementation of PYRO HR Analytics Platform.
