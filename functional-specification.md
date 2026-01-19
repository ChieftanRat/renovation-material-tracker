# Renovation Project Management Application

## 1. Purpose and Scope
This document defines the functional specification for a small-scale renovation project management application. The application tracks material purchases, labor attendance, task progress, and produces reports for expenses and timelines. The scope includes data capture, module behavior, and output/reporting requirements needed to estimate future projects.

## 2. Core Modules and Data Capture

### 2.1 Material Procurement Module
**Purpose:** Track all material and delivery costs for renovations and build a historical cost base for future estimates.

**Primary Capabilities**
- Create, edit, and archive material purchase entries.
- Associate each purchase with a project and optional task.
- Capture delivery charges separately to enable delivery cost analysis.
- Support filtering and export for reporting.

**Required Data Points per Entry**
- Vendor Name
- Material Description
- Unit Cost
- Quantity
- Total Material Cost (calculated: Unit Cost × Quantity)
- Delivery Cost (optional)
- Date of Purchase
- Associated Project/Task

**Data Validation Rules**
- Unit Cost, Quantity, Total Material Cost, and Delivery Cost must be non-negative numbers.
- Total Material Cost is auto-calculated but editable only by authorized roles (if role-based access is later implemented).
- Date of Purchase cannot be in the future (unless configured to allow pre-orders).

### 2.2 Labor Management Module
**Purpose:** Monitor labor expenditure and attendance to support accurate payroll generation.

**Primary Capabilities**
- Maintain laborer profiles with compensation terms.
- Record daily work sessions and associate them with projects/tasks.
- Calculate hours worked and gross pay based on rate type.

**Required Data Points per Laborer Profile**
- Laborer ID/Name
- Hourly Rate or Fixed Daily Rate

**Required Data Points per Work Session**
- Laborer ID
- Date
- Clock-in Time
- Clock-out Time
- Associated Project/Task

**Data Validation Rules**
- Clock-out Time must be after Clock-in Time.
- Each Work Session must reference a valid laborer and project.
- Rate must be greater than or equal to zero.

### 2.3 Task Progress Tracking Module
**Purpose:** Capture actual time taken for specific renovation tasks for future estimation accuracy.

**Primary Capabilities**
- Create and update task records with time tracking.
- Associate tasks with projects.
- Compute task durations for reporting averages.

**Required Data Points per Task Entry**
- Task Name (e.g., "Cement Block Laying," "Floor Casting")
- Start Date/Time
- End Date/Time
- Associated Project

**Data Validation Rules**
- End Date/Time must be after Start Date/Time.
- Task Name must be selected from a configurable list of predefined tasks or entered as custom.

## 3. Reporting and Analytics

### 3.1 Material Cost Reports
**Outputs**
- Consolidated material cost reports, filterable by vendor, material type, and project.
- Summary of total material expenditure per project.

**Key Calculations**
- Total Material Cost per Project = sum of Total Material Cost + Delivery Cost (if applicable).
- Vendor Spend = sum of Total Material Cost + Delivery Cost grouped by Vendor.

### 3.2 Labor Reports
**Outputs**
- Individual laborer payroll reports with total hours worked and gross pay for a specified period, filterable by laborer and project.
- Overall labor cost summary per project.

**Key Calculations**
- Hours Worked = Clock-out Time − Clock-in Time.
- Gross Pay (Hourly) = Hours Worked × Hourly Rate.
- Gross Pay (Daily) = Number of Work Sessions × Fixed Daily Rate.

### 3.3 Task Performance Analytics
**Outputs**
- Average task completion times for predefined tasks (e.g., average time for floor casting).

**Key Calculations**
- Task Duration = End Date/Time − Start Date/Time.
- Average Duration per Task = mean of Task Duration grouped by Task Name.

### 3.4 Future Project Cost Estimation
**Outputs**
- Estimated future project costs derived from historical material and labor data.

**Key Inputs**
- Historical average material costs per unit and task.
- Average labor hours per task with corresponding wage rates.

**Estimation Approach**
- Estimated Material Cost = sum of forecasted quantities × historical average unit costs.
- Estimated Labor Cost = sum of average hours per task × applicable labor rate.
- Estimated Project Total = Estimated Material Cost + Estimated Labor Cost + average delivery costs.

## 4. Data Relationships and Reference Requirements
- Projects are the top-level entity that link materials, labor sessions, and task entries.
- Tasks can be linked to multiple material purchases and labor sessions for detailed attribution.
- Every report must be filterable by project and date range at minimum.

## 5. Output Formats and Delivery
- Reports must be viewable in-app as tables with sortable columns.
- Reports must be exportable as CSV for external analysis.
- Support summary dashboards for materials, labor, and task performance.
