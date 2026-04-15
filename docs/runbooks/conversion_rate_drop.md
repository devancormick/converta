# Runbook: Conversion Rate Drop > 10%

**Alert:** Conversion rate dropped > 10% vs 7-day baseline  
**Severity:** PagerDuty page

## Investigation Steps

1. Check Grafana → Model Quality dashboard for classifier pass rate changes
2. Check if a new prompt version was deployed in the last 24h (`prompt_versions` table)
3. Check if a new classifier version was promoted (`model_versions` table, `champion=true`)
4. Check experiment status — any new experiment running that could skew traffic?
5. Check `eval_results` for average `llm_judge_score` drop over the same period

## Remediation

- If caused by a new prompt version: `make rollback MODEL=<previous_version>` or deprecate the prompt
- If caused by classifier: run `make rollback MODEL=<previous_version>`
- If caused by experiment: pause the experiment via `POST /v1/experiments/{id}/pause`

## Escalation

If not resolved within 30 minutes, escalate to ML team lead.
