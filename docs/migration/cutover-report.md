# Coherent migration cutover report

> 這是 cutover evidence 的空白模板，不是已完成的發布紀錄。填寫時必須引用外部固定的 candidate identity；本檔不能用自己的 commit SHA 證明自己。

## Candidate identity

- Fixed point：
- Candidate commit SHA：
- Candidate tree SHA：
- Reviewed manifest digest：
- Prepared at／by：

## Deterministic verification

| Contract | Command | Result | Evidence location |
|---|---|---|---|
| Migration freeze | `python3 scripts/verify-migration-freeze.py` |  |  |
| Migration manifest | `python3 scripts/verify-migration-manifest.py` |  |  |
| Route navigation | `python3 scripts/verify-route-navigation.py` |  |  |
| Durable course docs | `python3 scripts/verify-durable-course-docs.py` |  |  |
| Source registry | `python3 scripts/trace-source-registry.py` |  |  |
| Release candidate | `python3 scripts/validate-course-release.py` |  |  |

## Browser evidence

- Served candidate identity：
- Browser／version／platform：
- Index、TOC、route entry 與 route action result：
- Compatibility／Deprecation target result：
- Quiz／checklist interaction result：
- Failure、skip、partial 或 uncertainty：

## Review and authorization

- Review fixed point：
- Final Review checkpoint：
- Standards findings／disposition：
- Spec findings／disposition：
- Maintainer authorization evidence：

## Public cutover verification

- Production deployment identity：
- Stable public URL verification：
- GitHub Pages／secondary-host boundary：
- Rollback point and owner：
- Final disposition：`authorized`／`blocked`

## Claim boundary

Local checks、candidate commits、Review output 或本模板本身都不證明 production 已發布。只有外部 deployment identity、public-host observations 與 maintainer authorization 全部綁定同一 candidate 時，才能記錄 coherent cutover。
