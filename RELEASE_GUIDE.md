# Release Guide

本指南用于规范版本发布流程。

## 发布前
1. 确认主分支干净、CI 通过
2. 本地执行：

```bash
npm install
npm run test:all
```

3. 如果涉及数据库/协议变更：
- 更新 `backend/db/schema.sql`
- 说明兼容策略（旧库/旧字段如何处理）
- 更新 README 或升级说明

## 版本规则
采用语义化版本：`MAJOR.MINOR.PATCH`
- MAJOR：不兼容变更
- MINOR：向后兼容新功能
- PATCH：向后兼容修复

## 发布步骤
1. 更新版本号（根 package 与需要的 workspace）
2. 整理变更说明（建议维护 `CHANGELOG.md`）
3. 打标签并推送：

```bash
git checkout main
git pull
git tag vX.Y.Z
git push origin vX.Y.Z
```

4. 在 GitHub Releases 发布说明中至少包含：
- 新增功能
- 修复问题
- 兼容性影响
- 升级注意事项

## 回滚策略
1. 停止 worker（避免继续处理错误任务）
2. 回滚到上一稳定 tag
3. 记录事故原因与修复计划

## 发布检查清单
- [ ] `npm run test:all` 通过
- [ ] 文档已更新
- [ ] 版本号与 tag 一致
- [ ] 发布说明已完成
- [ ] 回滚方案已确认
