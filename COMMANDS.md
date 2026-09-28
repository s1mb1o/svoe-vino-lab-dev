python3 scripts/build_matcher_bundle.py \
    --embedding gx10-dinov3-vitb16 \
    --out <new-directory> \
    --include-images

python3 scripts/validate_matcher_bundle.py <bundle-directory>
