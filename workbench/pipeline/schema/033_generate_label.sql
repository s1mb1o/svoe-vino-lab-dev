-- 033: the owner can turn off the label cut of one image (plan 94).
--
--   generate_label  NULL (not set) or 1 (checked): the SAM3 label cut of the image is made
--                   as before. 0 (unchecked): no writer makes a label cut of the image, the
--                   save of the 0 removes the automatic label cut, and the embedding build
--                   marks the label view of the image as not applicable. A manual cut of
--                   plan 56 stays. The owner chose on 2026-09-30 that the value is a column
--                   of `image_description`.
-- `ALTER TABLE` adds the column after `presentation_mode`. No row changes, so each image
-- keeps its label cut.
-- Read docs/plans/94_generate-label-checkbox.md.
ALTER TABLE image_description ADD COLUMN generate_label INTEGER
    CHECK (generate_label IN (0, 1));
