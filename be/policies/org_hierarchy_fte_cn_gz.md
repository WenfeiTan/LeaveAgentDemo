# Org Hierarchy Reference - FTE_CN_GZ

Document ID: ORG-HIER-FTE-CN-GZ-2026
Applies To: Full-time employees (FTE) in Guangzhou, China
Effective Date: January 1, 2026

## 1. Org Chart

```mermaid
graph TD
  EMP9000["EMP9000 LiJun (Director, DataTech)"]

  subgraph DT["DataTech - Guangzhou"]
    EMP9100["EMP9100 ZhaoPeng (M2)"]
    EMP9101["EMP9101 XiaoMing (IC2)"]
    EMP9102["EMP9102 NancyFu (IC1)"]
    EMP9110["EMP9110 HeRui (HRBP)"]
  end

  subgraph AD["Admin - Guangzhou"]
    EMP9200["EMP9200 WangMin (M1)"]
    EMP9201["EMP9201 LiuXin (IC2)"]
    EMP9210["EMP9210 SunQing (HRBP)"]
  end

  subgraph FN["Finance - Guangzhou"]
    EMP9250["EMP9250 GaoLin (M1)"]
    EMP9251["EMP9251 XuTao (IC2)"]
    EMP9260["EMP9260 ZhouYi (HRBP)"]
  end

  EMP9000 --> EMP9100
  EMP9100 --> EMP9101
  EMP9101 --> EMP9102
  EMP9100 --> EMP9110

  EMP9000 --> EMP9200
  EMP9200 --> EMP9201
  EMP9200 --> EMP9210

  EMP9000 --> EMP9250
  EMP9250 --> EMP9251
  EMP9250 --> EMP9260
```

## 2. Department Set
- Admin
- DataTech
- Finance

## 3. Reporting Chain Policy
- direct manager: employee.manager_id
- skip-level manager: direct manager.manager_id

## 4. HRBP Belonging
HRBP owner is defined by `(department, location)`:
- `(DataTech, Guangzhou)` -> `EMP9110`
- `(Admin, Guangzhou)` -> `EMP9210`
- `(Finance, Guangzhou)` -> `EMP9260`
