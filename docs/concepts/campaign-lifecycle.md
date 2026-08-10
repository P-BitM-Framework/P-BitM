# Campaign lifecycle

## Creation

The admin backend validates the target URL, hostname, selected library
resources, schedule, protocol, and options. It persists the campaign and its
participants atomically; a partial campaign is not committed if creation
fails.

## Scheduled start

Scheduled campaigns begin in `scheduled`. The runtime reconciler activates
them when the timezone-aware start is reached and completes them at the
configured end.

## Active

An active campaign has a campaign service and isolated networks. Participant
browser containers are created on demand after admission.

## Pause and resume

Pause changes the state to `paused` and removes active campaign workloads.
Resume provisions the runtime again and returns the campaign to `active`.

## Stop and cleanup

Stop marks the campaign `completed` and removes related containers and isolated
networks. Deletion is a separate destructive action and is rejected when
resource or authorization constraints are not satisfied.

## Recovery

The admin runtime reconciler checks persisted state against Docker state after
startup and during scheduled runs. Orphan handling uses the configured grace
period instead of immediately deleting unknown workloads.
