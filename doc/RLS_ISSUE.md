# Power BI — RLS Technical Issue & Solution

## RLS Filter Bleeding Into DAX Measures — Root Cause Analysis & Fix

| | |
|---|---|
| **Issue Category** | RLS Filter Bleeding — Aggregate measures returning incorrect results due to RLS table-level filtering |
| **Affected Roles** | Role_HR — KPI cards showing filtered counts instead of org-wide totals |
| **Solution** | Disconnected calculated table using `SUMMARIZE(ALL(Employees))` to bypass RLS for aggregate measures |

---

## 1. The Problem — What Went Wrong

### 1.1 Observed Symptoms

| KPI Measure | Expected Value | Actual Value (HR Login) |
|---|---|---|
| Total Headcount | 10 | ❌ 6 |
| Active Employees | 10 | ❌ 6 |
| Avg Salary | $106,700 | ❌ $98,333 |
| Total Salary Budget | $1,067,000 | ❌ $590,000 |

---

### 1.2 Root Cause — RLS Filter Bleeding

When the HR role logs in, the RLS DAX filter is applied directly on the `Employees` dimension table:

```dax
-- Role_HR filter on Employees table
[Email] = USERPRINCIPALNAME() || [Role] = "Employee"
```

This filter reduces the `Employees` table to only **6 rows** (HR user's own row + all Employee-role rows).

Since ALL measures reference the `Employees` table, they ALL calculate on only 6 rows — not the full 10 employees in the organisation.

---

### 1.3 Why ALL() and REMOVEFILTERS() Don't Work

A natural first attempt is:

```dax
Total Headcount = CALCULATE(COUNTROWS(Employees), ALL(Employees))
```

This does **NOT** work because of the DAX evaluation order:

| Step | Operation | What Happens |
|---|---|---|
| 1 | **RLS Applied** | Employees table reduced to 6 rows — happens at engine level |
| 2 | **DAX Runs** | CALCULATE() evaluates — but table already has only 6 rows |
| 3 | **ALL() Fires** | ALL() removes user-applied filters BUT **cannot remove RLS filters** |
| 4 | **Result** | COUNTROWS = 6 — still wrong because RLS is preserved |

> **Key Principle:** RLS filters are applied at the **VertiPaq engine level** — BEFORE any DAX evaluation. This means they cannot be overridden by DAX filter functions. This is an intentional Power BI security design decision.

---

## 2. The Solution — Disconnected Calculated Table

### 2.1 Core Concept

Create a **disconnected calculated table** that captures a complete snapshot of the Employees data at model load time — before any RLS filters are applied.

Since this table has **NO relationships** to other tables, RLS filters from the Employees table never propagate to it. Measures built on this disconnected table always return org-wide numbers regardless of the logged-in user's role.

---

### 2.2 Step 1 — Create EmpCount Table

In Power BI Desktop: **Modeling tab → New Table** → paste this DAX:

```dax
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
```

Why this works:
- `SUMMARIZE()` creates a new table from the specified columns
- `ALL(Employees)` removes all filters **including RLS** before SUMMARIZE runs
- The resulting `EmpCount` table always contains all 10 rows
- No relationships = no RLS propagation = always full dataset

---

### 2.3 Step 2 — Rebuild All KPI Measures

Replace all aggregate measures to use `EmpCount` instead of `Employees`:

| Measure Name | New DAX Formula |
|---|---|
| Total Headcount | `COUNTROWS(EmpCount)` |
| Active Employees | `CALCULATE(COUNTROWS(EmpCount), EmpCount[Status] = "Active")` |
| Avg Salary | `AVERAGE(EmpCount[Salary])` |
| Total Salary Budget | `SUM(EmpCount[Salary])` |

---

## 3. How The Solution Works — Two Layer Architecture

After the fix, the model operates with two distinct data layers:

### RLS Filtered Layer
- **Table:** `Employees`
- **Rows for HR login:** 6 of 10
- **Used for:** Team Directory table, row-level detail visuals, Employee profile cards
- **Shows:** Only authorized employee rows ✅

### Unfiltered Layer
- **Table:** `EmpCount`
- **Rows always:** 10 of 10
- **Used for:** Total Headcount KPI, Active Employees KPI, Avg Salary KPI, Total Salary Budget KPI
- **Shows:** Org-wide statistics ✅
