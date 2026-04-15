# Runbook: Classifier Pass Rate Drop > 15%

**Alert:** Classifier pass rate dropped > 15%  
**Severity:** Slack alert + auto-pause new deployments

## Investigation Steps

1. Check `eval_results.classifier_score` distribution vs last 7 days in Grafana
2. Check if the classifier model was retrained/promoted recently (`model_versions`)
3. Check if input message distribution has changed (new campaign, segment shift)
4. Run PSI drift check manually if not recent: `make weekly-drift-check`

## Remediation

- If classifier issue: `make rollback MODEL=<previous_champion_version>`
- If input distribution shift: retrain with recent data: `make retrain-ci`
- If deployment issue: restart API service, reload champion: `POST /v1/admin/reload-classifier`

## Escalation

If pass rate is below 50%, escalate immediately — messages may be blocked in production.
