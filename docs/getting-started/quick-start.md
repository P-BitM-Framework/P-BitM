# Quick start

These steps assume installation and setup are complete.

## Start the stack

```bash
python3 p-bitm.py up
```

Missing images are built automatically. Force a rebuild after source or
dependency changes:

```bash
python3 p-bitm.py up --build
```

Open the configured dashboard URL, which defaults to:

```text
https://127.0.0.1:8443/
```

On the first successful start, the CLI displays the initial administrator
credentials after confirming that the account was persisted. Change the
password after signing in.

## Verify the deployment

```bash
python3 p-bitm.py status
python3 p-bitm.py doctor
```

## Prepare a campaign

Create the reusable resources in this order:

1. target list;
2. email template;
3. SMTP profile;
4. landing page;
5. optional plugins and modules;
6. campaign.

Use only approved test recipients and infrastructure.

## Stop the complete runtime

```bash
python3 p-bitm.py down
```

This is a terminal shutdown: active, paused, and scheduled campaigns are marked
completed, and all app-owned campaign, browser, and egress containers are
removed. Running `up` later starts only the control plane; it does not resume
those campaigns.
