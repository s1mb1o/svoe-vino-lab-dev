# Smoke tests

## 2026-10-18 accessibility

- All 12 simulator unit tests passed.
- All 6 accessibility UI tests passed.
- The test device was an iPhone 17 Pro simulator with iOS 26.2.

1. Enable VoiceOver.
2. Confirm that the age gate reads the title, age requirement, and both actions in logical order.
3. Select a photograph and confirm that VoiceOver moves to `Начать распознавание`.
4. Start recognition and confirm that VoiceOver announces the operation status.
5. Confirm that VoiceOver moves to `Результаты` when results appear.
6. Confirm that each result reads the wine name, producer, similarity, and website action.
7. Open History and confirm that each website action includes the wine name.
8. Open Settings and confirm that each picker reports its label and current value.
9. Confirm that each model status includes text and a symbol.
10. Start the accelerator test and confirm the start and completion announcements.
11. Open the code scanner with VoiceOver enabled.
12. Show one supported code to the camera.
13. Confirm that the detected value appears in the manual input field and VoiceOver reports it.
14. Set Dynamic Type to the largest accessibility size.
15. Confirm that source actions, result cards, and history rows use a vertical layout.
16. Confirm that text is not truncated and every action stays available.
17. Enable Reduce Motion, Reduce Transparency, Increase Contrast, Button Shapes, and Differentiate Without Color.
18. Confirm that every flow stays readable and usable in light and dark appearance.
19. Run `ChtoZaVinoUITests` on an iOS 17.2 or later simulator.
20. Confirm that all accessibility audits and control-size checks pass.

## 2026-10-06 bottleneck check

- All 11 simulator unit tests passed.
- A warm DIS with Base NaFlex p512 request improved from 6,728 ms to 3,216 ms.
- Warm local search improved from 360 ms to 11 ms.
- Repeated application startup reached the debug server in 5.6 seconds instead of 49.1 seconds.
- The optimized DIS path returned the same exact wine at rank 1.
- YOLO with Base NaFlex p512 returned the same wine at rank 1.
- The warm YOLO median was 1,884 ms.
- The simulator setting was restored to DIS after the comparison.

1. Start the installed application two times.
2. Confirm that the second start reuses the validation receipt.
3. Send the same image three times to `/v1/match`.
4. Confirm that `timings_ms` contains `segmentation`, `embedding`, and `search`.
5. Confirm that the Top-1 wine is stable.

## 2026-10-06 Base NaFlex p512

- All 10 simulator unit tests passed.
- `/healthz` reported encoder `siglip2-base-naflex-p512` and pack `20261006-ios-naflex-production`.
- A package-image self-match returned the exact wine at rank 1 with cosine 0.9083.
- The first request took 7,271 ms. The repeated request took 5,401 ms.
- The Settings screen showed NaFlex as selected. All three encoders reported `Готова`.

1. Select `SigLIP2 Base NaFlex p512` in Settings.
2. Confirm that Settings reports the model as `Готова`.
3. Recognize one bottle with DIS.
4. Confirm that the result uses `siglip2-base-naflex-p512` in the debug pipeline.
5. Repeat the request and confirm that the cached encoder works.
6. Run the accelerator test on a physical iPhone.
7. Confirm compatibility with the `CPU + ANE` compute mode.
8. Disable the network and repeat recognition.

## 2026-10-03 result

- The iPhone 17 Pro simulator used iOS 26.2.
- All 9 unit tests passed.
- The production pack reported 2,093 wines.
- `YOLO + MobileCLIP2-S2` returned `vinodelnya-marchenko-merlo-krasnoe-suhoe-14`.
- A clean request took 2,118.52 ms.
- A repeated cached request took 1,281.16 ms.
- `DIS + SigLIP2` returned the same Top-1 wine in 4,530.35 ms.
- `/healthz` reported the selected segmenter, selected encoder, pack version, and wine count.
- The main screen and Settings passed screenshot inspection.

## Automated checks

1. Run the Swift unit tests for the simulator.
2. Build the debug application for the simulator.
3. Install the application in a booted simulator.
4. Open the application and accept the age confirmation.
5. Import the bundled sample image.
6. Select DIS and SigLIP2.
7. Run recognition and confirm that results and debug images appear.
8. Select YOLO and confirm that the debug mask uses YOLO26n-seg.
9. Select MobileCLIP2-S2 and confirm that its vector index is used.
10. Enter a known EAN-13 value and confirm a local result.
11. Confirm that history survives an application restart.
12. Confirm that the application follows simulator light and dark appearance.
13. Enable the debug HTTP server and check `GET /healthz`.
14. Run `/v1/match` for each segmenter and encoder combination.
15. Confirm that `pipeline` identifies the selected models.

## Physical iPhone checks

1. Confirm camera capture.
2. Confirm live code scanning.
3. Confirm `Авто`, `ANE`, and `CPU` for DIS.
4. Confirm `Авто`, `ANE`, and `CPU` for each encoder.
5. Measure complete request latency and each inference stage.
6. Confirm operation without a network connection.
7. Repeat the accelerator test and confirm that the result appears in settings.
