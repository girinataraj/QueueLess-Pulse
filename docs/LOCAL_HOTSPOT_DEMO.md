# Erode demo on Windows Mobile Hotspot

The same approved React build and PostgreSQL records are used. Flask listens specifically on **192.168.137.1:5000** with HTTPS. PostgreSQL remains exclusively **127.0.0.1:55433 / queueless_erode_demo**. No Render, external database, GitHub main or Antigravity files are changed.

Windows Mobile Hotspot is confirmed On, using the active Microsoft Wi-Fi Direct virtual adapter `Local Area Connection* 12`, interface index 6, address 192.168.137.1/24. Connected clients are on 192.168.137.0/24. This virtual interface has no separate Windows connection profile; the startup helper validates the active Mobile Hotspot explicitly instead of treating it as an ordinary router Wi-Fi connection. The Internet uplink is marked Private. Do not use a guest/Public router network as a substitute.

## Start

After stopping the current Flask process with Ctrl+C, run:

```powershell
& 'C:\Users\girin\.codex\worktrees\erode-local-demo\DR\scripts\start-local-demo.ps1' -LanAddress 192.168.137.1 -MobileHotspot -Https
```

This starts only the isolated local PostgreSQL cluster if needed, verifies its identity, preserves the one-time seed, regenerates the actual QR for HTTPS and sets the permitted host/PUBLIC_BASE_URL. It binds no wildcard address. Debug/reload are off. HTTPS sessions use Secure cookies; gateway, CSRF and application permissions remain enabled.

## URLs and credentials

| Interface | URL |
| --- | --- |
| Reception | https://192.168.137.1:5000/static/local-demo/reception.html |
| Actual service QR | https://192.168.137.1:5000/static/local-demo/eye-consultation-qr.png |
| Patient | https://192.168.137.1:5000/app/b/erode-eye-clinic-demo/service/1 |
| Doctor | https://192.168.137.1:5000/app/staff/login |
| Owner | https://192.168.137.1:5000/app/owner/login |
| Public Display | https://192.168.137.1:5000/app/b/erode-eye-clinic-demo/display |

Private credentials remain in `.tmp/PRIVATE_LOCAL_DEMO_ACCESS.md`, with current HTTPS URLs. No passwords are in this document. Owner and Doctor are separate application logins after the browser gateway. Reception requires the gateway and does not require Owner privileges.

## Android certificate installation

Connect the phone to this laptop's Windows Mobile Hotspot. Transfer **only** `static/local-demo/QueueLess-Pulse-Hotspot-CA.crt` to the phone, for example into Downloads over USB. Never copy `.key` files or the private credentials profile.

In Android Settings, search for **Install certificate**. Select **CA certificate** and choose the transferred file. Menu names vary; credential installation is normally under Security / More security settings / Encryption and credentials. Enter any requested screen-lock PIN only on the phone. Google documents certificate management at https://support.google.com/pixelphone/answer/2844832; the Android CA must be installed through Settings, per https://developer.android.com/reference/android/security/KeyChain.

The public CA is named **QueueLess Pulse Local Demo CA**, SHA-256 fingerprint:

`0C:21:52:1F:C2:8E:BF:5A:A5:03:A6:71:7A:64:8F:2F:BE:AC:56:20:6C:6D:A1:44:18:33:90:20:1C:E2:24:88`

The certificate expires **12 October 2026, 4:17:42 PM IST**. The local server certificate has the exact hotspot IP in its Subject Alternative Name. This generated CA is trusted for the current Windows user for browser testing; remove it and the phone's installed demo CA after the demonstration. On Android, use Trusted credentials / User, select QueueLess Pulse Local Demo CA, and remove that certificate only.

Windows removal, for this exact generated certificate:

```powershell
Remove-Item -LiteralPath 'Cert:\CurrentUser\Root\687947E89EA4AABDB9D84BFD5AF3265C76AFE518'
```

HTTPS gives a secure browser context for the existing `crypto.randomUUID` call; the React bundle is not rebuilt. A local-launcher compatibility shim also exists for temporary LAN HTTP, using cryptographically random UUIDs, but the active hotspot release uses HTTPS and native browser UUID generation. Ordinary LAN HTTP is not assumed to expose that native API. HTTP would expose Basic credentials to network observers; never reuse production/hosted credentials there.

## Firewall and connection troubleshooting

No firewall change was made by the attempted setup: Windows reported that UAC elevation was canceled. If the phone cannot reach the URLs, run this prepared, narrowly scoped helper from **Administrator PowerShell**:

```powershell
& 'C:\Users\girin\.codex\worktrees\erode-local-demo\DR\scripts\hotspot-firewall.ps1'
```

It adds only `QueueLessPulse-Erode-Hotspot-HTTPS-5000`: inbound TCP 5000, local address 192.168.137.1, remote subnet 192.168.137.0/24, hotspot interface, Private profile, edge traversal blocked. It neither changes Public rules nor opens PostgreSQL. Its exact status is saved privately to `.tmp/hotspot-firewall-status.json` on success.

Remove this rule after the demonstration from Administrator PowerShell:

```powershell
Remove-NetFirewallRule -Name 'QueueLessPulse-Erode-Hotspot-HTTPS-5000'
```

The phone must remain connected to the laptop's hotspot, with a 192.168.137.x address. A phone browser timeout requires checking its hotspot connection and firewall; a certificate warning requires checking CA installation. No external router is used. Actual phone-to-laptop access, rather than a laptop browser accessing its own IP, is needed to prove there is no client-path isolation. Do not disable the firewall or forward ports to troubleshoot.

## Verified evidence

The desktop and mobile-viewport queue workflows passed at **https://192.168.137.1:5000**, with certificate validation and native secure-context UUID generation. The persistent HTTPS server also passed its Owner/Doctor/Reception/history check: **3 passed, 0 failed, 0 skipped across the two selected test runs**. The request runtime trusts the explicit local CA via `NODE_EXTRA_CA_CERTS`; no HTTPS-error bypass is used.

The workflow tests create separate test schemas in the same isolated PostgreSQL database. All 15 original public-schema rows and their 34 ticket events remain unchanged: 5 WAITING, E010 CALLED, 7 COMPLETED today and 2 SKIPPED today. Built React asset hashes are unchanged. The actual QR decodes to the HTTPS Eye Consultation URL. Gateway rejection and TLS verification were checked against the persistent service. Physical-phone certificate trust and scanning remain pending user confirmation.

E010 must be completed or skipped before Call Next. Existing E011–E015 precede a newly issued E016 in FIFO order. Real demonstration actions update persisted statuses and history; setup never resets them.
