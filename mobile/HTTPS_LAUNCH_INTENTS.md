# Android HTTPS launch-intent fix

The connected release accepts VIEW intents only for its compile-time pinned
`https://queueless-pulse-staging-free.onrender.com` origin and canonical `/app`
or `/app/…` paths. The initial intent selects the first remote page; a valid later
intent navigates the existing WebView without replacing its session. Invalid later
intents leave the current page unchanged. A launcher start or rejected initial
intent opens the existing Patient entry page.

HTTP, foreign hosts, user information in the authority, alternate ports, malformed
URLs, non-application path prefixes, dot segments and encoded path separators are
rejected. HTTPS port 443 is equivalent to the default port. Existing WebView
redirect restrictions, TLS-error cancellation, disabled mixed content/debugging,
third-party-cookie policy, secure window and Android Back handling remain active.
Only the existing authenticated same-origin service QR endpoints are retained as
download destinations; they are never accepted as launch-intent destinations.
Downloads still require application permissions, valid TLS and PNG validation,
and do not follow HTTP redirects.

The manifest declares HTTPS VIEW handling for the staging host. This does not
claim verified Android App Links: no website association file or Render change
is part of this patch. Depending on Android defaults, users may need to select
this app for supported links in Android Settings. Browser entry remains valid.
Emulator acceptance uses package-scoped VIEW intents, not a fabricated domain
verification state.

## Existing entry paths

- Patient: `/app/b/erode-eye-clinic-demo/service/1`
- Reception: `/app/staff/login?experience=reception`
- Doctor: `/app/staff/login`
- Owner: `/app/owner/login`
- Public Display: `/app/b/erode-eye-clinic-demo/display`

Protected roles continue using their existing server-authorized application
sessions. No credentials are included in intents, source or APK assets. Do not
log intent contents or private ticket links.

## Local verification

Use the project's existing locked dependencies, Android SDK and JDK 21:

```powershell
pnpm --dir mobile install --frozen-lockfile
pnpm --dir mobile run sync
pnpm --dir mobile test
.\mobile\android\gradlew.bat -p .\mobile\android testVerificationDebugUnitTest lintVerificationRelease
```

A connected release build uses the approved HTTPS origin and the existing
private signing environment described in the Android release instructions.
Version name is `0.2.1`, version code `3`. Preserve previous APKs and signing
credentials; installing the correctly signed update does not require uninstalling
or clearing application data. No website deployment, database migration or
Google Play publication is required by this Android-only change.
