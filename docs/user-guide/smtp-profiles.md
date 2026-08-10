# SMTP profiles

SMTP profiles define delivery transport and sender identity for complete
campaigns.

## Transport settings

Configure the SMTP host, port, username, password, sender address, and optional
sender name. Select at most one encrypted transport mode:

- **TLS** for STARTTLS;
- **SSL** for implicit TLS;
- neither only when the approved test server explicitly uses plaintext.

The backend tests the resulting SMTP configuration during profile updates. A
failed test rejects the update instead of saving unusable settings.

## Ignore certificate errors

Keep **Ignore certificate errors** disabled. Enable it only for an explicitly
approved test server using a self-signed or otherwise unverifiable
certificate. It is valid only when TLS or SSL is enabled and weakens endpoint
authentication.

## Sensitive values

SMTP passwords and DKIM private keys are encrypted before persistence. They
remain sensitive: restrict dashboard access, avoid screenshots containing
them, and rotate them after the engagement.
