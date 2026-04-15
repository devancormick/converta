# Runbook: Feature Drift Detected (PSI > 0.20)

**Alert:** PSI score for a feature exceeded 0.20 (warn) or 0.25 (critical)  
**Severity:** Slack (warn), PagerDuty + rollback flag (critical)

## Investigation Steps

1. Identify which feature triggered the alert from the Grafana Drift PSI panel
2. Check if a new data pipeline ran or if source data schema changed
3. Compare input distribution this week vs last week in `eval_results`
4. Check if the upstream campaign or applicant segment mix has shifted

## Remediation

**PSI 0.20–0.25 (Warning):**
- Investigate data source changes
- Schedule classifier retraining with recent data: `make retrain-ci`

**PSI > 0.25 (Critical):**
- Flag rollback candidate — evaluate if current model performance is degraded
- If conversion rate also dropped: execute rollback: `make rollback MODEL=<version>`
- File incident and retrain ASAP with recent labeled data

## Post-Incident

- Document root cause in incident log
- Update Great Expectations suite if distribution shift is expected/permanent
