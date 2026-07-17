# Source recertification contract

Source recertification 是對一個 Source anchor 的 dated reassessment，不是 link check。它必須重新比對 eligible sources，並依 anchor profile 重跑 executable recipe 或觀察 surface procedure；沒有新 evidence 時，不得把 `due` 或 `stale` 手動改回 `current`。

## Recertification record template

- Source anchor ID：
- Profile：`executable-recipe`／`surface-procedure`／`principle-only`
- Actor／recorded at：
- Claim scope：
- Eligible source URLs／snapshot identities：
- Source checked at：
- Drift class／due date／change trigger：
- Resolved version anchors：
- Verified environment／availability assumptions：
- Steps or observations：
- Expected evidence：
- Actual evidence location：
- Result：`current`／`due`／`stale`
- Conflict／limitation／disposition：
- Maintainer sign-off：`required`／`not-required`／evidence
- Next due date／owner：

## Procedure

1. 從 `source-anchors.json` 取得唯一 anchor record；不要另建平行 registry。
2. 確認 claim scope、profile、sources、drift class 與既有 version anchors。
3. 重新開啟 eligible sources；若第一方來源互相矛盾，保留 First-party conflict，不自行選一邊。
4. Executable recipe 要在 declared environment 重跑 steps 並保存輸出；Surface procedure 要記錄 exact surface path、availability 與 dated observation；Principle-only anchor 不虛構 command evidence。
5. 將 evidence 綁定實際 resolved version、platform、時間與 actor。URL 仍可開啟不等於 recertification。
6. 依 evidence 更新 registry 的 publication、freshness 與 conflict inputs，再由 deterministic gate 推導結果；不得手動指定 `gateState`。
7. 執行 `python3 scripts/trace-source-registry.py` 與 `python3 scripts/validate-course-release.py`。任何 blocker 保持 fail-closed，直到 corrected、bounded 或 retired。

## Legal stop

來源 identity、rights、version、environment、expected evidence、conflict disposition 或 accountable owner 任一不明時，停止 recertification 並維持原 freshness state。安全、權限或 First-party conflict 的 judgment-bearing 變更仍需 Maintainer sign-off。
