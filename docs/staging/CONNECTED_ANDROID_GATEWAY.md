# Connected Android gateway verification

The approved Free staging backend was deployed from
`e4e49fb82a4080d3d0e9c2069ca2bb873889de16` at
`https://queueless-pulse-staging-free.onrender.com`. Automatic deployments and PR
previews remain off. This Android correction does not require a backend redeploy.

The signed Android 14 emulator build issued a persisted patient ticket and
received CALLED and COMPLETED updates. Navigating to Reception then revealed
repeated invitation dialogs: `onReceivedHttpAuthRequest` prompted on every new
protected fetch path even when this Activity already held the invitation.

The handler now reuses the invitation held in memory only when the configured
HTTPS origin, challenge host and restricted-demo realm match, and Android's
`useHttpAuthUsernamePassword()` says the credentials remain suitable for the
current request. A rejected attempt prompts again. No credential store, TLS
bypass, gateway removal, injected application credentials or new permission was
introduced. The new native regression test covers missing invitations, rejected
attempts, foreign hosts, foreign realms and foreign page origins.

Android documents this retry signal in the
[HttpAuthHandler API](https://developer.android.com/reference/android/webkit/HttpAuthHandler#useHttpAuthUsernamePassword()).

Rebuild from the candidate worktree using the existing private signing profile:

```powershell
.\scripts\build-android.ps1 -Variant Staging -StagingOrigin 'https://queueless-pulse-staging-free.onrender.com'
```

This produces `evidence/android/QueueLess-Pulse-Staging.apk`. The installation
verification flavor remains separate. Staging invitation and role credentials,
signing material, APKs, backups and acceptance artifacts are ignored and must
never be committed. Physical-device results must be reported separately from
emulator and browser results.
