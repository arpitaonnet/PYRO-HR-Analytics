# PYRO HR Analytics — Power BI RLS Portfolio Project

![Power BI](https://img.shields.io/badge/Power%20BI-F2C811?style=for-the-badge&logo=powerbi&logoColor=black)
![Microsoft Entra ID](https://img.shields.io/badge/Microsoft%20Entra%20ID-0078D4?style=for-the-badge&logo=microsoft&logoColor=white)
![Microsoft Fabric](https://img.shields.io/badge/Microsoft%20Fabric-0078D4?style=for-the-badge&logo=microsoft&logoColor=white)
![DAX](https://img.shields.io/badge/DAX-FF6B35?style=for-the-badge)

A production-grade Power BI report implementing **Dynamic Row Level Security (RLS)** for an HR Analytics platform. Built end-to-end — from Microsoft Entra ID group provisioning through to a published Power BI App with role-based page navigation and org-wide KPI measures.

---

## Project Overview

**PYRO** (HR Analytics Platform) demonstrates how to implement enterprise-grade RLS in Power BI using real Microsoft Entra ID security groups, dynamic DAX measures, and a published Power BI App with audience-based access control.

| Dimension | Detail |
|-----------|--------|
| Tool | Power BI Desktop + Power BI Service |
| Identity | Microsoft Entra ID (pyrodemo tenant) |
| License | Microsoft 365 Business Standard (Power BI Pro) |
| Data Source | Excel (.xlsx) — 4 tables |
| RLS Type | Dynamic RLS using USERPRINCIPALNAME() |
| Roles | 3 roles — CEO/CFO, HR, Employee |
| Pages | 4 pages — Home, Employee, HR, CEO/CFO |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│            IDENTITY LAYER — Microsoft Entra ID       │
│  PBI_Executives  │  PBI_HR_Team  │  PBI_Employees   │
└──────────────────────────┬──────────────────────────┘
                           │ UPN sync
┌──────────────────────────▼──────────────────────────┐
│              DATA LAYER — Power BI Model             │
│  Employees (dim) → Projects (fact)                  │
│  Employees (dim) → Promotions (fact)                │
│  EmpCount (disconnected — bypasses RLS)             │
└──────────────────────────┬──────────────────────────┘
                           │ RLS roles
┌──────────────────────────▼──────────────────────────┐
│           SECURITY LAYER — Row Level Security        │
│  Role_CEO_CFO → TRUE()                              │
│  Role_HR      → Email=UPN OR Role="Employee"        │
│  Role_Employee → Email=UPN                          │
└──────────────────────────┬──────────────────────────┘
                           │ filtered data
┌──────────────────────────▼──────────────────────────┐
│        PRESENTATION LAYER — PYRO App                 │
│  Home page → dynamic nav (role-based visibility)    │
│  Employee page → profile cards + projects           │
│  HR page → team directory + salary charts           │
│  CEO/CFO page → KPIs + org analytics               │
└─────────────────────────────────────────────────────┘
```

---

## Repository Structure

```
PYRO-HR-Analytics/
│
├── README.md                          ← This file
│
├── data/
│   ├── PYRO_Clean.xlsx               ← Main data source (4 sheets)
│   └── PYRO_RLS_SampleData_RealWorld.xlsx  ← Extended reference data
│
├── report/
│   └── PYRO_RLS.pbix                 ← Power BI Desktop report file
│
├── assets/
│   ├── PYRO_Logo_Color.png           ← Logo for light backgrounds
│   ├── PYRO_Logo_Transparent.png     ← Logo for dark header
│   ├── PYRO_Logo_White.png           ← White version
│   ├── PYRO_Logo.svg                 ← Vector source
│   ├── icon_employee.png             ← Navigation card icon
│   ├── icon_hr.png                   ← Navigation card icon
│   ├── icon_executive.png            ← Navigation card icon
│   └── icon_lock.png                 ← Locked state icon
│
├── theme/
│   └── PYRO_Theme.json               ← Power BI custom theme file
│
├── docs/
│   ├── RLS_Issue_Solution.docx       ← RLS filter bleeding issue & fix
│   └── PYRO_RLS_Implementation_Guide.docx  ← Full implementation guide
│
└── dax/
    ├── rls_roles.dax                 ← All 3 RLS role expressions
    ├── measures_kpi.dax              ← KPI card measures
    ├── measures_employee.dax         ← Employee tab measures
    ├── measures_navigation.dax       ← Role detection + nav measures
    └── empcout_table.dax             ← Disconnected table definition
```

---

## Data Model

### Tables

| Table | Type | Rows | Purpose |
|-------|------|------|---------|
| `Employees` | Dimension | 10 | Core employee data — RLS applied here |
| `Projects` | Fact | 10 | Project allocations linked by EmployeeID |
| `Promotions` | Fact | 5 | Promotion records linked by EmployeeID |
| `RLS_SecurityMapping` | Security | 5 | Email → PBI_Role mapping |
| `EmpCount` | Disconnected | 10 | Bypasses RLS for org-wide KPIs |
| `_Measures` | Measure table | — | All DAX measures centralised |

### Relationships

```
Projects     ──(Many)──► Employees ◄──(Many)── Promotions
                              │
                        (One-to-One)
                              │
                    RLS_SecurityMapping
```

### Star Schema Design

The model follows star schema principles with `Employees` as the central dimension table. All relationships use single cross-filter direction except `RLS_SecurityMapping` which uses bidirectional to support dynamic RLS filtering.

---

## RLS Implementation

### Roles

```dax
-- Role_CEO_CFO (filter on Employees table)
TRUE()

-- Role_HR (filter on Employees table)
[Email] = USERPRINCIPALNAME()
    || [Role] = "Employee"

-- Role_Employee (filter on Employees table)
[Email] = USERPRINCIPALNAME()
```

### Security Group Mapping

| Entra ID Group | Power BI Role | Access |
|----------------|---------------|--------|
| PBI_Executives | Role_CEO_CFO | All rows, all pages |
| PBI_HR_Team | Role_HR | Own row + Employee rows |
| PBI_Employees | Role_Employee | Own row only |

### Dynamic Navigation Measures

```dax
Is_CEO_CFO =
IF(
    CALCULATE(
        COUNTROWS(RLS_SecurityMapping),
        RLS_SecurityMapping[Email] = USERPRINCIPALNAME(),
        RLS_SecurityMapping[PBI_Role] = "Role_CEO_CFO"
    ) > 0, 1, 0
)

Can_See_HR_Page =
IF(
    CALCULATE(
        COUNTROWS(RLS_SecurityMapping),
        RLS_SecurityMapping[Email] = USERPRINCIPALNAME(),
        RLS_SecurityMapping[PBI_Role] IN {"Role_HR", "Role_CEO_CFO"}
    ) > 0, 1, 0
)
```

---

## Key Technical Challenge — RLS Filter Bleeding

### Problem

When `Role_HR` is applied, the RLS filter on the `Employees` table reduces it to 6 rows. All DAX measures referencing `Employees` then calculated on 6 rows — causing KPI cards to show wrong org-wide totals.

```
Total Headcount = COUNTROWS(Employees)  ← returns 6, not 10 for HR role
```

Using `ALL()` or `REMOVEFILTERS()` does not help — RLS filters are applied at the VertiPaq engine level before DAX evaluation.

### Solution — Disconnected Calculated Table

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

`SUMMARIZE(ALL(Employees))` captures a full snapshot at model load time — before RLS applies. Since `EmpCount` has no relationships, RLS never propagates to it.

```dax
-- Correct KPI measures using disconnected table
Total Headcount    = COUNTROWS(EmpCount)
Active Employees   = CALCULATE(COUNTROWS(EmpCount), EmpCount[Status] = "Active")
Avg Salary         = AVERAGE(EmpCount[Salary])
Total Salary Budget = SUM(EmpCount[Salary])
```

---

## Report Pages

### Home (Landing Page)
- Dynamic welcome message using `My Name` measure
- Role-aware navigation cards — HR and Executive cards hidden for Employee role
- Blocking rectangle pattern to prevent unauthorized navigation
- Footer: "Access is controlled by your role · RLS Active"

### Employee Tab
- Profile cards: Name, Department, Job Title, Salary, Status, Manager
- My Projects table (own projects only)
- My Promotions table (own promotions only)
- All values filtered by `USERPRINCIPALNAME()`

### HR Tab
- KPI cards: Total Headcount, Avg Salary, Active Employees (org-wide via EmpCount)
- Team Directory table (Employee rows + own HR row)
- Promotions table (all promotions)
- Salary by Department bar chart

### CEO/CFO Tab
- 4 KPI cards: Headcount, Salary Budget, Active Projects, Total Promotions
- 3 bar charts: Headcount by Dept, Salary by Dept, Project Allocation %
- Full Employee Directory with all columns

---

## Power BI App Configuration

### Audiences

| Audience | Security Group | Pages Visible |
|----------|---------------|---------------|
| PBI_Employee | PBI_Employees | All (data restricted by RLS) |
| PBI_HR | PBI_HR_Team | All (data restricted by RLS) |
| PBI_Executive | PBI_Executives | All (full access) |

> Note: Individual page hiding per audience requires Fabric capacity. In this implementation, page-level security is achieved through dynamic button visibility and blocking rectangles using DAX role detection measures.

---

## Setup Instructions

### Prerequisites
- Power BI Desktop (April 2026 or later)
- Microsoft 365 Business Standard or Power BI Pro license
- Microsoft Entra ID tenant with Global Administrator access

### Step 1 — Clone Repository
```bash
git clone https://github.com/yourusername/PYRO-HR-Analytics.git
```

### Step 2 — Set Up Entra ID
1. Create three Security Groups in Microsoft Entra ID:
   - `PBI_Executives`
   - `PBI_HR_Team`
   - `PBI_Employees`
2. Create test users and assign to groups
3. Assign Power BI Pro licenses via M365 Admin Center

### Step 3 — Update Email Domain
Open `data/PYRO_Clean.xlsx` and update all email addresses in:
- `Employees` sheet → Email column
- `RLS_SecurityMapping` sheet → Email column

Replace `pyrodemo.onmicrosoft.com` with your tenant domain.

### Step 4 — Open Report
1. Open `report/PYRO_RLS.pbix` in Power BI Desktop
2. Go to **Home → Transform Data → Power Query**
3. Update data source to point to your local `PYRO_Clean.xlsx`
4. Apply **Transform → Format → Lowercase** on all Email columns
5. Click **Close & Apply**

### Step 5 — Apply Theme
1. **View → Themes → Browse for themes**
2. Select `theme/PYRO_Theme.json`

### Step 6 — Publish
1. **Home → Publish**
2. Sign in with your admin account
3. Select your workspace
4. Go to **app.powerbi.com → Datasets → Security**
5. Assign security groups to roles:
   - `Role_CEO_CFO` → `PBI_Executives`
   - `Role_HR` → `PBI_HR_Team`
   - `Role_Employee` → `PBI_Employees`

### Step 7 — Create App
1. Workspace → **Create app**
2. Configure 3 audiences with respective security groups
3. Publish app and share link with users

### Step 8 — Test
Open an incognito browser and log in as each test user to verify RLS behaviour.

---

## Test Users

| User | Role | Expected Behaviour |
|------|------|-------------------|
| alice.johnson@ | CEO | Sees all data, all pages |
| robert.kim@ | CFO | Sees all data, all pages |
| sarah.patel@ | HR | Sees own row + all employee rows |
| maria.garcia@ | Employee | Sees own row only |
| lisa.wong@ | Employee | Sees own row only |

---

## Certifications

| Certification | Relevance |
|---------------|-----------|
| PL-300 — Power BI Data Analyst | Core Power BI skills |
| DP-600 — Microsoft Fabric Analytics Engineer | Fabric + advanced analytics |

---

## Skills Demonstrated

- End-to-end Power BI development (requirements → published app)
- Dynamic Row Level Security with USERPRINCIPALNAME()
- Microsoft Entra ID group-based access control
- Star schema data modelling
- Advanced DAX — SUMMARIZE, CALCULATE, USERPRINCIPALNAME, SELECTEDVALUE
- RLS filter bleeding problem — disconnected table solution
- Power BI App with audience-based access control
- Custom theme development (JSON)
- UI/UX design — navigation cards, conditional visibility, role-aware layout


---

## License

This project is for portfolio and educational purposes.

---

## Author

**Your Name**
Power BI Developer · PL-300 · DP-600
[LinkedIn](https://linkedin.com/in/yourprofile) · [GitHub](https://github.com/yourusername)
