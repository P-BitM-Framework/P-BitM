# Keylogger

The browser-container keylogger writes bounded session logs to campaign
storage. Captured text is not emitted to process logs; only file metadata is
synchronized with the campaign backend. Files remain readable by an
authorized physical-host operator.

Runtime tuning uses `KEYLOG_FLUSH_SECONDS`, `KEYLOG_TIMESTAMP_SECONDS`, and
`KEYLOG_MAX_FILE_BYTES`. Screenshot capture is a separate, authenticated,
operator-initiated action.

See:

- [Actions and evidence](https://p-bitm-2269ecee.mintlify.site/user-guide/actions-and-evidence)
- [Storage and backups](https://p-bitm-2269ecee.mintlify.site/administration/storage-and-backups)
- [Authorized use](../../../docs/security/authorized-use.md)
