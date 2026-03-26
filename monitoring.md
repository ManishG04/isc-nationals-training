## CloudWatch Logs Insights

Querying cloudwatch logs

```bash
fields @timestamp, @message
| filter @message like /Error|Exception|Failed|Timeout/
| sort @timestamp desc
| limit 20
```

