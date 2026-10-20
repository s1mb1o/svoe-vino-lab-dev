# Android 0.3.0 verification — SEO-001

Checked on **20 October 2026, 19:26–19:28 UTC**. **The original APK/metadata mismatch is resolved for the production 0.3.0 download.** A complete GET, full-file SHA-256 and embedded manifest agree with the production page and pinned release contract. **HEAD still returns 404**; retain that as a P3/S response-correctness follow-up, outside the Pareto first wave.

Evidence: [E10, observations and source excerpts](evidence/android-030-verification.json). This supersedes the current-action conclusions of the earlier 0.2.0 finding; E01–E03 remain historical evidence of that previous release.

## Results

| Field | Production/download observation | Release contract / result |
|---|---|---|
| Android landing | HTTP 200; visible `Версия 0.3.0`, `718 МБ`, Android 9+ | Matches current `SoftwareApplication` and remote contract |
| Both download buttons | `/downloads/chtozavino-0.3.0-release-test-signed.apk` | Same filename in `download` attributes and Content-Disposition |
| Full download | **HTTP 200**, curl exit 0; **753,111,053 bytes** | Exactly equals JSON-LD `fileSize`, release contract, downloaded file and GET Content-Length |
| Rounded display size | 718 МБ | Approximately 718.22 MiB; consistent with the existing rounded binary-size convention |
| Embedded Android manifest | **versionName 0.3.0**, **versionCode 7** | Both match remote contract |
| Application ID | `com.alolalab.chtozavino` | Matches release record/contract |
| SDK | Minimum 28, target 36 | Minimum matches Android 9+ copy |
| Complete file SHA-256 | `89cb5863cc25c82dd424adb1d59ccb694f7ae0a7dbc1d7bd877c1001a05e5e7a` | Exactly matches both pinned contract and release record |
| Extracted signer certificate SHA-256 | `0d7616b6a86850435116fa262bbd2db5b18b06aebfd452ae37d5ac658a457cfb` in v2/v3 blocks | Matches the recorded existing test certificate; does not establish a new production signing identity |
| HEAD to new APK URL | **404**, JSON error MIME | Remaining method-dispatch discrepancy; GET is functional |
| Bounded Range request | HTTP 200 for complete representation; range ignored | Size guard deliberately stopped that probe before body transfer. The subsequent full GET succeeded; this is not a broken download. |

The 718 MB figure describes the downloadable APK, not the Android landing page's initial transfer. A larger new artifact is not itself a release-metadata mismatch.

## Source verification and branch drift

The local checkout at the start was `892e56749f27c95e518252d508c8084c5e73d02c`, with `webui/shared/android.ts` still declaring 0.2.0. It is a different branch/version from current production. I did not update, reset or merge it.

Read-only GitHub inspection pinned **main `58388d835d9a0dcf31cf4561dab03e757bfc2c03`**:

- [webui/shared/android.ts, lines 1–13](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/58388d835d9a0dcf31cf4561dab03e757bfc2c03/webui/shared/android.ts#L1-L13): version 0.3.0, code 7, exact size/hash, filename and display size.
- [android/docs/releases/0.3.0.md, lines 1–25](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/58388d835d9a0dcf31cf4561dab03e757bfc2c03/android/docs/releases/0.3.0.md#L1-L25): same artifact contract and certificate fingerprint; records prior signature/alignment checks.
- [webui/server/routes/downloads/[filename].get.ts, lines 5–30](https://github.com/s1mb1o/svoe-vino-lab-dev/blob/58388d835d9a0dcf31cf4561dab03e757bfc2c03/webui/server/routes/downloads/%5Bfilename%5D.get.ts#L5-L30): route remains method-specific GET. **Line 19 now rejects an unexpected byte length**, improving the old existence-only guard. This guard is verified in remote source; matching live bytes do not independently prove that exact deployed commit.

The actual downloaded APK agrees with this pinned record. Neither an old local checkout nor a matching manifest alone was used to infer binary identity.

## Remaining engineering task

**SEO-001 residual: P3 / Technical / S.** URL: `https://chtozavino.ru/downloads/chtozavino-0.3.0-release-test-signed.apk`. Existing GET-only route is consistent with the observed HEAD dispatch gap. Add an explicit `.head.ts` handler with a shared validated metadata/header resolver, or use a guarded GET/HEAD route. Preserve the filename/file-size checks and stream only for GET. HEAD should return 200 and the same content headers with no body. Do not hash a 753 MB file on every request; retain release-time attestation.

**Side effects:** HEAD must not allocate/read the APK stream; missing/unknown files and unexpected sizes must retain appropriate failures. Avoid accepting unintended methods. Preserve attachment naming, MIME, caching and GET content integrity.

**Verification:** on staging, compare GET and HEAD status/Content-Length/Content-Type/Content-Disposition; assert no HEAD body/stream. Test unknown filename, missing file and wrong-size file plus normal full GET/hash. After any separately authorized release, repeat bounded public headers and preserve a dated release record. No installation or production change is needed to establish this HTTP behavior.

The new size guard and artifact match resolve the high-priority concern. No new APK reconciliation/replacement project is justified by the current evidence. Keep the other five selected Pareto IDs as the first wave without automatically backfilling a sixth task.

## Method and limits

The complete 753,111,053-byte public APK was downloaded into audit-owned temporary storage and SHA-256 hashed. Python's existing ZIP facilities read the compiled Android manifest; a read-only binary-XML parser extracted package/version/SDK. Signing-block certificate DER was read according to the [AOSP v2 format](https://source.android.com/docs/security/features/apksigning/v2) and [v3 format](https://source.android.com/docs/security/features/apksigning/v3); existing OpenSSL parsed the certificates and confirmed their fingerprints. The APK was not installed or executed. It was removed from temporary storage after final evidence validation; no binary was added to the repository.

No existing Java runtime/apksigner SDK was available, so complete Android signature verification, alignment and install/upgrade tests were **not independently rerun**. The pinned release record reports those earlier signature/alignment checks. Certificate extraction is not a substitute for a full signature verifier. The full file's exact hash match and manifest inspection are independently verified here.

No application source, production configuration, dependency or Git ref was changed by this check. No deployment, issue posting or commit occurred. Only audit documentation/evidence was updated; concurrent unrelated workspace changes were left untouched.
