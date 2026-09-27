-- 024: the presentation mode of an image, the fifth value of `image_description`.
--
--   presentation_mode  the surface that carries the label: 'on_package', 'flat_surface',
--                      'other', 'unknown', or NULL (not set). The owner chose the four
--                      values on 2026-09-26. The prompt of `pipeline/describe_images.py`
--                      holds their meanings.
-- `ALTER TABLE` adds the column after `vlm_attempts`.
--
-- Each row that the VLM filled goes back to the queue of the watcher: `vlm_at`,
-- `vlm_name`, `vlm_model`, `vlm_answer`, and `vlm_error` become NULL, and `vlm_attempts`
-- becomes 0. The watcher fills only the values that are not set, so the four old values
-- stay, and they go into the prompt as fixed facts. The next answer fills
-- `presentation_mode`. A row that the VLM did not fill stays as it is. The owner chose
-- this on 2026-09-26.
-- Read docs/plans/26_image-description.md.

ALTER TABLE image_description ADD COLUMN presentation_mode TEXT
    CHECK (presentation_mode IN ('on_package', 'flat_surface', 'other', 'unknown'));

UPDATE image_description SET vlm_at = NULL, vlm_name = NULL, vlm_model = NULL,
    vlm_answer = NULL, vlm_error = NULL, vlm_attempts = 0
WHERE vlm_at IS NOT NULL;
