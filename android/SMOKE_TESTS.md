# Smoke tests

## Automated checks

1. Run `./gradlew test`.
2. Run `./gradlew assembleDebug`.
3. Run `python3 -m unittest tools/test_build_model_pack.py`.

## Verification on 2026-09-28

- `./gradlew lintDebug test assembleDebug` passed with JDK 17.
- Three catalogue index tests passed for the debug and release variants.
- Two model-pack builder tests passed.
- The debug APK has `minSdkVersion` 28 and `targetSdkVersion` 36.
- The debug APK has the application ID `Chtozavino.alolalab.com`.
- A physical device was not connected. The device checks are pending.
- A compatible 768-dimensional model pack was not available. The inference checks are pending.

## Device checks

1. Install the debug APK on an Android 9 arm64 device.
2. Confirm that the 18+ window blocks the application content.
3. Select `Мне есть 18 лет`.
4. Confirm that the application remembers the answer after a restart.
5. Import a valid model pack.
6. Confirm that the model count and vector count appear.
7. Import a pack with a changed payload byte.
8. Confirm that the application rejects the pack.
9. Take one bottle photograph.
10. Select one bottle photograph from the gallery.
11. Start recognition for each image.
12. Confirm that the result contains ranked wines and scores.
13. Open the debug section.
14. Confirm that the DIS mask, crop, and white-background image are visible.
15. Open the best result on `vino-svoe.ru`.
16. Disable the network connection.
17. Repeat image recognition.
18. Confirm that image recognition still works.
19. Scan one known EAN code and one known QR code.
20. Confirm that each code resolves without an image embedding.
21. Open history.
22. Confirm that image and code results appear in newest-first order.
