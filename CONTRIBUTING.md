# Contribution Guide

感谢你为本项目做贡献。

## 开发流程
1. Fork 仓库并创建分支（`feat/*`、`fix/*`、`chore/*`）
2. 小步提交，避免一次 PR 混入无关改动
3. 提交前本地通过测试
4. 发起 PR 并说明：
   - 改动内容
   - 验证方式
   - 风险与兼容性影响

## 提交规范
建议使用 Conventional Commits：
- `feat: ...`
- `fix: ...`
- `docs: ...`
- `refactor: ...`
- `test: ...`
- `chore: ...`

## 开发约定
- 优先“先加测试再改代码”
- 不要引入硬编码绝对路径
- 新配置优先用参数或环境变量
- 文案保持中英文策略一致（当前 UI 以中文为主）

## 必跑检查
```bash
npm run test:python
npm run test:web
```

## PR 检查清单
- [ ] 改动聚焦且说明清楚
- [ ] 已增加/更新测试
- [ ] `npm run test:python` 通过
- [ ] `npm run test:web` 通过
- [ ] 必要文档已更新

## Issue 反馈建议
请提供：
- 复现步骤
- 预期结果 / 实际结果
- 关键日志（脱敏）
- 运行环境（OS / Python / Node / ffmpeg）
