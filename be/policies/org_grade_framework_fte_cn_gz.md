# Org & Grade Framework - FTE_CN_GZ

Document ID: ORG-GRADE-FTE-CN-GZ-2026
Applies To: Full-time employees (FTE) in Guangzhou, China
Effective Date: January 1, 2026

## 1. Grade Order
Grade order from junior to senior:
IC1 < IC2 < IC3 < M1 < M2 < Director

HRBP Level Alignment:
- HRBP is a functional role aligned to manager level M1 for approval and benefit policy interpretation.

## 2. Reporting Chain Terms
- direct manager: employee's manager_id
- skip-level manager: direct manager's manager_id
- department head: highest manager in same department chain

## 3. Department Definition
Standard departments:
- Admin: general administration and office operations
- DataTech: data, engineering, analytics, and platform functions
- Finance: accounting, FP&A, treasury, and controlling
- PeopleOps: HR operations and business partner functions (recommended for HRBP ownership)

## 4. HRBP Belonging Rule
HRBP scope is determined only by (department, location).

Assignment rule:
- For each (department, location), configure exactly one active HRBP owner.
- Employee belongs to the HRBP owner of employee.department + employee.location.
- If no owner is configured for that pair, HRBP is unassigned and should be treated as null.
