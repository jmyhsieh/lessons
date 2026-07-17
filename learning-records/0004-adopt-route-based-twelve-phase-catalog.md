# 採用 route-based 十二 Phase catalog migration

Status: adopted

## 決策

使用者決定採用 [[MISSION.md]] 與 Issue #13 定義的 route-based 十二 Phase catalog migration：以 mission-first 入口、Task route、共同基礎、條件式 toolbox、Route synthesis artifact 與 coherent Migration release 取代舊五 Phase 的近線性課程呈現。這裡的 adoption 只表示課程 owner 採納這項 course-design decision，不是 real organizational adoption，也不代表任一 learner 已完成課程或 production 已發布新 catalog。

## 三個 state planes

- **Course-design history：** `learning-records/` 以 append-only 方式保存課程設計決策；migration manifest 的 `planned`／`authored` 只記錄頁面在 catalog migration 中的處置與 authoring 狀態。這筆記錄不改寫前三筆 learning records，也不把 authoring evidence 當成 publication evidence。
- **Learner-owned state：** learner 以 Return notebook 保存 selected route、readiness、Evidence carryover、`Lesson practiced`、`Route artifact produced`、artifact、judgment、feedback 與 return point。Return notebook 不是 course-design learning record、browser progress、completion authority 或 publication record。
- **Publication state：** 只有 exact coherent candidate 完成 deterministic 與 browser validation、固定 Review checkpoint、通過 Review、取得 Maintainer authorization，並完成 coherent cutover 與 public-host verification 後，才可記錄實際發布。Local migration commit、manifest `authored` 或本 learning record 都不會授權或證明 publication。

三個 state planes 不能互相推出：course history 不等於 learner progress，learner evidence 不等於 page authoring／publication，publication 也不替任何 learner 宣稱 route completion。
