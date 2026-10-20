# Resume the DIS USB interruption

Date: 2026-10-20.
Status: complete. The finite continuation finished at 19:33 MSK.
All 668 assignments passed the quality audit. All inherited records remain byte-identical.
HTTP-off and isolated-process-stop cleanup passed. The USB forward is absent.
Request latencies passed their targets. Do not claim uninterrupted stability.
The owner requested `resume`.

## Evidence and scope

Condition 8 saved 190 of 668 assignments before USB disconnected.
The original host controller exited. The Pixel process remains 22646.
The installed APK and private pack retain their frozen SHA-256 values.
All 191 received records contain one warmup and the 190 saved responses.
There is no received but unsaved assignment.
Keep completed conditions 5 and 7 unchanged. Keep all v3 artifacts unchanged.
Do not rebuild or install the application. Do not change the model pack.

## Continuation contract

Add an explicit full-run resume option to the host runner.
Require the expected prefix length. Require the same Pixel process.
Reject changed queries, accepted answers, condition, APK, pack, serial, or package.
Audit every prefix response and prediction before copying the prefix.
Require exact ordered query IDs, image hashes, candidates, and timing records.
Reject a partial line, an unexpected error, or a received but unsaved response.
Copy the raw interrupted attempt into a new output directory.
Copy the response and prediction prefixes without changing their bytes.
Preserve the interrupted metadata and its cleanup errors.
Record the continuation start, source inventory, and process identity separately.
Exclude the disconnected interval and the continuation warmup from request latency.
Include both measured segments in quality and request-latency calculations.
Do not label a resumed cohort as an uninterrupted stability pass.

## Execution and checks

Test rejection of changed identities, order, candidates, prefix length, and partial lines.
Test exact byte preservation. Test the resumed audit stability label.
Freeze a new host source snapshot. Do not edit source-snapshot-v3.
Use a finite detached workflow with no restart policy.
Check user 0, idle HTTP, foreground service, wake lock, and unchanged process.
Require thermal status at most 2 and battery temperature at most 40 C before continuation.
Resume at assignment 191. Keep re-ranking, barcode, and fallback disabled.
Audit the completed 668-assignment cohort. Compare it with conditions 5 and 7.
Disable HTTP and stop only the isolated test package during cleanup.
Remove the owned USB forward. Restore the observed screen-power setting.
Save cleanup evidence. Report the interruption with the final comparison.
