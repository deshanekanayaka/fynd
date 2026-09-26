# Orchestration runs locally, not in the cloud

Airflow runs in Docker on the developer machine. The scheduled cloud work is triggered by
EventBridge Scheduler against Fargate tasks instead.

The reason Airflow is wanted at all is backfill: the Backtest reruns pipeline stages across
several cutoff dates, and that work happens while developing, not in production. Managed
orchestration costs several hundred dollars a month, and self-hosting it on a small instance
would introduce the only always-on server in the design, which then has to be patched. Running
it locally keeps the directed acyclic graph in the repository, keeps the backfill capability,
and leaves nothing running in the cloud between scheduled task runs.
